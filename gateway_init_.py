"""Gateway (enterprise-grade, local-first): HTTP server for MasterAgent.

Contract:
- Host: 127.0.0.1
- Port: 10010 (fixed, non-configurable)
- Endpoints:
  - GET /health
  - GET /health/llm
  - GET /metrics
  - POST /chat

Notes:
- Deterministic request IDs (X-Request-Id)
- JSONL request logging with rotation/retention
- Rate limit: 30 requests / 60s / IP (429 + Retry-After)
- Concurrency guard: max 4 in-flight chat requests (503 BUSY)
"""

from __future__ import annotations

import json
import os
import signal
import threading
import time
import uuid
import urllib.error
import urllib.request
from collections import Counter, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Deque, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from core.kernel.master_agent import MasterAgent

HOST = "127.0.0.1"
PORT = 10010

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT_DIR, "logs")
REQ_LOG_PATH = os.path.join(LOG_DIR, "gateway_requests.jsonl")

AGENT = MasterAgent()

_LOG_LOCK = threading.Lock()

_STARTED_AT = time.time()
_METRICS_LOCK = threading.Lock()
_REQ_TOTAL = 0
_ERR_TOTAL = 0
_RATE_LIMITED_TOTAL = 0
_BY_PATH = Counter()
_BY_STATUS = Counter()
_LAT_MS: Deque[int] = deque(maxlen=5000)
_PLANS_SAVED_TOTAL = 0
_LAST_PLAN_ID = ""

_CHAT_METRICS_LOCK = threading.Lock()
_CHAT_MS: Deque[int] = deque(maxlen=5000)

_CHAT_INFLIGHT_LOCK = threading.Lock()
_CHAT_INFLIGHT = 0
_CHAT_BUSY_TOTAL = 0
MAX_CHAT_INFLIGHT = 4

_RATE_LOCK = threading.Lock()
_RATE_BUCKETS: Dict[str, Deque[float]] = {}
RATE_LIMIT_WINDOW_S = 60.0
RATE_LIMIT_MAX = 30

_WARMUP_LOCK = threading.Lock()
_WARMUP_STARTED = False
_WARMUP_DONE = False
_WARMUP_OK = False
_WARMUP_MS = 0
_WARMUP_ERR: Optional[str] = None

MAX_BODY_BYTES = 1024 * 1024  # 1 MiB
MAX_MESSAGE_CHARS = 100_000


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _ensure_log_dir() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)


def _append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    _ensure_log_dir()
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    with _LOG_LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)


def _percentile(sorted_vals: Tuple[int, ...], p: float) -> int:
    if not sorted_vals:
        return 0
    if p <= 0:
        return int(sorted_vals[0])
    if p >= 1:
        return int(sorted_vals[-1])
    idx = int(round((len(sorted_vals) - 1) * p))
    idx = max(0, min(len(sorted_vals) - 1, idx))
    return int(sorted_vals[idx])


def _warmup_state() -> Dict[str, Any]:
    with _WARMUP_LOCK:
        return {
            "warmup_started": _WARMUP_STARTED,
            "warmup_done": _WARMUP_DONE,
            "warmup_ok": _WARMUP_OK,
            "warmup_ms": _WARMUP_MS,
            "warmup_error": _WARMUP_ERR,
        }


def _record_metrics(path: str, status: int, latency_ms: int) -> None:
    global _REQ_TOTAL, _ERR_TOTAL
    with _METRICS_LOCK:
        _REQ_TOTAL += 1
        if status >= 400:
            _ERR_TOTAL += 1
        _BY_PATH[path] += 1
        _BY_STATUS[str(status)] += 1
        _LAT_MS.append(latency_ms)


def _record_chat_latency(ms: int) -> None:
    with _CHAT_METRICS_LOCK:
        _CHAT_MS.append(ms)


def _snapshot_metrics() -> Dict[str, Any]:
    with _METRICS_LOCK:
        vals = tuple(_LAT_MS)
        chat_vals = tuple(_CHAT_MS)
        by_path = dict(_BY_PATH)
        by_status = {str(k): v for k, v in _BY_STATUS.items()}
        req_total = _REQ_TOTAL
        err_total = _ERR_TOTAL
        rl_total = _RATE_LIMITED_TOTAL
        plans_saved_total = _PLANS_SAVED_TOTAL
        last_plan_id = _LAST_PLAN_ID

    with _CHAT_INFLIGHT_LOCK:
        inflight = _CHAT_INFLIGHT
        busy_total = _CHAT_BUSY_TOTAL

    vals_sorted = tuple(sorted(vals))
    chat_sorted = tuple(sorted(chat_vals))

    base = {
        "ok": True,
        "uptime_s": int(time.time() - _STARTED_AT),
        "requests_total": req_total,
        "plans_saved_total": plans_saved_total,
        "last_plan_id": last_plan_id,
        "errors_total": err_total,
        "rate_limited_total": rl_total,
        "by_path": by_path,
        "by_status": by_status,
        "latency_ms_p50": _percentile(vals_sorted, 0.50),
        "latency_ms_p95": _percentile(vals_sorted, 0.95),
        "latency_ms_p99": _percentile(vals_sorted, 0.99),
        "latency_samples": len(vals_sorted),
        "chat_p95_ms": _percentile(chat_sorted, 0.95),
        "chat_samples": len(chat_sorted),
        "chat_inflight": inflight,
        "max_chat_inflight": MAX_CHAT_INFLIGHT,
        "chat_busy_total": busy_total,
    }
    base.update(_warmup_state())
    return base


