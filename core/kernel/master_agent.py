import requests
from typing import List, Dict, Any

from core.memory.memory_os import MemoryOS
from core.rag.rag_engine import RAGEngine
from core.graph.graph_engine import GraphEngine
from core.planner.planner import Planner
from core.tools.tool_router import ToolRouter

# Aus providers.yaml / models.yaml
LM_STUDIO_BASE_URL = "http://localhost:10030"  # :contentReference[oaicite:3]{index=3}
LM_STUDIO_CHAT_ENDPOINT = "/v1/chat/completions"
MAIN_MODEL_ID = "josiefied-qwen3-4b-instruct-2507-abliterated-v1-i1@q5_k_m"  # :contentReference[oaicite:4]{index=4}


class MasterAgent:
    def __init__(self) -> None:
        self.memory = MemoryOS()
        self.rag = RAGEngine()
        self.graph = GraphEngine()
        self.planner = Planner()
        self.tools = ToolRouter()

    def _build_messages(self, user_message: str) -> List[Dict[str, str]]:
        """Baue den Chat-Verlauf für das Modell (intern Englisch, nach außen Deutsch)."""
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are Josie, a local assistant running inside AI Core. "
                    "You think and plan in English, but you answer the user in German "
                    "by default unless explicitly asked otherwise."
                ),
            }
        ]

        # Conversation History aus MemoryOS (falls vorhanden)
        history = self.memory.get_conversation()
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("message", "")
            if not content:
                continue
            messages.append({"role": role, "content": content})

        # Aktuelle User-Nachricht anhängen
        messages.append({"role": "user", "content": user_message})
        return messages

    def _call_main_model(self, messages: List[Dict[str, str]]) -> str:
        """Sprich das Hauptmodell in LM Studio an."""
        url = LM_STUDIO_BASE_URL + LM_STUDIO_CHAT_ENDPOINT
        payload: Dict[str, Any] = {
            "model": MAIN_MODEL_ID,
            "messages": messages,
            "temperature": 0.3,
        }

        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            # Fallback-Text, falls LM Studio nicht erreichbar ist
            return f"Fehler beim Aufruf des lokalen Modells: {e}"

    def handle_chat(self, message: str) -> Dict[str, Any]:
        """Haupteinstieg: wird vom Gateway /chat aufgerufen."""
        # 1. Planner (noch simpel): wir holen nur einen Plan-Text
        plan = self.planner.decompose(f"User request: {message}")
        plan_text = ""
        plan_tools = []

        if isinstance(plan, dict):
            plan_text = plan.get("summary", "") or str(plan)
            plan_tools = plan.get("tools", []) or []
        else:
            plan_text = str(plan)

        # 2. Tools ausführen (nur wenn der Planner welche nennt)
        tools_used = []
        if plan_tools:
            tools_used = self.tools.execute(plan_tools)

        # 3. Prompt fürs Modell bauen (Plan + Userfrage)
        messages = self._build_messages(
            f"{message}\n\n(Plan: {plan_text})"
        )

        # 4. LLM aufrufen
        answer = self._call_main_model(messages)

        # 5. Memory aktualisieren
        self.memory.add_turn("user", message)
        self.memory.add_turn("assistant", answer)

        # 6. Graph updaten (Stub genügt im Moment, Masterplan erlaubt Iteration) :contentReference[oaicite:5]{index=5}
        self.graph.add_conversation(message, answer, tools_used)

        return {
            "response": answer,
            "tools_used": tools_used,
            "plan": plan_text,
        }
