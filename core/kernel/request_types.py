from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CoreRequest(BaseModel):
    """
    Einheitliche Eingangsnachricht für den Kernel.

    input_type unterstützt aktuell:
      - "chat"
      - "tool"
      - "tool_select"
      - "planner"
      - "planner_agent"
      - "agent_step"
      - "agent_run"
    """
    trace_id: str
    session_id: str
    user_id: str
    input_type: str
    message: Optional[str] = None
    tool_name: Optional[str] = None
    tool_payload: Optional[Dict[str, Any]] = None
    context_hints: List[str] = []


class CoreError(BaseModel):
    """
    Mini-Exception-Schema für strukturierte Fehler.
    """
    trace_id: str
    error_type: str
    message: str
    details: Dict[str, Any] = {}
    severity: str = "error"  # info | warn | error | fatal


class CoreResponse(BaseModel):
    """
    Einheitliche Kernel-Antwort.
    """
    trace_id: str
    messages: List[Dict[str, Any]] = []
    tool_calls: List[Dict[str, Any]] = []
    memory_ops: List[Dict[str, Any]] = []
    planner_trace: List[Dict[str, Any]] = []
    agent_updates: Dict[str, Any] = {}
    errors: List[CoreError] = []