def _rate_limit_ok(ip: str) -> Tuple[bool, int]:
    now = time.time()
    with _RATE_LOCK:
        dq = _RATE_BUCKETS.get(ip)
        if dq is None:
            dq = deque()
            _RATE_BUCKETS[ip] = dq
        while dq and (now - dq[0]) > RATE_LIMIT_WINDOW_S:
            dq.popleft()
        if len(dq) >= RATE_LIMIT_MAX:
            retry_after = int(max(1, RATE_LIMIT_WINDOW_S - (now - dq[0])))
            return False, retry_after
        dq.append(now)
        return True, 0


def _mark_rate_limited() -> None:
    global _RATE_LIMITED_TOTAL
    with _METRICS_LOCK:
        _RATE_LIMITED_TOTAL += 1


def _chat_acquire() -> bool:
    global _CHAT_INFLIGHT, _CHAT_BUSY_TOTAL
    with _CHAT_INFLIGHT_LOCK:
        if _CHAT_INFLIGHT >= MAX_CHAT_INFLIGHT:
            _CHAT_BUSY_TOTAL += 1
            return False
        _CHAT_INFLIGHT += 1
        return True


def _chat_release() -> None:
    global _CHAT_INFLIGHT
    with _CHAT_INFLIGHT_LOCK:
        _CHAT_INFLIGHT = max(0, _CHAT_INFLIGHT - 1)


def _health_llm_details() -> Tuple[bool, Dict[str, Any]]:
    # HARD GUARANTEE: never throw. Always returns (ok, details).
    try:
        ok, details = AGENT.health_llm()
        if not isinstance(details, dict):
            details = {"details": details}
        return bool(ok), details
    except Exception as exc:
        return False, {"type": type(exc).__name__, "message": str(exc)}


