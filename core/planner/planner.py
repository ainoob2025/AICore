import uuid
from typing import List, Dict, Any


class Planner:
    """
    Einfache erste Version eines Task-Planners.

    Version 1 (Phase 2 Start):
    - Nimmt eine Aufgabe (Text) entgegen.
    - Zerlegt sie in 1–3 grobe Schritte.
    - Gibt einen strukturierten Plan zurück.
    - Keine Tool- oder Agentenlogik – das kommt in Phase 2.2 / 2.3.
    """

    def __init__(self):
        pass

    def create_plan(self, task: str) -> Dict[str, Any]:
        """
        Erstellt einen groben Plan für eine gegebene Aufgabe.

        Rückgabeformat:
        {
            "plan_id": "...",
            "task": "...",
            "steps": [
                {"id": "...", "description": "...", "status": "pending"},
                ...
            ]
        }
        """

        plan_id = str(uuid.uuid4())

        # Schritt-Erzeugung (sehr simpel)
        steps = self._generate_steps(task)

        return {
            "plan_id": plan_id,
            "task": task,
            "steps": steps,
        }

    def _generate_steps(self, task: str) -> List[Dict[str, Any]]:
        """
        Erste einfache Heuristik:
        - Schritt 1: Verständnis / Analyse
        - Schritt 2: Grobe Bearbeitung
        - Schritt 3: Ergebnis prüfen
        """

        s1 = {
            "id": str(uuid.uuid4()),
            "description": f"Analyse der Aufgabe: {task}",
            "status": "pending",
        }
        s2 = {
            "id": str(uuid.uuid4()),
            "description": f"Bearbeite den Kern der Aufgabe: {task}",
            "status": "pending",
        }
        s3 = {
            "id": str(uuid.uuid4()),
            "description": f"Prüfe die Ergebnisse für: {task}",
            "status": "pending",
        }

        return [s1, s2, s3]
