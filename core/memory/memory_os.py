"""MemoryOS (enterprise-grade): robust conversation storage with deterministic API.

Contract:
- add_turn(role: str, message: str, **meta) -> None
- get_conversation(session_id: str = "default", limit: int | None = None) -> list[dict]
- clear(session_id: str = "default") -> None

Storage:
- JSONL per session (append-only), atomic-ish writes, safe reads, tolerant to legacy text logs.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryOS:
    def __init__(self, base_dir: Optional[str] = None) -> None:
        repo_root = Path(__file__).resolve().parents[2]  # core/memory -> repo
        self._base = Path(base_dir).resolve() if base_dir else (repo_root / "data" / "memory")
        self._base.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _session_path(self, session_id: str) -> Path:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        safe = "".join(ch for ch in session_id.strip() if ch.isalnum() or ch in ("-", "_", "."))
        if not safe:
            raise ValueError("session_id invalid after sanitization")
        return (self._base / f"{safe}.jsonl").resolve()

    def add_turn(self, role: str, message: str, session_id: str = "default", **meta: Any) -> None:
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role must be a non-empty string")
        if not isinstance(message, str):
            raise ValueError("message must be a string")

        turn: Dict[str, Any] = {
            "ts": time.time(),
            "role": role.strip(),
            "message": message,
        }
        if meta:
            # Keep meta JSON-serializable
            turn["meta"] = self._json_safe(meta)

        path = self._session_path(session_id)
        line = json.dumps(turn, ensure_ascii=False)

        with self._lock:
            # Ensure directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            # Append with explicit encoding
            with path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(line + "\n")

    def get_conversation(self, session_id: str = "default", limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            raise ValueError("limit must be a positive int or None")

        path = self._session_path(session_id)
        if not path.exists():
            return []

        turns: List[Dict[str, Any]] = []
        with self._lock:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # JSONL preferred
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict) and "role" in obj and "message" in obj:
                                turns.append(obj)
                                continue
                        except Exception:
                            pass
                    # Legacy fallback: treat as plain text user message
                    turns.append({"ts": None, "role": "user", "message": line})

        if limit is not None and len(turns) > limit:
            turns = turns[-limit:]
        return turns

    def clear(self, session_id: str = "default") -> None:
        path = self._session_path(session_id)
        with self._lock:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                # hard guarantee: never raise on clear
                pass

    def _json_safe(self, obj: Any) -> Any:
        # Convert meta to JSON-safe values deterministically.
        try:
            json.dumps(obj)
            return obj
        except Exception:
            if isinstance(obj, dict):
                return {str(k): self._json_safe(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [self._json_safe(v) for v in obj]
            if isinstance(obj, (str, int, float, bool)) or obj is None:
                return obj
            return str(obj)


if __name__ == "__main__":
    m = MemoryOS()
    m.clear("test")
    m.add_turn("user", "hello", session_id="test")
    m.add_turn("assistant", "hi!", session_id="test")
    print(m.get_conversation("test"))
