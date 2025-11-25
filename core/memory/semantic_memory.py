from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import json


class SemanticMemory:
    """
    Persistentes Langzeitgedaechtnis (Version 2).

    Funktionen in dieser Version:
    - Persistente JSON-Dateien pro User
    - Jeder Eintrag hat:
        - id
        - content
        - source
        - tags
        - metadata (flexibel erweiterbar)
    - Kompatibel mit Cross-Memory-Search und Wissensgraph
    """

    def __init__(self, base_path: str = "./data/semantic"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

        # In-Memory Cache: { user_id: [knowledge_items] }
        self._knowledge: Dict[str, List[Dict[str, Any]]] = {}

        # Alle vorhandenen User laden
        self._load_all_users()

    # ---------------------------------------------------------
    # Laden + Speichern
    # ---------------------------------------------------------

    def _get_user_file(self, user_id: str) -> str:
        """Pfad zur JSON-Datei."""
        safe_id = str(user_id).replace("/", "_")
        return os.path.join(self.base_path, f"{safe_id}.json")

    def _load_user(self, user_id: str) -> None:
        path = self._get_user_file(user_id)

        if not os.path.exists(path):
            self._knowledge[user_id] = []
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._knowledge[user_id] = data
            else:
                self._knowledge[user_id] = []
        except Exception:
            self._knowledge[user_id] = []

    def _load_all_users(self) -> None:
        if not os.path.exists(self.base_path):
            return

        for filename in os.listdir(self.base_path):
            if filename.endswith(".json"):
                user_id = filename[:-5]
                self._load_user(user_id)

    def _save_user(self, user_id: str) -> None:
        path = self._get_user_file(user_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._knowledge.get(user_id, []), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------------------------------------------------------
    # Oeffentliche API
    # ---------------------------------------------------------

    def add_knowledge(
        self,
        user_id: str,
        content: str,
        source: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Fuegt ein Wissenselement hinzu und speichert es persistent.
        Voll kompatibel mit CrossMemory und dem Wissensgraphen.
        """
        if metadata is None:
            metadata = {}
        if tags is None:
            tags = []

        # sicherstellen, dass User geladen ist
        if user_id not in self._knowledge:
            self._load_user(user_id)

        item = {
            "id": f"km-{len(self._knowledge.get(user_id, [])) + 1}",
            "content": content,
            "source": source,
            "tags": tags,
            "metadata": {
                **metadata,
                "created_at": datetime.utcnow().isoformat() + "Z",
            },
        }

        self._knowledge.setdefault(user_id, []).append(item)
        self._save_user(user_id)

        return item

    def get_knowledge(
        self,
        user_id: str,
        limit: int = 20,
        tag_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Liefert Wissen fuer einen User, optional nach Tags gefiltert.
        Neueste zuerst.
        """
        if user_id not in self._knowledge:
            self._load_user(user_id)

        items = list(self._knowledge.get(user_id, []))

        if tag_filter:
            tag_set = set(tag_filter)
            items = [
                item for item in items
                if tag_set.intersection(set(item.get("tags", [])))
            ]

        # sortieren: neueste zuerst
        items.sort(
            key=lambda x: x.get("metadata", {}).get("created_at", ""),
            reverse=True,
        )

        return items[:limit]

    def get_recent_knowledge(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Alias zu get_knowledge für Rueckwaertskompatibilitaet."""
        return self.get_knowledge(user_id=user_id, limit=limit)
