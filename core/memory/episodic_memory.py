from datetime import datetime
from typing import List, Dict, Any
import os
import json


class EpisodicMemory:
    """
    Persistentes Episoden-Gedächtnis (Events).

    Architektur:
    - In-Memory Cache wie bisher
    - Zusätzliche JSON-Speicherung pro User unter:
        ./data/episodic/<user_id>.json

    Events-Struktur:
      {
        "timestamp": ...,
        "type": ...,
        "data": {...},
        "tags": [...]
      }
    """

    def __init__(self):
        self._events: Dict[str, List[Dict[str, Any]]] = {}

        # Basisordner für Episoden-Daten
        self.base_path = "./data/episodic"
        os.makedirs(self.base_path, exist_ok=True)

        # Beim Start alle vorhandenen Dateien laden
        self._load_all_users()

    # ---------- Datei-Helfer ----------

    def _get_user_file(self, user_id: str) -> str:
        """Pfad zur JSON-Datei des Users."""
        safe_id = str(user_id).replace("/", "_")
        return os.path.join(self.base_path, f"{safe_id}.json")

    def _load_user(self, user_id: str) -> None:
        """Lädt Episoden eines Users aus dessen JSON-Datei (falls vorhanden)."""
        file_path = self._get_user_file(user_id)

        if not os.path.exists(file_path):
            self._events[user_id] = []
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._events[user_id] = data
                else:
                    self._events[user_id] = []
        except Exception:
            # Bei Fehler: nicht crashen, einfach leere Liste
            self._events[user_id] = []

    def _load_all_users(self) -> None:
        """Lädt alle vorhandenen User-Dateien beim Start."""
        if not os.path.exists(self.base_path):
            return

        for filename in os.listdir(self.base_path):
            if filename.endswith(".json"):
                user_id = filename[:-5]  # ".json" abschneiden
                self._load_user(user_id)

    def _save_user(self, user_id: str) -> None:
        """Speichert alle Episoden eines Users in dessen JSON-Datei."""
        file_path = self._get_user_file(user_id)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._events.get(user_id, []), f, ensure_ascii=False, indent=2)
        except Exception:
            # Fehler beim Speichern nicht bis nach oben durchreichen
            pass

    # ---------- Hauptfunktionen ----------

    def add_event(
        self,
        user_id: str,
        event_type: str,
        data: Dict[str, Any],
        tags: List[str] | None = None,
    ) -> None:
        """
        Neues Ereignis im Episodengedächtnis speichern UND persistent ablegen.

        event_type z.B.:
          - "tool_call"
          - "tool_result"
          - "error"
          - "decision"
          - "insight"
          - "model_response"
        """
        if user_id not in self._events:
            self._events[user_id] = []

        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            "data": data,
            "tags": tags or [],
        }

        self._events[user_id].append(event)

        # Sofort speichern
        self._save_user(user_id)

    def get_recent_events(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Gibt die letzten 'limit' Ereignisse für einen User zurück.
        """
        if user_id not in self._events:
            self._load_user(user_id)

        return self._events.get(user_id, [])[-limit:]
