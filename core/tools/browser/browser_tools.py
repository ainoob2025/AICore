"""BrowserTools (enterprise-grade): HTTP client with guardrails (internet open, LAN allowlist)."""

from __future__ import annotations

import json
import os
import re
import socket
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Tuple


class BrowserTools:
    _DEFAULT_TIMEOUT_SEC = 15
    _DEFAULT_MAX_BYTES = 2_000_000
    _DEFAULT_MAX_TEXT_CHARS = 2_000_000

    def __init__(self) -> None:
        self._allowlist = self._load_allowlist_env()

    def _load_allowlist_env(self) -> List[str]:
        raw = os.environ.get("AICORE_HTTP_ALLOWLIST", "").strip()
        if not raw:
            return []
        return [p.strip().lower() for p in raw.split(",") if p.strip()]

    def _host_allowlisted(self, host: str) -> bool:
        h = host.lower()
        for p in self._allowlist:
            if p == h:
                return True
            if p.startswith("*.") and h.endswith(p[1:]) and h != p[2:]:
                return True
        return False

    def _is_blocked_ipv4(self, ip: str) -> bool:
        # Block only classic LAN/private ranges + loopback + link-local + CGNAT for guardrails.
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        a, b, *_ = [int(x) for x in parts]
        if a in (0, 10, 127):
            return True
        if a == 169 and b == 254:
            return True
        if a == 172 and 16 <= b <= 31:
            return True
        if a == 192 and b == 168:
            return True
        if a == 100 and 64 <= b <= 127:
            return True
        return False

    def _is_blocked_ipv6(self, ip: str) -> bool:
        # Guardrails for IPv6: block loopback, link-local, unique-local.
        s = ip.lower()
        if s == "::1":
            return True
        if s.startswith("fe80:"):  # link-local
            return True
        if s.startswith("fc") or s.startswith("fd"):  # unique local (fc00::/7)
            return True
        return False

    def _is_blocked_ip(self, ip: str) -> bool:
        if ":" in ip:
            return self._is_blocked_ipv6(ip)
        return self._is_blocked_ipv4(ip)

    def _resolve_ips(self, host: str) -> List[str]:
        try:
            infos = socket.getaddrinfo(host, None)
            ips: List[str] = []
            for info in infos:
                ip = info[4][0]
                if ip not in ips:
                    ips.append(ip)
            return ips
        except Exception:
            return []

    def _validate_url(self, url: str) -> Tuple[bool, str, Dict[str, Any]]:
        if not isinstance(url, str) or not url.strip():
            return False, "INVALID_URL", {"url": url}

        u = url.strip()
        parsed = urllib.parse.urlparse(u)

        if parsed.scheme not in ("http", "https"):
            return False, "INVALID_SCHEME", {"scheme": parsed.scheme}

        host = parsed.hostname
        if not host:
            return False, "MISSING_HOST", {"url": u}

        ips = self._resolve_ips(host)
        if not ips:
            return False, "DNS_RESOLUTION_FAILED", {"host": host}

        for ip in ips:
            if self._is_blocked_ip(ip) and not self._host_allowlisted(host):
                return False, "LAN_HOST_NOT_ALLOWLISTED", {"host": host, "ip": ip, "allowlist": self._allowlist}

        return True, u, {"host": host, "ips": ips, "allowlist": self._allowlist}

    def _truncate_bytes(self, data: bytes, max_bytes: int) -> Tuple[bytes, bool]:
        if len(data) > max_bytes:
            return data[:max_bytes], True
        return data, False

    def _decode_text(self, data: bytes, content_type: str, max_chars: int) -> Tuple[str, bool]:
        charset = "utf-8"
        m = re.search(r"charset=([A-Za-z0-9._-]+)", content_type or "", re.IGNORECASE)
        if m:
            charset = m.group(1)
        text = data.decode(charset, errors="replace")
        if len(text) > max_chars:
            return text[:max_chars], True
        return text, False

    def run(self, method: str, args: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "ok": False,
            "url": None,
            "status": None,
            "headers": None,
            "content_type": None,
            "text": None,
            "json": None,
            "body_truncated": None,
            "text_truncated": None,
            "error": None,
            "details": None,
        }

        try:
            if not isinstance(method, str) or not method:
                out["error"] = "INVALID_METHOD"
                out["details"] = {"method": method}
                return out
            if not isinstance(args, dict):
                out["error"] = "INVALID_ARGS"
                out["details"] = {"type": type(args).__name__}
                return out
            if method != "http_get":
                out["error"] = "UNKNOWN_METHOD"
                out["details"] = {"method": method}
                return out

            url = args.get("url", "")
            timeout = args.get("timeout_sec", self._DEFAULT_TIMEOUT_SEC)
            max_bytes = args.get("max_bytes", self._DEFAULT_MAX_BYTES)
            max_chars = args.get("max_text_chars", self._DEFAULT_MAX_TEXT_CHARS)

            if not isinstance(timeout, int) or timeout <= 0 or timeout > 300:
                out["error"] = "INVALID_TIMEOUT"
                out["details"] = {"timeout_sec": timeout}
                return out
            if not isinstance(max_bytes, int) or max_bytes <= 0 or max_bytes > 200_000_000:
                out["error"] = "INVALID_MAX_BYTES"
                out["details"] = {"max_bytes": max_bytes}
                return out
            if not isinstance(max_chars, int) or max_chars <= 0 or max_chars > 200_000_000:
                out["error"] = "INVALID_MAX_TEXT_CHARS"
                out["details"] = {"max_text_chars": max_chars}
                return out

            ok, vurl_or_err, vdetails = self._validate_url(url)
            if not ok:
                out["error"] = vurl_or_err
                out["details"] = vdetails
                return out

            vurl = vurl_or_err
            out["url"] = vurl

            req = urllib.request.Request(vurl, method="GET", headers={"User-Agent": "AICoreBrowser/1.0", "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = int(resp.getcode() or 0)
                headers = dict(resp.headers.items())
                ct = headers.get("Content-Type", "")

                raw = resp.read(max_bytes + 1)
                raw2, body_trunc = self._truncate_bytes(raw, max_bytes)
                text, text_trunc = self._decode_text(raw2, ct, max_chars)

                parsed_json = None
                if "application/json" in (ct or "").lower():
                    try:
                        parsed_json = json.loads(text)
                    except Exception:
                        parsed_json = None

                out.update(
                    ok=True,
                    status=status,
                    headers=headers,
                    content_type=ct,
                    text=text,
                    json=parsed_json,
                    body_truncated=body_trunc,
                    text_truncated=text_trunc,
                )
                return out

        except Exception as exc:
            out["error"] = "BROWSERTOOLS_EXCEPTION"
            out["details"] = {"type": type(exc).__name__, "message": str(exc)}
            return out


if __name__ == "__main__":
    bt = BrowserTools()
    r = bt.run("http_get", {"url": "https://example.com", "timeout_sec": 10})
    print(r["ok"], r["status"], r["error"])
