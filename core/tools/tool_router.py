from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
import subprocess

from .model_switcher import ModelSwitcher
from core.rag.rag_service import RagService


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
        self.rag_service = RagService()

        # interne Registry + Pfade
        base_dir = Path(__file__).resolve().parents[2]
        self._catalog_path = Path(__file__).resolve().parent / "tool_catalog.json"
        self._stats_path = base_dir / "data" / "tools" / "stats.json"
        self._stats_path.parent.mkdir(parents=True, exist_ok=True)

        # Phase 7 – Pfade / Sicherheitsgrenzen
        # Sandbox für Terminal
        self._terminal_sandbox_dir = base_dir / "data" / "terminal_sandbox"
        self._terminal_sandbox_dir.mkdir(parents=True, exist_ok=True)

        # Root für File-Tools
        self._file_root = base_dir / "data" / "files"
        self._file_root.mkdir(parents=True, exist_ok=True)

        # Audio-Verzeichnisse (Text-basiertes Stub-Handling)
        self._audio_input_root = base_dir / "data" / "audio"
        self._audio_output_root = base_dir / "data" / "audio_out"

        # Browser-Defaults
        self._browser_timeout = 10.0
        self._browser_max_bytes = 200_000

        self.tool_catalog: Dict[str, Dict[str, Any]] = self._load_tool_catalog()

        # Strategien laden (Phase 6)
        self.strategies_path = Path("config/strategies.json")
        self.strategies = self._load_strategies()

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
            elif tool_name == "rag_query":
                result = self._handle_rag_query(args)
            elif tool_name == "browser_get":
                result = self._handle_browser_get(args)
            elif tool_name == "browser_extract":
                result = self._handle_browser_extract(args)
            elif tool_name == "browser_click":
                result = self._handle_browser_click(args)
            elif tool_name == "shell_run":
                result = self._handle_shell_run(args)
            elif tool_name == "file_read":
                result = self._handle_file_read(args)
            elif tool_name == "file_write":
                result = self._handle_file_write(args)
            elif tool_name == "file_list":
                result = self._handle_file_list(args)
            elif tool_name == "file_summary":
                result = self._handle_file_summary(args)
            elif tool_name == "speech_to_text":
                result = self._handle_speech_to_text(args)
            elif tool_name == "text_to_speech":
                result = self._handle_text_to_speech(args)
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

        # Strategiebasierte Bonus-Priorisierung (Phase 6)
        try:
            tool_priorities = getattr(self, "strategies", {}).get("tool_priorities", {})
            if isinstance(tool_priorities, dict):
                for item in ranked:
                    name = item.get("name")
                    if isinstance(name, str) and name in tool_priorities:
                        # sichere Konvertierung zu float
                        try:
                            bonus = float(tool_priorities[name])
                        except Exception:
                            bonus = 0.0
                        item["score"] = float(item.get("score", 0.0)) + bonus
        except Exception:
            pass

        # Danach erneut sortieren
        ranked.sort(key=lambda x: x.get("score", 0.0), reverse=True)

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

    def _load_strategies(self):
        try:
            if self.strategies_path.exists():
                with self.strategies_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}

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

    def _handle_rag_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handler für das rag_query-Tool.
        Erwartet im payload:
          - "user_id": str
          - "query": str
          - optional "top_k": int
          - optional "filters": Dict[str, Any]
        Ruft RagService.query(...) auf und gibt eine strukturierte Antwort zurück.
        """
        user_id = payload.get("user_id")
        query = payload.get("query")
        top_k = payload.get("top_k", 5)
        filters = payload.get("filters") or {}

        if not isinstance(user_id, str) or not isinstance(query, str):
            return {
                "ok": False,
                "tool": "rag_query",
                "result": None,
                "error": "Payload muss 'user_id' (str) und 'query' (str) enthalten.",
            }

        try:
            results = self.rag_service.query(
                user_id=user_id,
                query_text=query,
                top_k=int(top_k) if top_k is not None else 5,
                filters=filters,
            )
            return {
                "ok": True,
                "tool": "rag_query",
                "results": results,
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": "rag_query",
                "results": [],
                "error": f"rag_query failed: {e}",
            }

    # ----------------------------------------------------------------------
    # Phase 7: Neue Tools (Browser, Shell, File, Audio) - private Handler
    # ----------------------------------------------------------------------

    def _handle_browser_get(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Einfaches Browser-GET (Phase 7).
        - Unterstützt nur http/https.
        - Nutzt requests.get mit Timeout.
        - Schneidet den Body nach self._browser_max_bytes ab.
        Erwartet:
          - url: str
          - optional headers: Dict[str, str]
        """
        url = str(payload.get("url", "")).strip()
        headers = payload.get("headers") or {}

        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return {
                "ok": False,
                "tool": "browser_get",
                "result": None,
                "error": "Invalid or missing 'url' (only http/https allowed).",
            }

        if not isinstance(headers, dict):
            headers = {}

        try:
            resp = requests.get(url, headers=headers, timeout=self._browser_timeout)
            text = resp.text[: int(self._browser_max_bytes)]
            result = {
                "url": url,
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "text": text,
            }
            return {
                "ok": True,
                "tool": "browser_get",
                "result": result,
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": "browser_get",
                "result": None,
                "error": f"browser_get failed: {e}",
            }

    def _handle_browser_extract(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sehr einfache Extraktion aus HTML/Text (Phase 7).
        Heuristik:
          - Wenn 'text' im Payload vorhanden ist, wird dieser genutzt.
          - Sonst wird browser_get(url) aufgerufen.
          - 'query' wird als einfacher Substring behandelt und ein Ausschnitt geliefert.
        Erwartet:
          - optional url: str
          - optional text: str
          - optional query: str
        """
        raw_text = payload.get("text")
        url = payload.get("url")
        query = payload.get("query")

        if raw_text is None and url:
            # Fallback: Text via browser_get laden
            get_result = self._handle_browser_get({"url": url})
            if not get_result.get("ok"):
                return {
                    "ok": False,
                    "tool": "browser_extract",
                    "result": None,
                    "error": "browser_get failed in browser_extract.",
                }
            raw_text = (get_result.get("result") or {}).get("text")

        text = str(raw_text or "")
        if not text:
            return {
                "ok": False,
                "tool": "browser_extract",
                "result": None,
                "error": "No text available for extraction.",
            }

        if query:
            query = str(query)
            idx = text.lower().find(query.lower())
            if idx != -1:
                start = max(idx - 200, 0)
                end = min(idx + 200, len(text))
                snippet = text[start:end]
            else:
                snippet = text[:400]
        else:
            snippet = text[:400]

        result = {
            "url": url,
            "query": query,
            "snippet": snippet,
        }

        return {
            "ok": True,
            "tool": "browser_extract",
            "result": result,
            "error": None,
        }

    def _handle_browser_click(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Vereinfachtes browser_click (Phase 7, Minimalversion).
        Aktuell: Alias für browser_get(url), Click-Logik ist TODO.
        Erwartet:
          - url: str
        """
        url = payload.get("url")
        if not url:
            return {
                "ok": False,
                "tool": "browser_click",
                "result": None,
                "error": "Missing 'url' for browser_click.",
            }

        base = self._handle_browser_get({"url": url})
        if not base.get("ok"):
            return {
                "ok": False,
                "tool": "browser_click",
                "result": None,
                "error": "browser_get failed in browser_click.",
            }

        result = base.get("result") or {}
        result["click_simulated"] = True

        return {
            "ok": True,
            "tool": "browser_click",
            "result": result,
            "error": None,
        }

    def _handle_shell_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sandboxed Terminal-Tool (Phase 7).
        - Whitelist-basierte Kommandos
        - Ausführung im Sandbox-Verzeichnis data/terminal_sandbox
        Erwartet:
          - command: str (z.B. "echo hello")
        """
        command = str(payload.get("command", "")).strip()
        if not command:
            return {
                "ok": False,
                "tool": "shell_run",
                "result": None,
                "error": "Missing 'command' for shell_run.",
            }

        # Whitelist einfacher Kommandos (nur Name, keine beliebigen Shell-Chains)
        allowed = {"echo", "ls", "dir", "pwd"}
        cmd_name = command.split()[0]

        if cmd_name not in allowed:
            return {
                "ok": False,
                "tool": "shell_run",
                "result": None,
                "error": f"Command '{cmd_name}' is not allowed.",
            }

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self._terminal_sandbox_dir,
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            result = {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
            return {
                "ok": True,
                "tool": "shell_run",
                "result": result,
                "error": None,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "tool": "shell_run",
                "result": None,
                "error": "Command timed out.",
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": "shell_run",
                "result": None,
                "error": f"shell_run failed: {e}",
            }

    def _resolve_file_path(self, relative_path: str) -> Optional[Path]:
        """
        Hilfsfunktion für File-Tools. Erzwingt, dass alle Zugriffe unterhalb von self._file_root liegen.
        """
        rel = Path(relative_path)
        full = (self._file_root / rel).resolve()

        try:
            # Python 3.9+: Path.is_relative_to
            if hasattr(full, "is_relative_to"):
                if not full.is_relative_to(self._file_root):
                    return None
            else:
                # Fallback für ältere Versionen
                if str(self._file_root.resolve()) not in str(full):
                    return None
        except Exception:
            return None

        return full

    def _handle_file_read(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Liest eine Textdatei relativ zu data/files.
        Erwartet:
          - path: relative Pfadangabe unterhalb von data/files
        """
        path = payload.get("path")
        if not path:
            return {
                "ok": False,
                "tool": "file_read",
                "result": None,
                "error": "Missing 'path' for file_read.",
            }

        target = self._resolve_file_path(str(path))
        if not target:
            return {
                "ok": False,
                "tool": "file_read",
                "result": None,
                "error": "Access outside file root is not allowed.",
            }

        if not target.is_file():
            return {
                "ok": False,
                "tool": "file_read",
                "result": None,
                "error": "File does not exist.",
            }

        try:
            text = target.read_text(encoding="utf-8")
            return {
                "ok": True,
                "tool": "file_read",
                "result": {"path": str(target), "content": text},
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": "file_read",
                "result": None,
                "error": f"file_read failed: {e}",
            }

    def _handle_file_write(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Schreibt eine Textdatei unterhalb von data/files.
        Erwartet:
          - path: relative Pfadangabe
          - content: str
        """
        path = payload.get("path")
        content = payload.get("content")

        if not path:
            return {
                "ok": False,
                "tool": "file_write",
                "result": None,
                "error": "Missing 'path' for file_write.",
            }

        if content is None:
            return {
                "ok": False,
                "tool": "file_write",
                "result": None,
                "error": "Missing 'content' for file_write.",
            }

        target = self._resolve_file_path(str(path))
        if not target:
            return {
                "ok": False,
                "tool": "file_write",
                "result": None,
                "error": "Access outside file root is not allowed.",
            }

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(content), encoding="utf-8")
            return {
                "ok": True,
                "tool": "file_write",
                "result": {"path": str(target)},
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": "file_write",
                "result": None,
                "error": f"file_write failed: {e}",
            }

    def _handle_file_list(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Listet Dateien/Verzeichnisse unterhalb von data/files.
        Erwartet:
          - optional path: Unterverzeichnis relativ zu data/files (Default: ".")
        """
        rel_path = str(payload.get("path", "."))
        target = self._resolve_file_path(rel_path)
        if not target:
            return {
                "ok": False,
                "tool": "file_list",
                "result": None,
                "error": "Access outside file root is not allowed.",
            }

        try:
            if not target.exists():
                return {
                    "ok": False,
                    "tool": "file_list",
                    "result": None,
                    "error": "Path does not exist.",
                }

            if target.is_file():
                entries = [
                    {"name": target.name, "is_dir": False, "size": target.stat().st_size}
                ]
            else:
                entries = []
                for child in sorted(target.iterdir()):
                    try:
                        entries.append(
                            {
                                "name": child.name,
                                "is_dir": child.is_dir(),
                                "size": child.stat().st_size if child.is_file() else None,
                            }
                        )
                    except Exception:
                        continue

            return {
                "ok": True,
                "tool": "file_list",
                "result": {"path": str(target), "entries": entries},
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": "file_list",
                "result": None,
                "error": f"file_list failed: {e}",
            }

    def _handle_file_summary(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sehr einfache Textzusammenfassung (statistisch, kein LLM).
        Erwartet:
          - path: relative Pfadangabe unter data/files
        """
        path = payload.get("path")
        if not path:
            return {
                "ok": False,
                "tool": "file_summary",
                "result": None,
                "error": "Missing 'path' for file_summary.",
            }

        target = self._resolve_file_path(str(path))
        if not target:
            return {
                "ok": False,
                "tool": "file_summary",
                "result": None,
                "error": "Access outside file root is not allowed.",
            }

        if not target.is_file():
            return {
                "ok": False,
                "tool": "file_summary",
                "result": None,
                "error": "File does not exist.",
            }

        try:
            text = target.read_text(encoding="utf-8")
            num_chars = len(text)
            num_lines = text.count("\n") + 1 if text else 0
            num_words = len(text.split())

            preview = text[:400]

            summary = {
                "path": str(target),
                "num_chars": num_chars,
                "num_lines": num_lines,
                "num_words": num_words,
                "preview": preview,
            }

            return {
                "ok": True,
                "tool": "file_summary",
                "result": summary,
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": "file_summary",
                "result": None,
                "error": f"file_summary failed: {e}",
            }

    def _resolve_audio_input(self, relative_path: str) -> Optional[Path]:
        rel = Path(relative_path)
        full = (self._audio_input_root / rel).resolve()
        try:
            if hasattr(full, "is_relative_to"):
                if not full.is_relative_to(self._audio_input_root):
                    return None
            else:
                if str(self._audio_input_root.resolve()) not in str(full):
                    return None
        except Exception:
            return None
        return full

    def _resolve_audio_output(self, relative_path: str) -> Optional[Path]:
        rel = Path(relative_path)
        full = (self._audio_output_root / rel).resolve()
        try:
            if hasattr(full, "is_relative_to"):
                if not full.is_relative_to(self._audio_output_root):
                    return None
            else:
                if str(self._audio_output_root.resolve()) not in str(full):
                    return None
        except Exception:
            return None
        return full

    def _handle_speech_to_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Einfaches speech_to_text-Stub (Phase 7).
        Aktuell: Erwartet eine Textdatei unter data/audio und gibt deren Inhalt als "Transkript" zurück.
        Erwartet:
          - path: relative Pfadangabe unter data/audio
        """
        path = payload.get("path")
        if not path:
            return {
                "ok": False,
                "tool": "speech_to_text",
                "result": None,
                "error": "Missing 'path' for speech_to_text.",
            }

        target = self._resolve_audio_input(str(path))
        if not target:
            return {
                "ok": False,
                "tool": "speech_to_text",
                "result": None,
                "error": "Access outside audio input root is not allowed.",
            }

        if not target.is_file():
            return {
                "ok": False,
                "tool": "speech_to_text",
                "result": None,
                "error": "Audio input file does not exist.",
            }

        try:
            # Stub: Datei als UTF-8-Text lesen
            text = target.read_text(encoding="utf-8")
            return {
                "ok": True,
                "tool": "speech_to_text",
                "result": {"path": str(target), "transcript": text},
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": "speech_to_text",
                "result": None,
                "error": f"speech_to_text failed: {e}",
            }

    def _handle_text_to_speech(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Einfaches text_to_speech-Stub (Phase 7).
        Aktuell: Schreibt den Text als .txt-Datei unter data/audio_out.
        Erwartet:
          - text: str
          - optional output_name: str (Dateiname, Default: "tts_output.txt")
        """
        text = payload.get("text")
        if text is None:
            return {
                "ok": False,
                "tool": "text_to_speech",
                "result": None,
                "error": "Missing 'text' for text_to_speech.",
            }

        output_name = payload.get("output_name") or "tts_output.txt"
        output_path = self._resolve_audio_output(str(output_name))
        if not output_path:
            return {
                "ok": False,
                "tool": "text_to_speech",
                "result": None,
                "error": "Invalid output path for text_to_speech.",
            }

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(str(text), encoding="utf-8")
            return {
                "ok": True,
                "tool": "text_to_speech",
                "result": {"path": str(output_path)},
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": "text_to_speech",
                "result": None,
                "error": f"text_to_speech failed: {e}",
            }
