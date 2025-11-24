from typing import Dict, Any

from core.planner.planner import Planner
from core.agents.agent_factory import AgentFactory


class PlannerAgentLink:
    """
    Verknüpft Planner und AgentFactory.

    Aufgabe:
    - Für einen Task einen Plan erzeugen.
    - Passenden Sub-Agenten nach Template anlegen.
    - Beide Infos gemeinsam zurückgeben.
    """

    def __init__(self):
        # Lokale Instanzen für einfache Nutzung.
        # Der MasterAgent kann später eigene Instanzen übergeben,
        # wenn du das zentralisieren willst.
        self.planner = Planner()
        self.agent_factory = AgentFactory()

    def create_plan_and_agent(
        self,
        user_id: str,
        task: str,
        template_name: str,
    ) -> Dict[str, Any]:
        """
        Erzeugt:
        - Plan (Planner)
        - Agent (AgentFactory)

        Rückgabe:
        {
          "task": "...",
          "template": "...",
          "plan": {...},
          "agent": {...}
        }
        """

        plan = self.planner.create_plan(task)
        agent = self.agent_factory.create_agent(
            user_id=user_id,
            template_name=template_name,
            task=task,
        )

        return {
            "task": task,
            "template": template_name,
            "plan": plan,
            "agent": agent,
        }
