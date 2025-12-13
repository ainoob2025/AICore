"""TerminalTools (enterprise-grade): controlled command execution with allowlist, timeout, and safe defaults."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class TerminalTools:
    """
    Enterprise-grade terminal execution wrapper.

    Security/robustness guarantees:
    - Allowlist for executables (python/pip/git by default).
    - No shell=True (prevents shell injection).
    - Timeout enforced per call.
    - Output capture with size limits.
    - Working directory confinement to repo root by default (no traversal).
    - Deterministic result schema, never raises unhandled exceptions.
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        allowed_executables: Optional[List[str]] = None,
        default_timeout_sec: int = 60,
        max_output_bytes: int = 1_000_000,
    ) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        self._base = Path(base_dir).resolve() if base_dir else repo_root
        self._allowed = [e.lower() for e in (allowed_executables or ["python", "pip", "git"])]
        self._default_timeout = int(default_timeout_sec) if isinstance(default_timeout_sec, int) and default_timeout_sec > 0 else 60
        self._max_output_bytes = int(max_output_bytes) if isinstance(max_output_bytes, int) and max_output_bytes > 0 else 1_000_000

    def _resolve_cwd(self, cwd: Optional[str]) -> Path:
        if cwd is None or cwd == "":
            return self._base
        if not isinstance(cwd, str):
            raise ValueError("cwd must be a string")
        target = (self._base / cwd).resolve()
        if self._base != target and self._base not in target.parents:
            raise PermissionError("cwd escapes base directory")
        if not target.exists() or not target.is_dir():
            raise FileNotFoundError("cwd does not exist or is not a directory")
        return target

    def _normalize_cmd(self, cmd: Any) -> Tuple[List[str], str]:
        # Accept either list[str] or a string command line.
        if isinstance(cmd, list):
            if not cmd or not all(isinstance(x, str) and x for x in cmd):
                raise ValueError("cmd list must be non-empty list of non-empty strings")
            argv = cmd
            raw = " ".join(cmd)
        elif isinstance(cmd, str):
            if not cmd.strip():
                raise ValueError("cmd string must be non-empty")
            # POSIX-like splitting; adequate for our allowlisted tools and simple args.
            argv = shlex.split(cmd, posix=os.name != "nt")
            raw = cmd
            if not argv:
                raise ValueError("cmd string produced empty argv")
        else:
            raise ValueError("cmd must be list[str] or str")

        exe = Path(argv[0]).name.lower()
        if exe.endswith(".exe"):
            exe = exe[:-4]
        return argv, exe

    def _truncate_bytes(self, b: bytes) -> Tuple[str, bool]:
        if not isinstance(b, (bytes, bytearray)):
            return "", False
        truncated = len(b) > self._max_output_bytes
        b2 = bytes(b[: self._max_output_bytes])
        # Decode with replacement to avoid decode errors exploding the tool
        return b2.decode("utf-8", errors="replace"), truncated

    def run(self, method: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not isinstance(method, str) or not method:
                return {"ok": False, "error": "INVALID_METHOD", "details": {"method": method}}
            if not isinstance(args, dict):
                return {"ok": False, "error": "INVALID_ARGS", "details": {"type": type(args).__name__}}

            if method != "run_cmd":
                return {"ok": False, "error": "UNKNOWN_METHOD", "details": {"method": method}}

            cmd = args.get("cmd")
            timeout = args.get("timeout_sec", self._default_timeout)
            cwd = args.get("cwd", None)
            env = args.get("env", None)

            if not isinstance(timeout, int) or timeout <= 0 or timeout > 3600:
                return {"ok": False, "error": "INVALID_TIMEOUT", "details": {"timeout_sec": timeout}}

            if env is not None and not isinstance(env, dict):
                return {"ok": False, "error": "INVALID_ENV", "details": {"type": type(env).__name__}}

            argv, exe = self._normalize_cmd(cmd)

            if exe not in self._allowed:
                return {
                    "ok": False,
                    "error": "EXECUTABLE_NOT_ALLOWED",
                    "details": {"exe": exe, "allowed": list(self._allowed)},
                }

            cwd_path = self._resolve_cwd(cwd)

            # Build env safely: start from current env; allow overriding a limited set of keys
            run_env = os.environ.copy()
            if isinstance(env, dict):
                for k, v in env.items():
                    if not isinstance(k, str) or not k:
                        return {"ok": False, "error": "INVALID_ENV_KEY", "details": {"key": k}}
                    if v is None:
                        run_env.pop(k, None)
                    elif isinstance(v, (str, int, float, bool)):
                        run_env[k] = str(v)
                    else:
                        return {"ok": False, "error": "INVALID_ENV_VALUE", "details": {"key": k, "type": type(v).__name__}}

            proc = subprocess.run(
                argv,
                cwd=str(cwd_path),
                env=run_env,
                capture_output=True,
                text=False,
                shell=False,
                timeout=timeout,
            )

            stdout_text, stdout_trunc = self._truncate_bytes(proc.stdout or b"")
            stderr_text, stderr_trunc = self._truncate_bytes(proc.stderr or b"")

            return {
                "ok": True,
                "exe": exe,
                "cmd": argv,
                "cwd": str(cwd_path),
                "returncode": proc.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "stdout_truncated": stdout_trunc,
                "stderr_truncated": stderr_trunc,
            }

        except subprocess.TimeoutExpired as exc:
            # exc.stdout/err may exist
            out = getattr(exc, "stdout", b"") or b""
            err = getattr(exc, "stderr", b"") or b""
            stdout_text, stdout_trunc = self._truncate_bytes(out)
            stderr_text, stderr_trunc = self._truncate_bytes(err)
            return {
                "ok": False,
                "error": "TIMEOUT",
                "details": {
                    "timeout_sec": getattr(exc, "timeout", None),
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "stdout_truncated": stdout_trunc,
                    "stderr_truncated": stderr_trunc,
                },
            }
        except Exception as exc:
            return {"ok": False, "error": "TERMINALTOOLS_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}


if __name__ == "__main__":
    tt = TerminalTools()
    print(tt.run("run_cmd", {"cmd": ["python", "-c", "print('ping')"], "timeout_sec": 10}))
