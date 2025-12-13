"""Tool canonicalization (single source of truth).

Purpose:
- Prevent alias drift (fetch/get/exec/run/etc.)
- Deterministic mapping to ToolRouter methods

Contract:
- canonicalize(name, method, args) -> (name, method, args)
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


def canonicalize(name: Any, method: Any, args: Any) -> Tuple[str, str, Dict[str, Any]]:
    n = str(name).strip() if isinstance(name, str) else ""
    m = str(method).strip() if isinstance(method, str) else ""
    a = args if isinstance(args, dict) else {}

    # Browser
    if n == "browser":
        if m in ("fetch", "get", "get_url", "download", "httpget"):
            m = "http_get"

    # Terminal
    elif n == "terminal":
        if m in ("exec", "run", "cmd"):
            m = "run_cmd"

    # File
    elif n == "file":
        if m == "read":
            m = "read_text"
        elif m == "write":
            m = "write_text"
        elif m in ("ls", "dir"):
            m = "list_dir"
        elif m == "mkdir":
            m = "mkdirs"

    return n, m, a
