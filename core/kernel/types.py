"""
Internal kernel base types for AI Core.

These types define the canonical internal structures for requests,
responses and errors handled by the MasterAgent and core services.

Design principles:
- Pure Python dataclasses and enums (no external dependencies).
- Stable field names that map cleanly to JSON for transport.
- Explicit separation of internal roles/channels from HTTP-layer schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Channel(str, Enum):
    """
    High-level channel indicating the type of operation requested from
    the kernel.

    - chat:    Standard conversational requests.
    - tool:    Direct tool invocations.
    - planner: Planner-centric operations (plans, evaluations).
    - agent:   Direct agent operations (start, step, inspect).
    """
    CHAT = "chat"
    TOOL = "tool"
    PLANNER = "planner"
    AGENT = "agent"


class Role(str, Enum):
    """
    Generic message role used across the system.
    Compatible with common chat schemas.
    """
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

@dataclass
class Message:
    """
    Internal message representation used by the kernel.

    Notes:
    - `role` uses the Role enum above.
    - `content` is plain text for now; richer content types can be added later.
    - `metadata` allows attaching small, structured hints (e.g. source, tags).
    """
    role: Role
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolCall:
    """
    Representation of a single tool call issued by the kernel or a model.
    """
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class KernelError:
    """
    Structured error information propagated inside the kernel.

    - `code`:   Short, stable machine-readable error code.
    - `message`:Human-readable description (English, internal).
    - `details`:Optional structured payload with extra information.
    """
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class KernelRequest:
    """
    Canonical internal request type for the kernel.

    This is what the gateway and other services should translate into
    before handing a task to the MasterAgent.
    """
    request_id: str
    channel: Channel

    # Identity and session
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Conversation / content
    messages: List[Message] = field(default_factory=list)

    # Localisation & models
    locale: Optional[str] = None  # e.g. "de-DE", "en-US"
    model: Optional[str] = None   # logical model identifier, not a provider ID

    # Execution hints
    tools: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

    # Free-form metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class KernelResponse:
    """
    Canonical internal response type from the kernel.

    The kernel should always attempt to return a KernelResponse object:
    - `messages` contains the assistant-side messages produced.
    - `tool_calls` lists any tool invocations requested by the model.
    - `finished` indicates whether this response is final for the request.
    - `error` is populated if the request failed.
    """
    request_id: str
    session_id: Optional[str]

    messages: List[Message] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)

    finished: bool = True
    error: Optional[KernelError] = None

    metadata: Dict[str, Any] = field(default_factory=dict)