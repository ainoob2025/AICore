import os
import json
from typing import Dict, List, Any


class MemoryCore:
    """
    Persistentes Conversation Memory.

    Architektur:
    - In-Memory Cache (wie bisher)
    - Automatische JSON-Speicherung pro User:
        ./data/conversation/<user_id>.json
    - Modular und problemlos austauschbar durch:
        SQLite, MongoDB, Chroma oder Weaviate.
    """

    def __init__(self):
        # In-Memory: { user_id: [ {role, content}, ... ] }
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}

        # Root-Directory für Conversation Memory
        self.base_path = "./data/conversation"
        os.makedirs(self.base_path, exist_ok=True)

        # Bestehende User-Daten laden
        self._load_all_users()

    # ---------- Datei-Helfer ----------

    def _get_user_file(self, user_id: str) -> str:
        """Pfad zur JSON-Datei eines Nutzers."""
        safe_id = str(user_id).replace("/", "_")
        return os.path.join(self.base_path, f"{safe_id}.json")

    def _load_user(self, user_id: str) -> None:
        """Konversation eines Nutzers aus Datei laden."""
        file_path = self._get_user_file(user_id)

        if not os.path.exists(file_path):
            self._conversations[user_id] = []
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._conversations[user_id] = data
                else:
                    self._conversations[user_id] = []
        except Exception:
            # Datei beschädigt → nicht crashen
            self._conversations[user_id] = []

    def _load_all_users(self) -> None:
        """Lädt alle vorhandenen User-Konversationen."""
        if not os.path.exists(self.base_path):
            return

        for filename in os.listdir(self.base_path):
            if filename.endswith(".json"):
                user_id = filename[:-5]
                self._load_user(user_id)

    def _save_user(self, user_id: str) -> None:
        """Speichert die Konversation als JSON."""
        file_path = self._get_user_file(user_id)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._conversations.get(user_id, []), f, ensure_ascii=False, indent=2)
        except Exception:
            # Fehler werden geschluckt, MemoryRouter darf nie crashen
            pass

    # ---------- Hauptfunktionen ----------

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """
        Fügt eine Nachricht zum Verlauf eines Users hinzu
        UND speichert sofort persistent.
        """
        if user_id not in self._conversations:
            self._conversations[user_id] = []

        self._conversations[user_id].append(
            {
                "role": role,
                "content": content
            }
        )

        # Persistenz
        self._save_user(user_id)

    def get_recent_messages(self, user_id: str, limit: int = 10) -> list:
        """Gibt die letzten 'limit' Nachrichten eines Nutzers zurück."""
        if user_id not in self._conversations:
            self._load_user(user_id)

        return self._conversations.get(user_id, [])[-limit:]
