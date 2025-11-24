from typing import List, Dict, Any, Tuple

from .memory_core import MemoryCore
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory


class MemoryRouter:
    """
    MemoryRouter = 'Pumpe' des Gedächtnissystems.
    (Inhalt wie gehabt, nur Imports angepasst.)
    """

    def __init__(
        self,
        memory_core: MemoryCore,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
    ):
        self.memory_core = memory_core
        self.episodic = episodic
        self.semantic = semantic

    # ---------- Wichtigkeit ----------

    def _compute_importance_score(self, user_message: str, assistant_reply: str) -> int:
        """
        Erzeugt einen Score von 0–100 auf Basis mehrerer Heuristiken.
        (ohne harte User-Marker – die kommen extra in _classify_importance)
        """
        score = 0
        text = f"{user_message} {assistant_reply}".lower()

        # 1) Emotionale Stärke
        emotional_words = [
            "ich liebe",
            "ich hasse",
            "ich fürchte",
            "ich bin begeistert von",
            "ich hasse es",
            "ich liebe es",
        ]
        if any(w in text for w in emotional_words):
            score += 20

        # 2) Profilrelevanz (Identität, Hobby, Vorlieben, Regeln)
        profile_markers = [
            "ich heiße",
            "mein name ist",
            "ich wohne in",
            "ich lebe in",
            "mein hobby ist",
            "meine hobbies sind",
            "ich arbeite als",
            "mein beruf ist",
            "ich mag",
            "ich liebe",
            "ich trinke gerne",
            "ich esse gerne",
            "mein ziel ist",
            "mein aktuelles projekt ist",
            "mein projekt ist",
            "antworte mir immer",
        ]
        if any(m in text for m in profile_markers):
            score += 25

        # 3) Ziel-/Projekt-Relevanz (AI Core / autonomes KI-System)
        goal_project_markers = [
            "ai core",
            "autonomes ki-system",
            "autonomes ki system",
            "mein ziel ist es, ein autonomes ki-system zu bauen",
            "mein aktuelles projekt ist der ai core",
        ]
        if any(m in text for m in goal_project_markers):
            score += 25

        return max(0, min(100, score))

    def _classify_importance(self, user_message: str, assistant_reply: str) -> str:
        """
        Mappt auf low / medium / high.

        Wichtige Sonderregel:
        - Wenn der USER direkt sagt "merke dir", "wichtig", "dauerhaft merken", etc.
          -> IMMER high, egal wie die Modellantwort aussieht.
        """
        lower_user = user_message.lower()

        # Direkte Marker vom Nutzer -> immer high
        direct_markers = [
            "wichtig",
            "sehr wichtig",
            "bitte merken",
            "merke dir",
            "notiere",
            "dauerhaft merken",
            "vergiss das nie",
        ]
        if any(m in lower_user for m in direct_markers):
            return "high"

        # Sonst Score-Heuristik
        score = self._compute_importance_score(user_message, assistant_reply)

        if score >= 60:
            return "high"
        if score >= 30:
            return "medium"
        return "low"

    # ---------- Fakt-Erkennung (einzeln) ----------

    def _extract_single_fact(self, text: str) -> Tuple[str, str] | None:
        """
        Erkennt genau EINEN Fakt aus einem einfachen Satz.
        Wird von _extract_user_facts mehrfach aufgerufen.
        """
        text_clean = text.strip()
        if not text_clean:
            return None

        lower = text_clean.lower()

        # 1) Name
        if "ich heiße " in lower:
            idx = lower.find("ich heiße ")
            value = text_clean[idx + len("ich heiße "):].strip(" .!?,;")
            if value:
                return "name", value

        if "mein name ist " in lower:
            idx = lower.find("mein name ist ")
            value = text_clean[idx + len("mein name ist "):].strip(" .!?,;")
            if value:
                return "name", value

        # 2) Lieblingsfarbe
        if "meine lieblingsfarbe ist " in lower:
            idx = lower.find("meine lieblingsfarbe ist ")
            value = text_clean[idx + len("meine lieblingsfarbe ist "):].strip(" .!?,;")
            if value:
                return "favorite_color", value

        # 3) Wohnort / Umzug
        if "ich wohne in " in lower:
            idx = lower.find("ich wohne in ")
            value = text_clean[idx + len("ich wohne in "):].strip(" .!?,;")
            if value:
                return "location", value

        if "ich lebe in " in lower:
            idx = lower.find("ich lebe in ")
            value = text_clean[idx + len("ich lebe in "):].strip(" .!?,;")
            if value:
                return "location", value

        if "ich bin umgezogen nach " in lower:
            idx = lower.find("ich bin umgezogen nach ")
            value = text_clean[idx + len("ich bin umgezogen nach "):].strip(" .!?,;")
            if value:
                return "location", value

        if "ich bin nach " in lower and " umgezogen" in lower:
            start = lower.find("ich bin nach ")
            end = lower.find(" umgezogen")
            if end > start:
                value = text_clean[start + len("ich bin nach "):end].strip(" .!?,;")
                if value:
                    return "location", value

        # 4) Beruf
        if "ich arbeite als " in lower:
            idx = lower.find("ich arbeite als ")
            value = text_clean[idx + len("ich arbeite als "):].strip(" .!?,;")
            if value:
                return "job", value

        if "mein beruf ist " in lower:
            idx = lower.find("mein beruf ist ")
            value = text_clean[idx + len("mein beruf ist "):].strip(" .!?,;")
            if value:
                return "job", value

        # 5) Hobby
        if "mein hobby ist " in lower:
            idx = lower.find("mein hobby ist ")
            value = text_clean[idx + len("mein hobby ist "):].strip(" .!?,;")
            if value:
                return "hobby", value

        if "ich spiele gerne " in lower:
            idx = lower.find("ich spiele gerne ")
            value = text_clean[idx + len("ich spiele gerne "):].strip(" .!?,;")
            if value:
                return "hobby", value

        # 6) Vorlieben allgemein
        if "ich mag " in lower:
            idx = lower.find("ich mag ")
            value = text_clean[idx + len("ich mag "):].strip(" .!?,;")
            if value:
                return "like", value

        if "ich liebe " in lower:
            idx = lower.find("ich liebe ")
            value = text_clean[idx + len("ich liebe "):].strip(" .!?,;")
            if value:
                return "like", value

        # 7) Essen / Trinken
        if "ich trinke gerne " in lower:
            idx = lower.find("ich trinke gerne ")
            value = text_clean[idx + len("ich trinke gerne "):].strip(" .!?,;")
            if value:
                return "food_like", value

        if "ich esse gerne " in lower:
            idx = lower.find("ich esse gerne ")
            value = text_clean[idx + len("ich esse gerne "):].strip(" .!?,;")
            if value:
                return "food_like", value

        # 8) Haustier
        if "mein haustier ist ein " in lower:
            idx = lower.find("mein haustier ist ein ")
            value = text_clean[idx + len("mein haustier ist ein "):].strip(" .!?,;")
            if value:
                return "pet", value

        if "ich habe einen hund" in lower:
            return "pet", "Hund"

        if "ich habe eine katze" in lower:
            return "pet", "Katze"

        # 9) Ziel
        if "mein ziel ist " in lower:
            idx = lower.find("mein ziel ist ")
            value = text_clean[idx + len("mein ziel ist "):].strip(" .!?,;")
            if value:
                return "goal", value

        # 10) Projekt
        if "mein aktuelles projekt ist " in lower:
            idx = lower.find("mein aktuelles projekt ist ")
            value = text_clean[idx + len("mein aktuelles projekt ist "):].strip(" .!?,;")
            if value:
                return "project", value

        if "mein projekt ist " in lower:
            idx = lower.find("mein projekt ist ")
            value = text_clean[idx + len("mein projekt ist "):].strip(" .!?,;")
            if value:
                return "project", value

        # 11) Antwortstil
        if "antworte mir immer " in lower:
            idx = lower.find("antworte mir immer ")
            value = text_clean[idx + len("antworte mir immer "):].strip(" .!?,;")
            if value:
                return "rule_response_style", value

        return None

    # ---------- Mehrere Fakten aus einer Nachricht ----------

    def _extract_user_facts(self, user_message: str) -> List[Tuple[str, str]]:
        """
        Zerlegt die Nachricht in einfache Sätze und
        erkennt in jedem Satz einen möglichen Fakt.
        """
        facts: List[Tuple[str, str]] = []

        temp = (
            user_message.replace("!", ".")
            .replace("?", ".")
        )
        parts = [p.strip() for p in temp.split(".") if p.strip()]

        for part in parts:
            result = self._extract_single_fact(part)
            if result is not None and result not in facts:
                facts.append(result)

        return facts

    # ---------- Archivierung alter Fakten ----------

    def _archive_old_facts(self, user_id: str, fact_type: str) -> None:
        """Archiviert alle alten Fakten eines Typs."""
        all_items = self.semantic.get_recent_knowledge(user_id=user_id, limit=100)

        for item in all_items:
            tags = item.get("tags", [])
            if (
                "user_fact" in tags
                and f"fact:{fact_type}" in tags
                and "archived:true" not in tags
            ):
                new_tags = tags + ["archived:true"]
                content = f"[ARCHIVIERT] {item.get('content', '')}"
                self.semantic.add_knowledge(
                    user_id=user_id,
                    content=content,
                    source="archive",
                    tags=new_tags,
                )

    def _upsert_user_fact(self, user_id: str, fact_type: str, fact_value: str) -> None:
        """Archiviert alte Fakten und speichert den neuen Fakt."""
        self._archive_old_facts(user_id, fact_type)

        content = f"Nutzer-Info ({fact_type}): {fact_value}"
        self.semantic.add_knowledge(
            user_id=user_id,
            content=content,
            source="user_message",
            tags=["auto", "user_fact", "importance:high", f"fact:{fact_type}"],
        )

    # ---------- Eingangslogik ----------

    def on_user_message(self, user_id: str, message: str) -> None:
        """
        - Speichert die Nachricht im Kurzzeitgedächtnis.
        - Extrahiert ALLE erkennbaren Fakten.
        - Speichert jeden Fakt einzeln und archiviert ältere pro Typ.
        """
        self.memory_core.add_message(user_id, "user", message)

        facts = self._extract_user_facts(message)
        for fact_type, fact_value in facts:
            self._upsert_user_fact(user_id, fact_type, fact_value)

    # ---------- Modellantwort ----------

    def on_assistant_reply(self, user_id: str, reply: str, original_message: str) -> None:
        self.memory_core.add_message(user_id, "assistant", reply)

        importance = self._classify_importance(original_message, reply)
        importance_tag = f"importance:{importance}"

        self.episodic.add_event(
            user_id=user_id,
            event_type="model_response",
            data={
                "user_message": original_message,
                "assistant_reply": reply[:200] + ("..." if len(reply) > 200 else ""),
                "importance": importance,
            },
            tags=["conversation", "llm", importance_tag],
        )

        if importance == "high":
            self.semantic.add_knowledge(
                user_id=user_id,
                content=f"Wichtige Antwort des Assistenten zu: {original_message[:100]}",
                source="conversation",
                tags=["auto", importance_tag],
            )

    # ---------- Kontextaufbau ----------

    def build_llm_context(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        messages = self.memory_core.get_recent_messages(user_id, limit=limit)
        block = self._build_context_block(user_id=user_id, limit=50)
        if block is not None:
            messages = [block] + messages
        return messages

    def _build_context_block(self, user_id: str, limit: int) -> Dict[str, str] | None:
        """
        Baut einen kompakten System-Kontext aus den wichtigsten Fakten.
        - Nur nicht-archivierte Fakten.
        - Pro Faktentyp nur der neueste Eintrag.
        """
        all_items = self.semantic.get_recent_knowledge(user_id=user_id, limit=limit)

        latest_by_type: Dict[str, str] = {}
        generic: List[str] = []

        for item in all_items:
            tags = item.get("tags", [])
            if "archived:true" in tags:
                continue

            if not any(t.startswith("importance:high") for t in tags):
                continue

            content = item.get("content", "")
            if not content:
                continue

            fact_tags = [t for t in tags if t.startswith("fact:")]
            if fact_tags:
                fact_type = fact_tags[0].split(":", 1)[1]
                if fact_type not in latest_by_type:
                    latest_by_type[fact_type] = content
                continue

            generic.append(content)

        if not latest_by_type and not generic:
            return None

        lines: List[str] = ["Langzeit-Wissen über diesen Nutzer:", ""]

        for ftype in sorted(latest_by_type.keys()):
            lines.append(f"- {latest_by_type[ftype]}")

        for entry in generic[:3]:
            lines.append(f"- {entry}")

        return {
            "role": "system",
            "content": "\n".join(lines),
        }

    # ---------- Debug ----------

    def get_debug_snapshot(self, user_id: str) -> Dict[str, Any]:
        return {
            "recent_conversation": self.memory_core.get_recent_messages(user_id, limit=20),
            "recent_events": self.episodic.get_recent_events(user_id, limit=20),
            "recent_knowledge": self.semantic.get_recent_knowledge(user_id, limit=20),
        }
