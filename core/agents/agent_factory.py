import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from core.agents.agent_state import AgentStateManager


class AgentFactory:
    """
    AgentFactory (Phase 2 – erste Version)

    Aufgaben:
    - Lädt Agent-Templates aus core/agents/templates/
    - Erstellt dynamisch neue Agenten mit:
        * Rolle
        * Tools
        * Memory-Scope
        * Workspace
        * Bewertungslogik
    - Speichert Agenten über AgentStateManager
    """

    def __init__(self):
        self.template_path = Path("core/agents/templates")
        self.agent_state = AgentStateManager()

    # ----------------------------------------------------------------------
    # INTERNAL: Template laden
    # ----------------------------------------------------------------------

    def _load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        file_path = self.template_path / f"{template_name}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            return None

    # ----------------------------------------------------------------------
    # Agent erstellen
    # ----------------------------------------------------------------------

    def create_agent(self, user_id: str, template_name: str, task: str) -> Optional[Dict[str, Any]]:
        """
        Erzeugt einen neuen Agenten basierend auf einem Template.
        """

        template = self._load_template(template_name)
        if not template:
            return None

        # Schritt 1: Basis-Agent via AgentStateManager anlegen
        agent = self.agent_state.create_agent(user_id=user_id, task=task)

        # Schritt 2: Template-Metadaten hinzufügen
        meta_update = {
            "role": template.get("role"),
            "description": template.get("description"),
            "allowed_tools": template.get("allowed_tools", []),
            "memory_scope": template.get("memory_scope", []),
            "work_area": template.get("work_area"),
            "evaluation": template.get("evaluation", {}),
        }

        updated_agent = self.agent_state.update_agent(
            agent_id=agent["agent_id"],
            meta_update=meta_update
        )

        return updated_agent

    # ----------------------------------------------------------------------
    # Agent-Info abrufen
    # ----------------------------------------------------------------------

    def load_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Lädt ein Template ohne Erstellung eines Agenten."""
        return self._load_template(template_name)

    def list_available_templates(self) -> Dict[str, str]:
        """Listet alle vorhandenen Agent-Templates auf."""
        templates = {}

        for file in self.template_path.glob("*.json"):
            name = file.stem
            templates[name] = str(file)

        return templates
