"""Tool subsystem public API (stable exports for the AI Core tool layer)."""

from __future__ import annotations

__version__ = "1.0.0"

from .tool_router import ToolRouter
from .echo_tool import EchoTool
from .browser.browser_tools import BrowserTools
from .file.file_tools import FileTools
from .terminal.terminal_tools import TerminalTools
from .audio.audio_tools import AudioTools
from .video.video_tools import VideoTools

__all__ = (
    "ToolRouter",
    "EchoTool",
    "BrowserTools",
    "FileTools",
    "TerminalTools",
    "AudioTools",
    "VideoTools",
)

if __name__ == "__main__":
    print(__all__)
    print(__version__)
