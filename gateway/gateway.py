import json
import requests
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.memory.memory_core import MemoryCore
from core.memory.episodic_memory import EpisodicMemory
from core.memory.semantic_memory import SemanticMemory
from core.memory.memory_router import MemoryRouter

from core.tools.tool_router import ToolRouter
from core.agents.agent_state import AgentStateManager
from core.agents.agent_factory import AgentFactory
from core.agents.agent_runner import AgentRunner

from core.planner.planner import Planner
from core.planner.planner_agent_link import PlannerAgentLink

from core.kernel.request_types import CoreRequest, CoreResponse


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        if session_id:
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            return session_id

        new_id = f"{user_id}-chat"
        if new_id not in self._sessions:
            self._sessions[new_id] = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat()
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

        # ---------------- CHAT ----------------
        if core_request.input_type == "chat":
            reply_dict = self.handle_message(core_request.user_id, core_request.message or "")
            response.messages.append({"role": "assistant", "content": reply_dict.get("reply", "")})
            return response

        # ---------------- TOOL ----------------
        if core_request.input_type == "tool":
            tool_name = core_request.tool_name or ""
            tool_payload = core_request.tool_payload or {}
            result = self.call_tool(core_request.user_id, tool_name, tool_payload)
            response.tool_calls.append({"tool": tool_name, "result": result})
            return response

        # ---------------- PLANNER ONLY ----------------
        if core_request.input_type == "planner":
            task = core_request.message or ""
            plan = self.planner.create_plan(task)
            response.planner_trace.append(plan)
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
            return response

        # ---------------- AGENT RUN (NEU) ----------------
        if core_request.input_type == "agent_run":
            payload = core_request.tool_payload or {}
            agent_id = payload.get("agent_id")

            runner_result = self.agent_runner.run_next_step(agent_id)

            response.agent_updates = runner_result
            return response

        # ---------------- FALLBACK ----------------
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
import uuid
from typing import Dict, Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from core.kernel.master_agent import MasterAgent
from core.kernel.request_types import CoreRequest

app = FastAPI()

master_agent = MasterAgent()


class UserMessage(BaseModel):
    user_id: str
    message: str


class ToolCall(BaseModel):
    user_id: str
    tool: str
    payload: Optional[Dict[str, Any]] = None


class ThinkerRequest(BaseModel):
    user_id: str
    question: str


class PlannerRequest(BaseModel):
    user_id: str
    task: str


class AgentCreateRequest(BaseModel):
    user_id: str
    task: str
    template: str


class AgentStepRequest(BaseModel):
    agent_id: str
    step_type: str
    description: str
    data: Optional[Dict[str, Any]] = None


class AgentRunRequest(BaseModel):
    agent_id: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "local-ai-core"}


@app.post("/chat")
def chat_endpoint(data: UserMessage):
    core_request = CoreRequest(
        trace_id=str(uuid.uuid4()),
        session_id=f"{data.user_id}-chat",
        user_id=data.user_id,
        input_type="chat",
        message=data.message,
        tool_name=None,
        tool_payload=None,
        context_hints=[],
    )
    core_response = master_agent.handle_request(core_request)
    reply_text = ""
    if core_response.messages:
        reply_text = core_response.messages[0].get("content", "")
    return {"reply": reply_text}


@app.post("/tool")
def tool_endpoint(data: ToolCall):
    payload = data.payload or {}
    core_request = CoreRequest(
        trace_id=str(uuid.uuid4()),
        session_id=f"{data.user_id}-chat",
        user_id=data.user_id,
        input_type="tool",
        message=None,
        tool_name=data.tool,
        tool_payload=payload,
        context_hints=[],
    )
    core_response = master_agent.handle_request(core_request)
    tool_result: Any = None
    if core_response.tool_calls:
        tool_result = core_response.tool_calls[0].get("result")
    return {
        "user_id": data.user_id,
        "tool": data.tool,
        "result": tool_result,
    }


@app.post("/thinker_assist")
def thinker_assist_endpoint(data: ThinkerRequest):
    return master_agent.run_thinker_assist(
        user_id=data.user_id,
        question=data.question,
    )


@app.post("/planner")
def planner_endpoint(data: PlannerRequest):
    core_request = CoreRequest(
        trace_id=str(uuid.uuid4()),
        session_id=f"{data.user_id}-planner",
        user_id=data.user_id,
        input_type="planner",
        message=data.task,
        tool_name=None,
        tool_payload=None,
        context_hints=[],
    )
    core_response = master_agent.handle_request(core_request)
    return {
        "user_id": data.user_id,
        "task": data.task,
        "plans": core_response.planner_trace or [],
    }


@app.post("/agent/create")
def agent_create_endpoint(data: AgentCreateRequest):
    core_request = CoreRequest(
        trace_id=str(uuid.uuid4()),
        session_id=f"{data.user_id}-planner-agent",
        user_id=data.user_id,
        input_type="planner_agent",
        message=data.task,
        tool_name=data.template,
        tool_payload=None,
        context_hints=[],
    )
    core_response = master_agent.handle_request(core_request)
    return {
        "user_id": data.user_id,
        "task": data.task,
        "template": data.template,
        "agent": core_response.agent_updates,
        "plans": core_response.planner_trace or [],
    }


@app.post("/agent/step")
def agent_step_endpoint(data: AgentStepRequest):
    core_request = CoreRequest(
        trace_id=str(uuid.uuid4()),
        session_id=f"{data.agent_id}-steps",
        user_id="system",
        input_type="agent_step",
        message=None,
        tool_name=None,
        tool_payload={
            "agent_id": data.agent_id,
            "step_type": data.step_type,
            "description": data.description,
            "data": data.data or {},
        },
        context_hints=[]
    )
    core_response = master_agent.handle_request(core_request)
    return {"agent": core_response.agent_updates}


@app.post("/agent/run")
def agent_run_endpoint(data: AgentRunRequest):
    core_request = CoreRequest(
        trace_id=str(uuid.uuid4()),
        session_id=f"{data.agent_id}-run",
        user_id="system",
        input_type="agent_run",
        message=None,
        tool_name=None,
        tool_payload={"agent_id": data.agent_id},
        context_hints=[],
    )
    core_response = master_agent.handle_request(core_request)
    return {"result": core_response.agent_updates}


@app.get("/episodes/{user_id}")
def get_episodes(user_id: str, limit: int = 20):
    return {"user_id": user_id, "events": master_agent.get_recent_events(user_id, limit)}


@app.get("/semantic/{user_id}")
def get_semantic(user_id: str, limit: int = 20):
    return {"user_id": user_id, "knowledge": master_agent.get_semantic_memory(user_id, limit)}
