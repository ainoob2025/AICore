"""Enterprise-grade ToolRouter for AI Core.
Deterministic results, strict validation, robust error handling.
"""

from __future__ import annotations

import logging
from typing import TypedDict, List, Dict, Any

from .browser.browser_tools import BrowserTools
from .file.file_tools import FileTools
from .terminal.terminal_tools import TerminalTools
from .audio.audio_tools import AudioTools
from .video.video_tools import VideoTools
from .echo_tool import EchoTool
from .ping_tool import PingTool


class ToolCall(TypedDict):
    name: str
    method: str
    args: Dict[str, Any]


class ToolResult(TypedDict):
    ok: bool
    name: str
    method: str
    result: Dict[str, Any] | None
    error: str | None
    details: Dict[str, Any] | None


ERROR_INVALID_TOOL_CALL = "INVALID_TOOL_CALL"
ERROR_UNKNOWN_TOOL = "UNKNOWN_TOOL"
ERROR_TOOL_EXCEPTION = "TOOL_EXCEPTION"


class ToolRouter:
    def __init__(self) -> None:
        self._log = logging.getLogger(__name__)
        self._tools: Dict[str, Any] = {
            "browser": BrowserTools(),
            "file": FileTools(),
            "terminal": TerminalTools(),
            "audio": AudioTools(),
            "video": VideoTools(),
            "echo": EchoTool(),
            "ping": PingTool(),
        }

    def available_tools(self) -> List[str]:
        return sorted(self._tools.keys())

    def execute(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        results: List[ToolResult] = []

        for call in tool_calls:
            name = call.get("name")
            method = call.get("method")
            args = call.get("args")

            if not isinstance(name, str) or not name or not isinstance(method, str) or not method or not isinstance(args, dict):
                results.append({
                    "ok": False,
                    "name": str(name),
                    "method": str(method),
                    "result": None,
                    "error": ERROR_INVALID_TOOL_CALL,
                    "details": {"call": call},
                })
                continue

            tool = self._tools.get(name)
            if tool is None:
                results.append({
                    "ok": False,
                    "name": name,
                    "method": method,
                    "result": None,
                    "error": ERROR_UNKNOWN_TOOL,
                    "details": {"available": self.available_tools()},
                })
                continue

            self._log.info("Tool call start", extra={"tool": name, "method": method, "args_keys": list(args.keys())})

            try:
                result = tool.run(method, args)
                results.append({
                    "ok": True,
                    "name": name,
                    "method": method,
                    "result": result,
                    "error": None,
                    "details": None,
                })
                self._log.info("Tool call end", extra={"tool": name, "method": method})
            except Exception as exc:
                self._log.exception("Tool exception", extra={"tool": name, "method": method})
                results.append({
                    "ok": False,
                    "name": name,
                    "method": method,
                    "result": None,
                    "error": ERROR_TOOL_EXCEPTION,
                    "details": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                })

        return results


if __name__ == "__main__":
    router = ToolRouter()
    print(router.available_tools())
    print(router.execute([{"name": "echo", "method": "echo", "args": {"text": "ping"}}]))
    print(router.execute([{"name": "ping", "method": "get", "args": {}}]))
