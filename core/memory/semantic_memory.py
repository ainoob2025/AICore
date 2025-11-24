from typing import List, Dict, Any
from datetime import datetime
import os
import json


class SemanticMemory:
    """
    Persistentes Langzeitgedächtnis (Version 1).

    Architektur:
    - In-Memory Cache (wie bisher)
    - Automatische JSON-Speicherung pro User:
        ./data/semantic/<user_id>.json
    - Voll modular: Kann später leicht gegen SQLite, MongoDB,
      ChromaDB oder Weaviate ausgetauscht werden.
    """

    def __init__(self):
        self._knowledge: Dict[str, List[Dict[str, Any]]] = {}

        # Speicherpfad für JSON-Dateien
        self.base_path = "./data/semantic"
        os.makedirs(self.base_path, exist_ok=True)

        # Beim Start alle vorhandenen JSON-Dateien laden
        self._load_all_users()

    # ---------- Laden & Speichern ----------

    def _get_user_file(self, user_id: str) -> str:
        """Pfad zur JSON-Datei des Users.""" 
        safe_id = str(user_id).replace("/", "_")
        return os.path.join(self.base_path, f"{safe_id}.json")

    def _load_user(self, user_id: str) -> None:
        """Lädt Wissen eines Users aus der JSON-Datei (falls vorhanden)."""
        file_path = self._get_user_file(user_id)

        if not os.path.exists(file_path):
            self._knowledge[user_id] = []
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._knowledge[user_id] = data
                else:
                    self._knowledge[user_id] = []
        except Exception:
            # Falls Datei korrupt ist → nicht crashen
            self._knowledge[user_id] = []

    def _load_all_users(self) -> None:
        """Lädt alle vorhandenen JSON-Dateien beim Start."""
        if not os.path.exists(self.base_path):
            return

        for filename in os.listdir(self.base_path):
            if filename.endswith(".json"):
                user_id = filename[:-5]  # ".json" entfernen
                self._load_user(user_id)

    def _save_user(self, user_id: str) -> None:
        """Speichert Wissen eines Users in dessen JSON-Datei."""
        file_path = self._get_user_file(user_id)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._knowledge.get(user_id, []), f, ensure_ascii=False, indent=2)
        except Exception:
            # Wir schlucken Fehler, damit MemoryRouter nicht crasht
            pass

    # ---------- Hauptfunktionen ----------

    def add_knowledge(
        self,
        user_id: str,
        content: str,
        source: str = "manual",
        tags: List[str] | None = None,
    ) -> None:
        """Fügt einen Wissenseintrag hinzu UND speichert sofort persistent."""
        if user_id not in self._knowledge:
            self._knowledge[user_id] = []

        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "content": content,
            "source": source,
            "tags": tags or [],
        }

        self._knowledge[user_id].append(entry)

        # → Sofortige Persistenz
        self._save_user(user_id)

    def get_all_knowledge(self, user_id: str) -> List[Dict[str, Any]]:
        """Gibt alle Wissenseinträge zurück."""
        if user_id not in self._knowledge:
            self._load_user(user_id)
        return self._knowledge.get(user_id, [])

    def get_recent_knowledge(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Gibt die letzten 'limit' Wissenseinträge zurück."""
        if user_id not in self._knowledge:
            self._load_user(user_id)
        return self._knowledge.get(user_id, [])[-limit:]