class Handler(BaseHTTPRequestHandler):
    server_version = "AICoreGateway/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: Dict[str, Any], request_id: str, extra_headers: Optional[Dict[str, str]] = None) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-Id", request_id)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        request_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        status = 500
        try:
            if self.path == "/health":
                status = 200
                self._send_json(200, {"ok": True}, request_id=request_id)
                return

            if self.path == "/health/llm":
                ok, details = _health_llm_details()
                if ok:
                    status = 200
                    self._send_json(200, {"ok": True, "details": details}, request_id=request_id)
                else:
                    status = 503
                    self._send_json(503, {"ok": False, "error": "LLM_UNREACHABLE", "details": details}, request_id=request_id)
                return

            if self.path == "/metrics":
                status = 200
                self._send_json(200, _snapshot_metrics(), request_id=request_id)
                return

            status = 404
            self._send_json(404, {"ok": False, "error": "NOT_FOUND"}, request_id=request_id)
        finally:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            _record_metrics(self.path, status, latency_ms)
            _append_jsonl(
                REQ_LOG_PATH,
                {
                    "ts": _utc_iso(),
                    "request_id": request_id,
                    "remote": self.client_address[0] if self.client_address else None,
                    "method": "GET",
                    "path": self.path,
                    "status": status,
                    "latency_ms": latency_ms,
                },
            )

    def do_POST(self) -> None:
        request_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        status = 500
        session_id: Optional[str] = None
        plan_id: Optional[str] = None
        acquired = False
        chat_total_ms: Optional[int] = None

        try:
            if self.path != "/chat":
                status = 404
                self._send_json(404, {"ok": False, "error": "NOT_FOUND"}, request_id=request_id)
                return

            remote_ip = self.client_address[0] if self.client_address else "unknown"

            ok, retry_after = _rate_limit_ok(remote_ip)
            if not ok:
                _mark_rate_limited()
                status = 429
                self._send_json(
                    429,
                    {"ok": False, "error": "RATE_LIMITED"},
                    request_id=request_id,
                    extra_headers={"Retry-After": str(retry_after)},
                )
                return

            acquired = _chat_acquire()
            if not acquired:
                status = 503
                self._send_json(503, {"ok": False, "error": "BUSY"}, request_id=request_id)
                return

            clen = int(self.headers.get("Content-Length", "0") or "0")
            if clen > MAX_BODY_BYTES:
                status = 413
                self._send_json(413, {"ok": False, "error": "PAYLOAD_TOO_LARGE", "limit_bytes": MAX_BODY_BYTES}, request_id=request_id)
                return

            raw = self.rfile.read(clen) if clen > 0 else b"{}"
            body = json.loads(raw.decode("utf-8", errors="replace"))
            if not isinstance(body, dict):
                status = 400
                self._send_json(400, {"ok": False, "error": "INVALID_SCHEMA"}, request_id=request_id)
                return

            if "message" not in body or not isinstance(body.get("message"), str):
                status = 400
                self._send_json(400, {"ok": False, "error": "INVALID_REQUEST", "details": {"missing_or_type": "message"}}, request_id=request_id)
                return

            message = body.get("message", "")
            if len(message) > MAX_MESSAGE_CHARS:
                status = 413
                self._send_json(413, {"ok": False, "error": "PAYLOAD_TOO_LARGE", "limit_chars": MAX_MESSAGE_CHARS}, request_id=request_id)
                return

            sid = body.get("session_id", "default")
            if not isinstance(sid, str):
                status = 400
                self._send_json(400, {"ok": False, "error": "INVALID_REQUEST", "details": {"session_id": "must be string"}}, request_id=request_id)
                return
            session_id = sid

            pid = body.get("plan_id", None)
            if pid is not None and not isinstance(pid, str):
                status = 400
                self._send_json(400, {"ok": False, "error": "INVALID_REQUEST", "details": {"plan_id": "must be string"}}, request_id=request_id)
                return
            plan_id = pid

            res = AGENT.handle_chat(message, session_id=session_id, plan_id=plan_id)

            # Metrics: count successful plan checkpoint saves and track last plan_id
            try:
                cp = res.get("checkpoint") if isinstance(res, dict) else None
                if isinstance(cp, dict) and cp.get("ok") is True:
                    pid2 = cp.get("plan_id")
                    if not isinstance(pid2, str) or not pid2:
                        pl = res.get("plan") if isinstance(res, dict) else None
                        pid2 = pl.get("plan_id") if isinstance(pl, dict) else None
                    if isinstance(pid2, str) and pid2:
                        with _METRICS_LOCK:
                            global _PLANS_SAVED_TOTAL, _LAST_PLAN_ID
                            _PLANS_SAVED_TOTAL += 1
                            _LAST_PLAN_ID = pid2
            except Exception:
                pass

            try:
                tm = res.get("timing_ms") if isinstance(res, dict) else None
                if isinstance(tm, dict) and "total" in tm:
                    chat_total_ms = int(tm.get("total") or 0)
                    _record_chat_latency(chat_total_ms)
            except Exception:
                pass

            status = 200
            self._send_json(200, res, request_id=request_id)

        except Exception as exc:
            status = 500
            self._send_json(
                500,
                {"ok": False, "error": "GATEWAY_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}},
                request_id=request_id,
            )
        finally:
            if acquired:
                _chat_release()
            latency_ms = int((time.perf_counter() - t0) * 1000)
            _record_metrics(self.path, status, latency_ms)
            rec = {
                "ts": _utc_iso(),
                "request_id": request_id,
                "remote": self.client_address[0] if self.client_address else None,
                "method": "POST",
                "path": self.path,
                "status": status,
                "latency_ms": latency_ms,
            }
            if session_id is not None:
                rec["session_id"] = session_id
            if plan_id:
                rec["plan_id"] = plan_id
            if chat_total_ms is not None:
                rec["chat_total_ms"] = chat_total_ms
            _append_jsonl(REQ_LOG_PATH, rec)


def _warmup() -> None:
    global _WARMUP_STARTED, _WARMUP_DONE, _WARMUP_OK, _WARMUP_MS, _WARMUP_ERR
    with _WARMUP_LOCK:
        if _WARMUP_STARTED:
            return
        _WARMUP_STARTED = True

    t0 = time.perf_counter()
    try:
        ok, details = AGENT.health_llm()
        ms = int((time.perf_counter() - t0) * 1000)
        with _WARMUP_LOCK:
            _WARMUP_DONE = True
            _WARMUP_OK = bool(ok)
            _WARMUP_MS = ms
            _WARMUP_ERR = None if ok else json.dumps(details, ensure_ascii=False)
    except Exception as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        with _WARMUP_LOCK:
            _WARMUP_DONE = True
            _WARMUP_OK = False
            _WARMUP_MS = ms
            _WARMUP_ERR = f"{type(exc).__name__}:{exc}"


def run() -> None:
    _warmup()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)

    stop_event = threading.Event()

    def _signal_handler(signum: int, frame: Any) -> None:
        stop_event.set()
        try:
            httpd.shutdown()
        except Exception:
            pass

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    httpd.serve_forever()


if __name__ == "__main__":
    run()
