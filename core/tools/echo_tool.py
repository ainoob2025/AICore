"""Echo tool (enterprise-grade test utility)."""

from __future__ import annotations

from typing import Any, Dict


class EchoTool:
    """Deterministic echo tool for smoke tests and integration checks."""

    def run(self, method: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(method, str) or not method:
            return {"ok": False, "error": "INVALID_METHOD", "details": {"method": method}}
        if not isinstance(args, dict):
            return {"ok": False, "error": "INVALID_ARGS", "details": {"type": type(args).__name__}}

        if method == "echo":
            text = args.get("text", "")
            if not isinstance(text, (str, int, float, bool)):
                return {"ok": False, "error": "INVALID_TEXT", "details": {"type": type(text).__name__}}
            return {"ok": True, "text": str(text)}

        if method == "ping":
            return {"ok": True, "pong": True}

        return {"ok": False, "error": "UNKNOWN_METHOD", "details": {"method": method}}
