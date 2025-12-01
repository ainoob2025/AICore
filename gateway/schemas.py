"""
HTTP API schemas for the AI Core gateway.

These dataclasses define the JSON shape of HTTP requests and responses
for the gateway endpoints. They are deliberately decoupled from the
internal kernel types in `core.kernel.types`, but are designed to map
cleanly onto them.

The actual HTTP server implementation (routing, validation, serialization)
will be added in later steps.\n"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class GatewayEndpoint(str, Enum):
    """
    Logical endpoints exposed by the gateway API.

    These values match the intended paths:
    - /chat
    - /tool
    - /planner
    - /agent
    """
    CHAT = "chat"
    TOOL = "tool"
    PLANNER = "planner"
    AGENT = "agent"

@dataclass
class ChatMessageDTO:
    """
    HTTP-level chat message schema.

    This mirrors common chat protocols (role + content) and can be
    constructed directly from user input.
    """
    role: str
    content: str
    name: Optional[str] = None

@dataclass
class ChatRequestDTO:
    """
    Request body for POST /chat.

    - `messages`:  ordered list of ChatMessageDTO items (user, system, assistant).
    - `user_id`:   optional high-level user identifier.
    - `session_id`:optional session identifier used for conversation threading.
    - `locale`:    optional locale hint (e.g. "de-DE").
    - `tools`:     optional list of tool names allowed in this request.
    """
    messages: List[ChatMessageDTO]

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    locale: Optional[str] = None
    tools: Optional[List[str]] = None

    # Optional extra parameters (kept small for now)
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChatResponseDTO:
    """
    Response body for POST /chat.

    - `messages`:       assistant messages returned to the client.
    - `session_id`:     session identifier (may be reused by the client).
    - `request_id`:     server-assigned identifier for tracing.
    - `finish_reason`:  high-level reason (e.g. "stop", "length", "error").
    - `metadata`:       small, structured extras (e.g. timing, tokens).
    """
    messages: List[ChatMessageDTO]
    session_id: Optional[str]
    request_id: str

    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolRequestDTO:
    """
    Request body for POST /tool.

    Allows a client (or later another service) to trigger a direct
    tool call via the gateway.
    """
    tool_name: str
    arguments: Dict[str, Any]

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    locale: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolResponseDTO:
    """
    Response body for POST /tool.
    """
    tool_name: str
    result: Any
    request_id: str
    session_id: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PlannerRequestDTO:
    """
    Request body for POST /planner.

    Encapsulates a high-level goal and optional context. The planner
    will later translate this into plans and steps.
    """
    goal: str
    context: Optional[str] = None

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    locale: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PlannerResponseDTO:
    """
    Response body for POST /planner.

    For now this is a placeholder structure that can later carry
    plan objects, evaluation results, etc.
    """
    request_id: str
    session_id: Optional[str] = None

    # Free-form plan representation (to be refined in Phase 2).
    plan: Any = None

    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentRequestDTO:
    """
    Request body for POST /agent.

    Allows direct interaction with a specific agent (e.g. code, research).
    """
    agent_role: str
    input: str

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    locale: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentResponseDTO:
    """
    Response body for POST /agent.
    """
    request_id: str
    session_id: Optional[str] = None

    output: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ErrorResponseDTO:
    """
    Standard error response schema for the gateway.

    Used for non-2xx responses where the request could not be processed.
    """
    error: str          # short code, e.g. "bad_request", "internal_error"
    message: str        # human-readable description
    request_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


def to_dict(obj: Any) -> Dict[str, Any]:
    """
    Utility helper to convert a dataclass (DTO) into a plain dict that
    can be serialized as JSON by an HTTP framework.

    This is a thin wrapper around dataclasses.asdict to keep the API
    surface explicit.
    """
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    raise TypeError(f"Object of type {type(obj)!r} is not a dataclass instance.")