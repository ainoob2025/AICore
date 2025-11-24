import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from core.agents.agent_state import AgentStateManager


class AgentRunner:
    """
    Mini-AgentRunner (Phase 2):
    - Holt den nächsten ungeprüften Schritt (status=pending)
    - Markiert Schritte als erledigt (done)
    - Fügt Runner-Ereignisse hinzu
    - Keine Tool-Ausführung (kommt Phase 3/4)
    """

    def __init__(self):
        self.agent_state = AgentStateManager()

    # --------------------------------------------------------------------------
    # Hilfsfunktionen
    # --------------------------------------------------------------------------

    def _find_next_step(self, agent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Liefert ersten Schritt mit status = pending.
        """
        steps = agent.get("steps", [])
        for step in steps:
            if step.get("status", "pending") == "pending":
                return step
        return None

    def _update_step_status(self, agent: Dict[str, Any], step_id: str, new_status: str) -> Dict[str, Any]:
        """
        Setzt Status eines Steps und speichert Agent.
        """
        for step in agent.get("steps", []):
            if step.get("id") == step_id:
                step["status"] = new_status
                step["completed_at"] = datetime.utcnow().isoformat() + "Z"

        agent["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self.agent_state._save_agent_file(agent)
        return agent

    # --------------------------------------------------------------------------
    # Runner-API
    # --------------------------------------------------------------------------

    def get_next_step(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Gibt den nächsten unbearbeiteten Schritt zurück.
        """
        agent = self.agent_state.load_agent(agent_id)
        if not agent:
            return None

        return self._find_next_step(agent)

    def mark_step_done(self, agent_id: str, step_id: str) -> Optional[Dict[str, Any]]:
        """
        Markiert einen Schritt als erledigt.
        """
        agent = self.agent_state.load_agent(agent_id)
        if not agent:
            return None

        return self._update_step_status(agent, step_id, "done")

    def run_next_step(self, agent_id: str) -> Dict[str, Any]:
        """
        Führt den nächsten Schritt „logisch“ aus.
        Noch KEINE Tool-Ausführung.
        Nur:
        - Step holen
        - Step als 'running' markieren
        - Step als 'done' markieren
        """

        agent = self.agent_state.load_agent(agent_id)
        if not agent:
            return {
                "ok": False,
                "error": "Agent not found",
                "agent_id": agent_id
            }

        next_step = self._find_next_step(agent)
        if not next_step:
            return {
                "ok": True,
                "message": "No pending steps",
                "agent_id": agent_id
            }

        step_id = next_step.get("id")

        # Schritt „starten“
        next_step["status"] = "running"
        next_step["started_at"] = datetime.utcnow().isoformat() + "Z"
        self.agent_state._save_agent_file(agent)

        # Phase 2 → keine echte Ausführung, nur Abschluss
        updated_agent = self._update_step_status(agent, step_id, "done")

        return {
            "ok": True,
            "agent_id": agent_id,
            "step_id": step_id,
            "step": next_step,
            "message": "Step executed (logical run only)"
        }
