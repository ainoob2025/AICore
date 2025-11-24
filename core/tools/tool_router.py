from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .model_switcher import ModelSwitcher


class ToolRouter:
    """
    Zentrale Schaltstelle für alle Tools.

    Phase 3-Erweiterungen:
    - Tool-Registry (core/tools/tool_catalog.json)
    - Tool-Statistiken (data/tools/stats.json)
    - LLM-gesteuerte Tool-Auswahl: select_tools(...)
    - Einheitliche Tool-Ausführung: run_tool(...)
    - route_tool_call(...) bleibt als Legacy-Wrapper erhalten.
    """

    def __init__(
        self,
        api_url: str,
        main_model_id: str,
        vision_model_id: Optional[str] = None,
        thinking_model_id: Optional[str] = None,
    ) -> None:
        self.api_url = api_url
        self.main_model_id = main_model_id
        self.vision_model_id = vision_model_id
        self.thinking_model_id = thinking_model_id

        self.model_switcher = ModelSwitcher(api_url=self.api_url)

        # interne Registry + Pfade
        base_dir = Path(__file__).resolve().parents[2]
        self._catalog_path = Path(__file__).resolve().parent / "tool_catalog.json"
        self._stats_path = base_dir / "data" / "tools" / "stats.json"
        self._stats_path.parent.mkdir(parents=True, exist_ok=True)

        self.tool_catalog: Dict[str, Dict[str, Any]] = self._load_tool_catalog()

    # ----------------------------------------------------------------------
    # Öffentliche API
    # ----------------------------------------------------------------------

    def route_tool_call(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy-Einstiegspunkt.
        Intern wird immer run_tool(...) verwendet.
        """
        return self.run_tool(tool_name=tool_name, args=payload)

    def run_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Einheitliche Tool-Ausführung.

        - Erwartet: bekannten Tool-Namen aus der Registry
        - Misst Latenz und aktualisiert data/tools/stats.json
        - Kapselt Exceptions in ein einheitliches Result-Schema
        """
        start = time.perf_counter()
        ok = False
        error_message: Optional[str] = None
        result: Dict[str, Any]

        try:
            if tool_name == "echo":
                result = self._handle_echo(args)
            elif tool_name == "uppercase":
                result = self._handle_uppercase(args)
            elif tool_name == "vision_analyze":
                result = self._handle_vision_analyze(args)
            elif tool_name == "thinking_reason":
                result = self._handle_thinking_reason(args)
            else:
                result = {
                    "ok": False,
                    "tool": tool_name,
                    "result": None,
                    "error": f"Unknown tool: {tool_name}",
                }

            ok = bool(result.get("ok", False))
            error_message = result.get("error")
        except Exception as e:
            error_message = str(e)
            result = {
                "ok": False,
                "tool": tool_name,
                "result": None,
                "error": error_message,
            }

        latency = max(time.perf_counter() - start, 0.0)
        self._update_stats(tool_name=tool_name, ok=ok, latency=latency, error_message=error_message)

        return result

    def select_tools(
        self,
        step_description: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        LLM-gesteuerte Tool-Auswahl mit Heuristik-Fallback.

        Rückgabe:
            Liste von Kandidaten, absteigend sortiert nach Relevanz:
            [
              {
                "name": str,
                "score": float,
                "reason": str,
                "meta": {...}   # Eintrag aus tool_catalog.json
              },
              ...
            ]
        """
        if not step_description:
            return []

        context = context or {}
        available_tools = list(self.tool_catalog.values())
        if not available_tools:
            return []

        # 1) Versuch: LLM-Ranking
        ranked = self._rank_tools_via_llm(step_description=step_description, context=context)

        # 2) Fallback: reine Heuristik
        if not ranked:
            ranked = self._rank_tools_heuristic(available_tools)

        if top_k is not None and top_k > 0:
            ranked = ranked[:top_k]

        return ranked

    # ----------------------------------------------------------------------
    # Tool-Registry + Stats
    # ----------------------------------------------------------------------

    def _load_tool_catalog(self) -> Dict[str, Dict[str, Any]]:
        """
        Lädt core/tools/tool_catalog.json in ein Dict[name] -> Eintrag.
        """
        catalog: Dict[str, Dict[str, Any]] = {}
        try:
            if self._catalog_path.is_file():
                with self._catalog_path.open("r", encoding="utf-8") as f:
                    raw = json.load(f)

                if isinstance(raw, list):
                    for entry in raw:
                        name = entry.get("name")
                        if isinstance(name, str):
                            catalog[name] = entry
                elif isinstance(raw, dict):
                    # optionales Format: {name: {...}}
                    for name, entry in raw.items():
                        if isinstance(entry, dict):
                            entry.setdefault("name", name)
                            catalog[name] = entry
        except Exception:
            # Bei Fehlern: leere Registry, Tools können trotzdem direkt via run_tool genutzt werden.
            pass

        return catalog

    def _load_stats(self) -> Dict[str, Dict[str, Any]]:
        try:
            if self._stats_path.is_file():
                with self._stats_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def _save_stats(self, stats: Dict[str, Dict[str, Any]]) -> None:
        try:
            with self._stats_path.open("w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception:
            # Stats sind diagnostisch, Fehler dürfen nie den Kernfluss brechen.
            pass

    def _update_stats(
        self,
        tool_name: str,
        ok: bool,
        latency: float,
        error_message: Optional[str],
    ) -> None:
        if not tool_name:
            return

        stats = self._load_stats()
        entry = stats.get(
            tool_name,
            {
                "success_count": 0,
                "failure_count": 0,
                "avg_latency": 0.0,
                "last_error": None,
            },
        )

        success_count = int(entry.get("success_count", 0))
        failure_count = int(entry.get("failure_count", 0))
        total_calls = success_count + failure_count
        new_total = total_calls + 1

        # neue Durchschnittslatenz
        try:
            prev_avg = float(entry.get("avg_latency", 0.0))
        except (TypeError, ValueError):
            prev_avg = 0.0

        new_avg = ((prev_avg * total_calls) + float(latency)) / float(new_total or 1.0)

        if ok:
            success_count += 1
            entry["last_error"] = None
        else:
            failure_count += 1
            if error_message:
                entry["last_error"] = error_message

        entry["success_count"] = success_count
        entry["failure_count"] = failure_count
        entry["avg_latency"] = new_avg

        stats[tool_name] = entry
        self._save_stats(stats)

    # ----------------------------------------------------------------------
    # LLM-Ranking + Fallback
    # ----------------------------------------------------------------------

    def _rank_tools_via_llm(
        self,
        step_description: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Nutzt das Main-Model, um Tools zu ranken.
        Falls irgendetwas schiefgeht (HTTP-Fehler, JSON-Parsing, etc.),
        wird [] zurückgegeben, damit der Heuristik-Fallback greift.
        """
        if not self.main_model_id:
            return []

        try:
            self.model_switcher.ensure_model(self.main_model_id)

            tools_for_prompt = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("input_schema", {}),
                    "output_schema": t.get("output_schema", {}),
                    "cost": t.get("cost", 1),
                    "latency": t.get("latency", 1),
                    "reliability_score": t.get("reliability_score", 0.5),
                    "tags": t.get("tags", []),
                }
                for t in self.tool_catalog.values()
            ]

            system_msg = {
                "role": "system",
                "content": (
                    "You are a tool selection router. "
                    "You receive a step description and must rank available tools. "
                    "Respond ONLY with strict JSON in the format:\n"
                    '{ "tools": [ {"name": "...", "score": 0.0, "reason": "..."}, ... ] }'
                ),
            }

            user_msg = {
                "role": "user",
                "content": json.dumps(
                    {
                        "step_description": step_description,
                        "context": context,
                        "available_tools": tools_for_prompt,
                    },
                    ensure_ascii=False,
                ),
            }

            payload = {
                "model": self.main_model_id,
                "messages": [system_msg, user_msg],
            }

            response = requests.post(self.api_url, json=payload, timeout=60)
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Content sollte JSON sein, evtl. ohne Code-Fences.
            content_stripped = content.strip()
            if content_stripped.startswith("```"):
                content_stripped = content_stripped.strip("`")
                parts = content_stripped.split("\n", 1)
                if len(parts) == 2:
                    content_stripped = parts[1]

            parsed = json.loads(content_stripped)
            tools_section = parsed.get("tools")
            if not isinstance(tools_section, list):
                return []

            ranked: List[Dict[str, Any]] = []
            for item in tools_section:
                name = item.get("name")
                if not isinstance(name, str):
                    continue
                base_meta = self.tool_catalog.get(name)
                if not base_meta:
                    continue
                score = float(item.get("score", 0.0))
                reason = str(item.get("reason", ""))

                ranked.append(
                    {
                        "name": name,
                        "score": score,
                        "reason": reason,
                        "meta": base_meta,
                    }
                )

            ranked.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            return ranked

        except Exception:
            return []

    def _rank_tools_heuristic(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Failsafe-Fallback:
        - Höchste reliability_score zuerst
        - Danach niedrigere cost
        - Danach niedrigere latency
        """
        ranked: List[Dict[str, Any]] = []

        for t in tools:
            name = t.get("name")
            if not isinstance(name, str):
                continue

            reliability = float(t.get("reliability_score", 0.5))
            cost = float(t.get("cost", 1.0))
            latency = float(t.get("latency", 1.0))

            score = reliability - 0.01 * cost - 0.01 * latency

            ranked.append(
                {
                    "name": name,
                    "score": score,
                    "reason": "heuristic_fallback",
                    "meta": t,
                }
            )

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked

    # ----------------------------------------------------------------------
    # Konkrete Tools
    # ----------------------------------------------------------------------

    def _handle_echo(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Einfaches Echo-Tool. Gibt den Payload zurück."""
        return {
            "ok": True,
            "tool": "echo",
            "result": payload,
            "error": None,
        }

    def _handle_uppercase(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Nimmt einen Text unter payload['text'] und macht ihn GROSS."""
        text = str(payload.get("text", ""))
        return {
            "ok": True,
            "tool": "uppercase",
            "result": text.upper(),
            "error": None,
        }

    def _handle_vision_analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Vision-Analyse-Tool.

        Erwartet im payload:
          - "messages": Liste von Chat-Nachrichten im LM-Studio-Format,
                        inkl. Bildinhalt (wie du es an LM Studio schickst).
        """
        if not self.vision_model_id:
            return {
                "ok": False,
                "tool": "vision_analyze",
                "result": None,
                "error": "Vision model is not configured.",
            }

        messages = payload.get("messages")
        if not messages:
            return {
                "ok": False,
                "tool": "vision_analyze",
                "result": None,
                "error": "Missing 'messages' in payload for vision_analyze.",
            }

        self.model_switcher.ensure_model(self.vision_model_id)

        lm_payload = {
            "model": self.vision_model_id,
            "messages": messages,
        }

        try:
            response = requests.post(self.api_url, json=lm_payload, timeout=120)
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            return {
                "ok": True,
                "tool": "vision_analyze",
                "result": content,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "tool": "vision_analyze",
                "result": None,
                "error": f"Vision call failed: {e}",
            }

    def _handle_thinking_reason(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thinking-Tool für komplexes Reasoning.

        Erwartet im payload:
          - "messages": Liste von Chat-Nachrichten im LM-Studio-Format
        """
        if not self.thinking_model_id:
            return {
                "ok": False,
                "tool": "thinking_reason",
                "result": None,
                "error": "Thinking model is not configured.",
            }

        messages = payload.get("messages")
        if not messages:
            return {
                "ok": False,
                "tool": "thinking_reason",
                "result": None,
                "error": "Missing 'messages' in payload for thinking_reason.",
            }

        self.model_switcher.ensure_model(self.thinking_model_id)

        lm_payload = {
            "model": self.thinking_model_id,
            "messages": messages,
        }

        try:
            response = requests.post(self.api_url, json=lm_payload, timeout=300)
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            return {
                "ok": True,
                "tool": "thinking_reason",
                "result": content,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "tool": "thinking_reason",
                "result": None,
                "error": f"Thinking call failed: {e}",
            }
