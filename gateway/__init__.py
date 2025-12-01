"""
Gateway package for AI Core.

The gateway exposes a local HTTP API (e.g. /chat, /tool, /planner, /agent)
for UIs and external clients. It translates HTTP requests into internal
kernel requests and returns HTTP responses based on kernel responses.

This package currently provides only schema definitions. The actual
HTTP server and routing will be implemented in later phases.\n"""

from .schemas import (
    ChatMessageDTO,
    ChatRequestDTO,
    ChatResponseDTO,
    ToolRequestDTO,
    ToolResponseDTO,
    PlannerRequestDTO,
    PlannerResponseDTO,
    AgentRequestDTO,
    AgentResponseDTO,
    ErrorResponseDTO,
)

__all__ = [
    "ChatMessageDTO",
    "ChatRequestDTO",
    "ChatResponseDTO",
    "ToolRequestDTO",
    "ToolResponseDTO",
    "PlannerRequestDTO",
    "PlannerResponseDTO",
    "AgentRequestDTO",
    "AgentResponseDTO",
    "ErrorResponseDTO",
]