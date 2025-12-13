"""Gateway (enterprise-grade, local-first): HTTP server for MasterAgent.

Fixed network contract:
- Host: 127.0.0.1
- Port: 10010

Routes:
- GET  /health        (fast)
- GET  /health/llm    (deep check LM Studio reachability)
- GET  /metrics
- POST /chat          {session_id?: str, plan_id?: str, message: str}

(Other behavior unchanged)
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

from core.kernel.master_agent import MasterAgent


HOST = "127.0.0.1"
PORT = 10010

MAX_BODY_BYTES = 256 * 1024
MAX_MESSAGE_CHARS = 32_000

CHAT_RATE_LIMIT_COUNT = 30
CHAT_RATE_LIMIT_WINDOW_S = 60
MAX_RL_KEYS = 5000

MAX_CHAT_INFLIGHT = 4

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
_CHAT_MS: Deque[int] = deque(maxlen=2000)

_RL_LOCK = threading.Lock()
_RL: Dict[str, Deque[float]] = {}

_WARMUP_LOGGED = {"done": False}

_CHAT_INFLIGHT_LOCK = threading.Lock()
_CHAT_INFLIGHT = 0
_CHAT_BUSY_TOTAL = 0


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
    k = int(round((len(sorted_vals) - 1) * p))
    if k < 0:
        k = 0
    if k >= len(sorted_vals):
        k = len(sorted_vals) - 1
    return int(sorted_vals[k])


def _record_metrics(path: str, status: int, latency_ms: int) -> None:
    global _REQ_TOTAL, _ERR_TOTAL
    with _METRICS_LOCK:
        _REQ_TOTAL += 1
        _BY_PATH[path] += 1
        _BY_STATUS[status] += 1
        _LAT_MS.append(latency_ms)
        if status >= 500:
            _ERR_TOTAL += 1


def _inc_rate_limited() -> None:
    global _RATE_LIMITED_TOTAL
    with _METRICS_LOCK:
        _RATE_LIMITED_TOTAL += 1


def _record_chat_latency(chat_total_ms: int) -> None:
    if chat_total_ms < 0:
        return
    with _METRICS_LOCK:
        _CHAT_MS.append(int(chat_total_ms))


def _warmup_state() -> Dict[str, Any]:
    try:
        return AGENT.warmup_status()
    except Exception:
        return {"warmup_started": False, "warmup_done": False, "warmup_ok": False, "warmup_ms": 0, "warmup_error": None}


def _snapshot_metrics() -> Dict[str, Any]:
    with _METRICS_LOCK:
        vals = tuple(_LAT_MS)
        chat_vals = tuple(_CHAT_MS)
        by_path = dict(_BY_PATH)
        by_status = {str(k): v for k, v in _BY_STATUS.items()}
        req_total = _REQ_TOTAL
        err_total = _ERR_TOTAL
        rl_total = _RATE_LIMITED_TOTAL

    with _CHAT_INFLIGHT_LOCK:
        inflight = _CHAT_INFLIGHT
        busy_total = _CHAT_BUSY_TOTAL

    vals_sorted = tuple(sorted(vals))
    chat_sorted = tuple(sorted(chat_vals))

    base = {
        "ok": True,
        "uptime_s": int(time.time() - _STARTED_AT),
        "requests_total": req_total,
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


def _llm_reachable() -> Tuple[bool, Optional[Dict[str, Any]]]:
    try:
        base = getattr(getattr(AGENT, "llm", None), "base_url", None)
        if not base or not isinstance(base, str):
            return False, {"error": "NO_LLM_BASE_URL"}

        url = base.rstrip("/") + "/v1/models"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            raw = resp.read()
        obj = json.loads(raw.decode("utf-8", errors="replace"))
        if isinstance(obj, dict) and "data" in obj:
            return True, None
        return False, {"error": "INVALID_LLM_RESPONSE", "response_preview": str(obj)[:200]}
    except urllib.error.HTTPError as exc:
        return False, {"error": "HTTP_ERROR", "code": exc.code, "reason": str(exc.reason)}
    except Exception as exc:
        return False, {"error": "LLM_UNREACHABLE", "type": type(exc).__name__, "message": str(exc)}


def _rl_cleanup_and_bound(window_start: float) -> None:
    empty_keys = [k for k, dq in _RL.items() if not dq or (dq and dq[-1] < window_start)]
    for k in empty_keys:
        _RL.pop(k, None)

    if len(_RL) > MAX_RL_KEYS:
        keys_sorted = sorted(_RL.keys())
        drop = keys_sorted[MAX_RL_KEYS:]
        for k in drop:
            _RL.pop(k, None)


def _rate_limit_allow(remote_ip: str) -> Tuple[bool, int]:
    now = time.time()
    window_start = now - CHAT_RATE_LIMIT_WINDOW_S

    with _RL_LOCK:
        dq = _RL.get(remote_ip)
        if dq is None:
            dq = deque()
            _RL[remote_ip] = dq

        while dq and dq[0] < window_start:
            dq.popleft()

        _rl_cleanup_and_bound(window_start)

        dq = _RL.get(remote_ip)
        if dq is None:
            dq = deque()
            _RL[remote_ip] = dq

        if len(dq) >= CHAT_RATE_LIMIT_COUNT:
            oldest = dq[0] if dq else now
            retry_after = int(max(1, (oldest + CHAT_RATE_LIMIT_WINDOW_S) - now))
            return False, retry_after

        dq.append(now)
        return True, 0


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
        if _CHAT_INFLIGHT > 0:
            _CHAT_INFLIGHT -= 1


class Handler(BaseHTTPRequestHandler):
    server_version = "AICoreGateway/2.5"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, code: int, obj: Dict[str, Any], request_id: str) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-Id", request_id)
        if code == 429 and isinstance(obj, dict) and "retry_after_s" in obj:
            self.send_header("Retry-After", str(obj["retry_after_s"]))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        request_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        status = 500
        payload: Dict[str, Any] = {"ok": False}

        try:
            if self.path == "/health":
                st = _warmup_state()
                if st.get("warmup_done") and not st.get("warmup_ok"):
                    status = 503
                    payload = {"ok": False, "error": "WARMUP_FAILED"}
                else:
                    status = 200
                    payload = {"ok": True}
            elif self.path == "/health/llm":
                ok, details = _llm_reachable()
                status = 200 if ok else 503
                payload = {"ok": True} if ok else {"ok": False, "error": "LLM_UNREACHABLE", "details": details}
            elif self.path == "/metrics":
                status = 200
                payload = _snapshot_metrics()
            else:
                status = 404
                payload = {"ok": False, "error": "NOT_FOUND"}
        finally:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            _record_metrics(self.path, status, latency_ms)
            self._send_json(status, payload, request_id=request_id)

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
                self._send_json(404, {"ok": False, "error": "NOT_FOUND"}, request_id=request_id)
                return

            remote_ip = self.client_address[0] if self.client_address else "unknown"

            allowed, retry_after_s = _rate_limit_allow(remote_ip)
            if not allowed:
                _inc_rate_limited()
                self._send_json(429, {"ok": False, "error": "RATE_LIMITED", "retry_after_s": retry_after_s}, request_id=request_id)
                return

            acquired = _chat_acquire()
            if not acquired:
                self._send_json(503, {"ok": False, "error": "BUSY"}, request_id=request_id)
                return

            clen = int(self.headers.get("Content-Length", "0") or "0")
            if clen > MAX_BODY_BYTES:
                self._send_json(413, {"ok": False, "error": "PAYLOAD_TOO_LARGE", "limit_bytes": MAX_BODY_BYTES}, request_id=request_id)
                return

            raw = self.rfile.read(clen) if clen > 0 else b"{}"
            body = json.loads(raw.decode("utf-8", errors="replace"))
            if not isinstance(body, dict):
                self._send_json(400, {"ok": False, "error": "INVALID_SCHEMA"}, request_id=request_id)
                return

            if "message" not in body or not isinstance(body.get("message"), str):
                self._send_json(400, {"ok": False, "error": "INVALID_SCHEMA", "details": {"missing_or_type": "message"}}, request_id=request_id)
                return

            message = body.get("message", "")
            if len(message) > MAX_MESSAGE_CHARS:
                self._send_json(413, {"ok": False, "error": "PAYLOAD_TOO_LARGE", "limit_chars": MAX_MESSAGE_CHARS}, request_id=request_id)
                return

            sid = body.get("session_id", "default")
            if not isinstance(sid, str):
                self._send_json(400, {"ok": False, "error": "INVALID_SCHEMA", "details": {"session_id": "must be string"}}, request_id=request_id)
                return
            session_id = sid

            pid = body.get("plan_id", None)
            if pid is not None and not isinstance(pid, str):
                self._send_json(400, {"ok": False, "error": "INVALID_SCHEMA", "details": {"plan_id": "must be string"}}, request_id=request_id)
                return
            plan_id = pid

            res = AGENT.handle_chat(message, session_id=session_id, plan_id=plan_id)

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
            self._send_json(500, {"ok": False, "error": "GATEWAY_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}, request_id=request_id)
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


def _install_signal_handlers(httpd: ThreadingHTTPServer) -> None:
    stop_once = {"done": False}

    def _request_stop(signum: int, _frame: Any) -> None:
        if stop_once["done"]:
            return
        stop_once["done"] = True

        def _shutdown() -> None:
            try:
                httpd.shutdown()
            except Exception:
                pass

        threading.Thread(target=_shutdown, daemon=True).start()

    try:
        signal.signal(signal.SIGINT, _request_stop)
    except Exception:
        pass

    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, _request_stop)
        except Exception:
            pass


def run() -> None:
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    httpd.daemon_threads = True
    _install_signal_handlers(httpd)
    print(f"Gateway listening on http://{HOST}:{PORT}")
    try:
        httpd.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            httpd.server_close()
        except Exception:
            pass
        print("Gateway stopped.")


if __name__ == "__main__":
    run()
