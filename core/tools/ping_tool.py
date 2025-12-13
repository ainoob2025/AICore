"""Deterministic PingTool (baseline tool health)."""

from __future__ import annotations

from typing import Any, Dict


class PingTool:
    """Minimal, deterministic tool used for health/baseline verification.
    Returns a fixed payload to avoid non-determinism.
    """

    def run(self, method: str, args: Dict[str, Any]) -> Dict[str, Any]:
        m = (method or "").strip().lower()

        # Accept common variants produced by planners/LLMs
        if m in ("ping", "pong", "get", "execute", "run"):
            return {"pong": True}

        return {
            "pong": False,
            "error": "INVALID_METHOD",
            "details": {"allowed": ["ping", "pong", "get", "execute", "run"], "got": method},
        }
