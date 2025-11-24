import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional


class AgentStateManager:
    """
    AgentStateManager = Verwaltung von Agenten-Zuständen.

    Struktur eines Agenten:
    {
        "agent_id": str,
        "user_id": str,
        "task": str,
        "status": str,              # "created", "running", "paused", "completed", "failed", "aborted"
        "created_at": str,
        "updated_at": str,
        "steps": [
            {
                "id": str,
                "timestamp": str,
                "type": str,        # "plan", "tool_call", "reasoning", "info", "error", "finish", ...
                "description": str,
                "status": str,      # "pending", "running", "done"
                "data": dict
            },
            ...
        ],
        "meta": dict
    }
    """

    def __init__(self):
        self.base_path = "./data/agents"
        os.makedirs(self.base_path, exist_ok=True)

    # ---------- Datei-Helfer ----------

    def _get_agent_file(self, agent_id: str) -> str:
        safe_id = str(agent_id).replace("/", "_")
        return os.path.join(self.base_path, f"{safe_id}.json")

    def _load_agent_file(self, agent_id: str) -> Optional[Dict[str, Any]]:
        file_path = self._get_agent_file(agent_id)
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return None

    def _save_agent_file(self, agent: Dict[str, Any]) -> None:
        agent_id = agent.get("agent_id")
        if not agent_id:
            return
        file_path = self._get_agent_file(agent_id)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(agent, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- Öffentliche API ----------

    def create_agent(self, user_id: str, task: str) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat() + "Z"
        agent_id = str(uuid.uuid4())

        agent = {
            "agent_id": agent_id,
            "user_id": user_id,
            "task": task,
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "steps": [],
            "meta": {},
        }

        self._save_agent_file(agent)
        return agent

    def load_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self._load_agent_file(agent_id)

    def update_agent(
        self,
        agent_id: str,
        status: Optional[str] = None,
        meta_update: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        agent = self._load_agent_file(agent_id)
        if agent is None:
            return None

        changed = False

        if status is not None and status != agent.get("status"):
            agent["status"] = status
            changed = True

        if meta_update:
            meta = agent.get("meta", {})
            if not isinstance(meta, dict):
                meta = {}
            meta.update(meta_update)
            agent["meta"] = meta
            changed = True

        if changed:
            agent["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self._save_agent_file(agent)

        return agent

    def add_step(
        self,
        agent_id: str,
        step_type: str,
        description: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        agent = self._load_agent_file(agent_id)
        if agent is None:
            return None

        steps = agent.get("steps", [])
        if not isinstance(steps, list):
            steps = []

        step = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": step_type,
            "description": description,
            "status": "pending",
            "data": data or {},
        }

        steps.append(step)
        agent["steps"] = steps
        agent["updated_at"] = datetime.utcnow().isoformat() + "Z"

        self._save_agent_file(agent)
        return agent

    def list_agents(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        agents: List[Dict[str, Any]] = []

        if not os.path.exists(self.base_path):
            return agents

        for filename in os.listdir(self.base_path):
            if not filename.endswith(".json"):
                continue
            agent_id = filename[:-5]
            agent = self._load_agent_file(agent_id)
            if not agent:
                continue
            if user_id is not None and agent.get("user_id") != user_id:
                continue
            agents.append(agent)

        def _sort_key(a: Dict[str, Any]) -> str:
            return a.get("created_at", "")

        agents.sort(key=_sort_key, reverse=True)
        return agents
