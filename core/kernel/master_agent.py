import json
import requests
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import time

from core.memory.memory_core import MemoryCore
from core.memory.episodic_memory import EpisodicMemory
from core.memory.semantic_memory import SemanticMemory
from core.memory.memory_router import MemoryRouter

from core.tools.tool_router import ToolRouter
from core.agents.agent_state import AgentStateManager
from core.agents.agent_factory import AgentFactory
from core.agents.agent_runner import AgentRunner
from core.agents.self_improvement_agent import SelfImprovementAgent

from core.planner.planner import Planner
from core.planner.planner_agent_link import PlannerAgentLink

from core.kernel.request_types import CoreRequest, CoreResponse
from core.kernel.task_feedback import TaskFeedbackLogger


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        if session_id:
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat(),
                }
            return session_id

        new_id = f"{user_id}-chat"
        if new_id not in self._sessions:
            self._sessions[new_id] = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
            }
        return new_id


class MasterAgent:
    def __init__(self):
        with open("models/model_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        self.api_url = config["lmstudio_api_url"]
        self.main_model = config["main_model"]
        self.vision_model = config.get("vision_model")
        self.thinking_model = config.get("thinking_model")

        memory_core = MemoryCore()
        episodic = EpisodicMemory()
        semantic = SemanticMemory()

        self.router = MemoryRouter(
            memory_core=memory_core,
            episodic=episodic,
            semantic=semantic,
        )

        self.tool_router = ToolRouter(
            api_url=self.api_url,
            main_model_id=self.main_model,
            vision_model_id=self.vision_model,
            thinking_model_id=self.thinking_model,
        )

        self.agent_state_manager = AgentStateManager()
        self.agent_factory = AgentFactory()
        self.agent_runner = AgentRunner()
        self.planner = Planner()
        self.plan_agent_link = PlannerAgentLink()

        self.session_manager = SessionManager()

        self._memory_core = memory_core
        self._episodic = episodic
        self._semantic = semantic

        self._log_path = Path("data/logs/core.log")
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

        self.task_logger = TaskFeedbackLogger()
        self.self_improvement = SelfImprovementAgent()

    # ----------------------------------------------------------------------
    # LOGGING
    # ----------------------------------------------------------------------

    def _log_core_event(self, trace_id: str, event: str, data: Dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id,
            "event": event,
            "data": data,
        }
        try:
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ----------------------------------------------------------------------
    # CENTRAL REQUEST HANDLER
    # ----------------------------------------------------------------------

    def handle_request(self, core_request: CoreRequest) -> CoreResponse:
        trace_id = core_request.trace_id or str(uuid.uuid4())

        session_id = self.session_manager.get_or_create_session(
            user_id=core_request.user_id,
            session_id=core_request.session_id,
        )

        response = CoreResponse(
            trace_id=trace_id,
            messages=[],
            tool_calls=[],
            memory_ops=[],
            planner_trace=[],
            agent_updates={},
            errors=[],
        )

        started_at = time.perf_counter()
        used_tools = []

        # ---------------- SELF-IMPROVEMENT ----------------
        if core_request.input_type == "self_improve":
            strategies = self.run_self_improvement()
            response.messages.append(
                {"role": "assistant", "content": json.dumps(strategies, ensure_ascii=False)}
            )
            self._log_task_feedback(core_request, response, started_at, used_tools=[])
            return response

        # ---------------- CHAT ----------------
        if core_request.input_type == "chat":
            reply_dict = self.handle_message(core_request.user_id, core_request.message or "")
            response.messages.append({"role": "assistant", "content": reply_dict.get("reply", "")})
            self._log_task_feedback(core_request, response, started_at, used_tools=used_tools)
            return response

        # ---------------- TOOL ----------------
        if core_request.input_type == "tool":
            tool_name = core_request.tool_name or ""
            tool_payload = core_request.tool_payload or {}
            result = self.call_tool(core_request.user_id, tool_name, tool_payload)
            response.tool_calls.append({"tool": tool_name, "result": result})
            used_tools = [tool_name] if tool_name else []
            self._log_task_feedback(core_request, response, started_at, used_tools=used_tools)
            return response

        # ---------------- TOOL SELECT (LLM-gesteuerte Auswahl) ----------------
        if core_request.input_type == "tool_select":
            step_description = core_request.message or ""
            selection_context: Dict[str, Any] = {
                "user_id": core_request.user_id,
                "session_id": session_id,
                "context_hints": core_request.context_hints,
                "payload": core_request.tool_payload or {},
            }

            candidates = self.tool_router.select_tools(
                step_description=step_description,
                context=selection_context,
            )

            response.tool_calls.append(
                {
                    "mode": "tool_select",
                    "step_description": step_description,
                    "candidates": candidates,
                }
            )
            self._log_task_feedback(core_request, response, started_at, used_tools=used_tools)
            return response

        # ---------------- PLANNER ONLY ----------------
        if core_request.input_type == "planner":
            task = core_request.message or ""
            plan = self.planner.create_plan(task)
            response.planner_trace.append(plan)
            self._log_task_feedback(core_request, response, started_at, used_tools=used_tools)
            return response

        # ---------------- PLANNER + AGENT ----------------
        if core_request.input_type == "planner_agent":
            task = core_request.message or ""
            template = core_request.tool_name
            result = self.plan_agent_link.create_plan_and_agent(
                user_id=core_request.user_id,
                task=task,
                template_name=template,
            )
            response.planner_trace.append(result.get("plan"))
            response.agent_updates = result.get("agent")
            self._log_task_feedback(core_request, response, started_at, used_tools=used_tools)
            return response

        # ---------------- AGENT STEP ----------------
        if core_request.input_type == "agent_step":
            payload = core_request.tool_payload or {}
            agent_id = payload.get("agent_id")
            step_type = payload.get("step_type")
            description = payload.get("description")
            data = payload.get("data", {})

            updated_agent = self.agent_state_manager.add_step(
                agent_id=agent_id,
                step_type=step_type,
                description=description,
                data=data,
            )

            response.agent_updates = updated_agent
            self._log_task_feedback(core_request, response, started_at, used_tools=used_tools)
            return response

        # ---------------- AGENT RUN ----------------
        if core_request.input_type == "agent_run":
            payload = core_request.tool_payload or {}
            agent_id = payload.get("agent_id")

            runner_result = self.agent_runner.run_next_step(agent_id)

            response.agent_updates = runner_result
            self._log_task_feedback(core_request, response, started_at, used_tools=used_tools)
            return response

        # ---------------- FALLBACK ----------------
        self._log_task_feedback(core_request, response, started_at, used_tools=used_tools)
        return response

    # ----------------------------------------------------------------------
    # CHAT
    # ----------------------------------------------------------------------

    def handle_message(self, user_id: str, message: str) -> dict:
        self.router.on_user_message(user_id, message)

        context_messages = self.router.build_llm_context(user_id, limit=10)

        payload = {"model": self.main_model, "messages": context_messages}

        try:
            response = requests.post(self.api_url, json=payload)
            data = response.json()
            reply = data["choices"][0]["message"]["content"]

            self.router.on_assistant_reply(user_id, reply, message)
            return {"reply": reply}

        except Exception as e:
            self._episodic.add_event(user_id, "error", {"error": str(e)}, ["exception"])
            return {"reply": "Fehler beim Modellaufruf.", "info": str(e)}

    # ----------------------------------------------------------------------
    # TOOLS
    # ----------------------------------------------------------------------

    def call_tool(self, user_id: str, tool_name: str, payload: dict) -> dict:
        result = self.tool_router.route_tool_call(tool_name, payload)

        self._episodic.add_event(
            user_id,
            "tool_call",
            {"tool_name": tool_name, "payload": payload, "result": result},
            ["tool", tool_name],
        )

        return result

    # ----------------------------------------------------------------------
    # MEMORY API (für Gateway-Endpunkte /episodes und /semantic)
    # ----------------------------------------------------------------------

    def get_recent_events(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Liefert die letzten Episoden-Einträge für einen User.

        Defensiv implementiert:
        - Versucht bekannte Methoden der EpisodicMemory-Implementierung zu nutzen.
        - Bei Fehlern oder unbekannten Implementationen wird [] zurückgegeben.
        """
        try:
            # häufigster Fall: direkte API
            if hasattr(self._episodic, "get_recent_events"):
                return self._episodic.get_recent_events(user_id=user_id, limit=limit)  # type: ignore[arg-type]

            # alternativer Name
            if hasattr(self._episodic, "list_recent_events"):
                return self._episodic.list_recent_events(user_id=user_id, limit=limit)  # type: ignore[arg-type]
        except Exception:
            pass
        return []

    def get_semantic_memory(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Liefert semantisches Wissen für einen User.

        Defensiv implementiert:
        - Versucht bekannte Methoden der SemanticMemory-Implementierung zu nutzen.
        - Bei Fehlern oder unbekannten Implementationen wird [] zurückgegeben.
        """
        try:
            if hasattr(self._semantic, "get_semantic_memory"):
                return self._semantic.get_semantic_memory(user_id=user_id, limit=limit)  # type: ignore[arg-type]

            if hasattr(self._semantic, "query_user_knowledge"):
                return self._semantic.query_user_knowledge(user_id=user_id, limit=limit)  # type: ignore[arg-type]

            if hasattr(self._semantic, "get_top_k"):
                return self._semantic.get_top_k(user_id=user_id, k=limit)  # type: ignore[arg-type]
        except Exception:
            pass
        return []

    # ----------------------------------------------------------------------
    # THINKER ASSIST
    # ----------------------------------------------------------------------

    def run_thinker_assist(self, user_id: str, question: str) -> dict:
        thinking_payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a pure logic reasoner. Provide detailed reasoning only, "
                        "not a final user-facing answer."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Analyze this question step-by-step and provide all intermediate reasoning:\n"
                        f"{question}"
                    ),
                },
            ]
        }

        thinking_result = self.call_tool(user_id, "thinking_reason", thinking_payload)

        if not thinking_result.get("ok", False):
            return {"reply": "Das Thinker-Modell konnte die Analyse nicht durchführen."}

        thinking_output = thinking_result.get("result", "")

        josie_messages = [
            {
                "role": "system",
                "content": (
                    "You are Josie. You receive reasoning from a dedicated thinking model. "
                    "Produce the final answer in German.\n\n"
                    f"Reasoning (hidden):\n{thinking_output}"
                ),
            },
            {"role": "user", "content": question},
        ]

        payload = {"model": self.main_model, "messages": josie_messages}

        try:
            response = requests.post(self.api_url, json=payload)
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            self.router.on_assistant_reply(user_id, reply, question)
            return {"reply": reply}
        except Exception as e:
            return {"reply": "Fehler im Thinker-Assist.", "info": str(e)}

    def run_self_improvement(self) -> dict:
        """
        Führt Phase-6-Self-Improvement aus.
        Nutzt SelfImprovementAgent.run_analysis().

        Rückgabewert:
            dict – die neu erstellten Strategien.
        """
        try:
            return self.self_improvement.run_analysis()
        except Exception:
            return {"ok": False, "error": "Self-improvement failed"}

    def _log_task_feedback(
        self,
        core_request: CoreRequest,
        response: CoreResponse,
        started_at: float,
        used_tools=None,
    ):
        if used_tools is None:
            used_tools = []
        try:
            duration = max(time.perf_counter() - started_at, 0.0)

            goal = ""
            if core_request.input_type == "chat":
                goal = core_request.message or ""
            elif core_request.input_type == "tool":
                goal = core_request.tool_name or ""
            elif core_request.input_type in {"planner", "planner_agent"}:
                payload = core_request.tool_payload or {}
                goal = str(payload.get("task") or payload.get("goal") or "")

            error_entries = []
            for err in response.errors or []:
                try:
                    if hasattr(err, "dict"):
                        error_entries.append(err.dict())
                    elif hasattr(err, "model_dump"):
                        error_entries.append(err.model_dump())
                    else:
                        error_entries.append(str(err))
                except Exception:
                    error_entries.append(str(err))

            entry = {
                "task_id": response.trace_id,
                "user_id": core_request.user_id,
                "session_id": core_request.session_id,
                "input_type": core_request.input_type,
                "goal": goal,
                "result_quality": "unknown",
                "used_tools": used_tools,
                "plan_structure": response.planner_trace or [],
                "duration_sec": duration,
                "errors": error_entries,
            }

            self.task_logger.log_entry(entry)
        except Exception:
            pass
