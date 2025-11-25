from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class SelfImprovementAgent:
    """
    SelfImprovementAgent (Phase 6 – Selbstoptimierung, erste Version).

    Aufgaben (Iteration 1):
    - Lies Task-Feedback-Logs aus data/logs/task_feedback.jsonl.
    - Lies Tool-Statistiken aus data/tools/stats.json.
    - Erzeuge daraus einfache Konfigurations-Strategien in config/strategies.json:
        - tool_priorities: Empfehlungsscores pro Tool
        - planner: Basiswerte (z.B. default_max_steps)
        - retries: Basis-Retry-Counts
    Kein RL, kein Finetuning – nur Heuristiken auf Basis vorhandener Logs.
    """

    def __init__(
        self,
        feedback_log_path: str = "data/logs/task_feedback.jsonl",
        tool_stats_path: str = "data/tools/stats.json",
        strategies_path: str = "config/strategies.json",
    ) -> None:
        self.feedback_log_file = Path(feedback_log_path)
        self.tool_stats_file = Path(tool_stats_path)
        self.strategies_file = Path(strategies_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_analysis(self) -> Dict[str, Any]:
        """
        Führt eine komplette Self-Improvement-Runde aus:
        - Lädt Logs + Tool-Stats
        - Berechnet neue Strategien
        - Schreibt config/strategies.json
        - Gibt die Strategien als Dict zurück
        """
        feedback_entries = self._load_feedback_entries()
        tool_stats = self._load_tool_stats()

        strategies = self._build_strategies(feedback_entries, tool_stats)
        self._save_strategies(strategies)

        return strategies

    # ------------------------------------------------------------------
    # Intern: Daten laden
    # ------------------------------------------------------------------

    def _load_feedback_entries(self) -> List[Dict[str, Any]]:
        """
        Lädt alle Task-Feedback-Einträge aus der JSON-Lines-Datei.
        Format: eine JSON-Struktur pro Zeile.
        Fehlerhafte Zeilen werden ignoriert.
        """
        entries: List[Dict[str, Any]] = []

        if not self.feedback_log_file.exists():
            return entries

        try:
            with self.feedback_log_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            entries.append(obj)
                    except Exception:
                        # Einzelne fehlerhafte Zeilen ignorieren
                        continue
        except Exception:
            # Log komplett ignorieren, falls etwas schiefgeht
            return []

        return entries

    def _load_tool_stats(self) -> Dict[str, Any]:
        """
        Lädt data/tools/stats.json, falls vorhanden.
        """
        if not self.tool_stats_file.exists():
            return {}

        try:
            with self.tool_stats_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            return {}

        return {}

    # ------------------------------------------------------------------
    # Intern: Strategien bauen
    # ------------------------------------------------------------------

    def _build_strategies(
        self,
        feedback_entries: List[Dict[str, Any]],
        tool_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Baut eine einfache Strategiekonfiguration.
        Heuristiken (Iteration 1):
        - tool_priorities:
            - Basis: Tool-Statistiken (Success-Rate, Latenz)
            - Optionale Anpassung anhand Task-Feedback (z.B. Häufigkeit in erfolgreichen Tasks)
        - planner:
            - default_max_steps wird konservativ auf 3 gesetzt
        - retries:
            - tool_call auf 1 gesetzt
        """
        tool_priorities: Dict[str, float] = {}

        # 1) Heuristik mit Tool-Statistiken
        for tool_name, stats in tool_stats.items():
            try:
                success = float(stats.get("success_count", 0) or 0)
                failure = float(stats.get("failure_count", 0) or 0)
                total = success + failure
                avg_latency = float(stats.get("avg_latency", 0.0) or 0.0)

                if total > 0:
                    reliability = success / total
                else:
                    reliability = 0.5  # neutraler Default

                # Je schneller, desto höher der Score (einfache 1/(1+latency)-Formel)
                latency_factor = 1.0 / (1.0 + max(avg_latency, 0.0))

                score = reliability * latency_factor
                tool_priorities[tool_name] = float(round(score, 4))
            except Exception:
                continue

        # 2) Optional: Feedback mit einfließen lassen (Iteration 1: nur Häufigkeit erfolgreicher Tasks)
        # Wir werten vorerst nur aus, wie oft ein Tool in Tasks ohne Errors vorkommt.
        tool_success_counter: Dict[str, int] = {}

        for entry in feedback_entries:
            try:
                errors = entry.get("errors") or []
                used_tools = entry.get("used_tools") or []
                if not isinstance(used_tools, list):
                    continue

                # Wenn keine Errors, Tool-Häufigkeit positiv werten
                if not errors:
                    for t in used_tools:
                        if not isinstance(t, str):
                            continue
                        tool_success_counter[t] = tool_success_counter.get(t, 0) + 1
            except Exception:
                continue

        # Boost für Tools mit vielen erfolgreichen Tasks
        if tool_success_counter:
            max_count = max(tool_success_counter.values())
        else:
            max_count = 0

        if max_count > 0:
            for tool_name, count in tool_success_counter.items():
                base = tool_priorities.get(tool_name, 0.5)
                boost = (count / max_count) * 0.2  # bis zu +0.2
                tool_priorities[tool_name] = float(round(base + boost, 4))

        strategies: Dict[str, Any] = {
            "version": 1,
            "updated_at": datetime.utcnow().isoformat(),
            "tool_priorities": tool_priorities,
            "planner": {
                "default_max_steps": 3,
            },
            "retries": {
                "tool_call": 1,
            },
        }

        return strategies

    # ------------------------------------------------------------------
    # Intern: Strategien speichern
    # ------------------------------------------------------------------

    def _save_strategies(self, strategies: Dict[str, Any]) -> None:
        """
        Schreibt config/strategies.json.
        """
        try:
            self.strategies_file.parent.mkdir(parents=True, exist_ok=True)
            with self.strategies_file.open("w", encoding="utf-8") as f:
                json.dump(strategies, f, ensure_ascii=False, indent=2)
        except Exception:
            # Self-Improvement darf den Core nie crashen
            pass