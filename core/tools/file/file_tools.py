"""FileTools (enterprise-grade): safe filesystem operations with path confinement."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class FileTools:
    def __init__(self, base_dir: Optional[str] = None) -> None:
        # Default: repository root (two levels up: core/tools/file -> repo)
        repo_root = Path(__file__).resolve().parents[3]
        self._base = Path(base_dir).resolve() if base_dir else repo_root

    def _resolve_safe(self, p: str) -> Path:
        if not isinstance(p, str) or not p:
            raise ValueError("path must be a non-empty string")
        target = (self._base / p).resolve()
        # Confinement: prevent directory traversal outside base
        if self._base != target and self._base not in target.parents:
            raise PermissionError("path escapes base directory")
        return target

    def run(self, method: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not isinstance(method, str) or not method:
                return {"ok": False, "error": "INVALID_METHOD", "details": {"method": method}}
            if not isinstance(args, dict):
                return {"ok": False, "error": "INVALID_ARGS", "details": {"type": type(args).__name__}}

            if method == "exists":
                path = self._resolve_safe(args.get("path", ""))
                return {"ok": True, "exists": path.exists()}

            if method == "mkdirs":
                path = self._resolve_safe(args.get("path", ""))
                path.mkdir(parents=True, exist_ok=True)
                return {"ok": True, "path": str(path)}

            if method == "list_dir":
                path = self._resolve_safe(args.get("path", "."))
                if not path.exists() or not path.is_dir():
                    return {"ok": False, "error": "NOT_A_DIRECTORY", "details": {"path": str(path)}}
                entries: List[Dict[str, Any]] = []
                for child in sorted(path.iterdir(), key=lambda x: x.name.lower()):
                    try:
                        st = child.stat()
                        entries.append({
                            "name": child.name,
                            "path": str(child),
                            "is_dir": child.is_dir(),
                            "size": st.st_size,
                        })
                    except Exception:
                        entries.append({
                            "name": child.name,
                            "path": str(child),
                            "is_dir": child.is_dir(),
                            "size": None,
                        })
                return {"ok": True, "path": str(path), "entries": entries}

            if method == "read_text":
                path = self._resolve_safe(args.get("path", ""))
                encoding = args.get("encoding", "utf-8")
                max_chars = args.get("max_chars", 2_000_000)
                if not isinstance(encoding, str) or not encoding:
                    return {"ok": False, "error": "INVALID_ENCODING", "details": {"encoding": encoding}}
                if not isinstance(max_chars, int) or max_chars <= 0:
                    return {"ok": False, "error": "INVALID_MAX_CHARS", "details": {"max_chars": max_chars}}
                if not path.exists() or not path.is_file():
                    return {"ok": False, "error": "NOT_A_FILE", "details": {"path": str(path)}}
                text = path.read_text(encoding=encoding, errors="strict")
                truncated = len(text) > max_chars
                return {"ok": True, "path": str(path), "text": text[:max_chars], "truncated": truncated}

            if method == "write_text":
                path = self._resolve_safe(args.get("path", ""))
                encoding = args.get("encoding", "utf-8")
                text = args.get("text", "")
                mkdirs = args.get("mkdirs", True)
                if not isinstance(encoding, str) or not encoding:
                    return {"ok": False, "error": "INVALID_ENCODING", "details": {"encoding": encoding}}
                if not isinstance(text, str):
                    return {"ok": False, "error": "INVALID_TEXT", "details": {"type": type(text).__name__}}
                if mkdirs:
                    path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding=encoding, errors="strict")
                return {"ok": True, "path": str(path), "bytes": len(text.encode(encoding, errors="strict"))}

            return {"ok": False, "error": "UNKNOWN_METHOD", "details": {"method": method}}
        except Exception as exc:
            return {"ok": False, "error": "FILETOOLS_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}


if __name__ == "__main__":
    ft = FileTools()
    print(ft.run("exists", {"path": "core/tools/file/file_tools.py"}))
