from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class PolicyOptimizer:
    """
    Phase 9 – Offline-Policy-Optimierung / Auto-Improvement (RL-light).

    Nutzt:
      - Task-Feedback-Logs (data/logs/task_feedback.jsonl)
      - Aktuelle Strategien (config/strategies.json)

    Aufgaben:
      - Tool-spezifische Rewards aus Logs berechnen.
      - tool_priorities datengetrieben anpassen.
      - Versionen in config/strategies_versions.jsonl protokollieren.

    KEIN Online-RL, KEIN Finetuning der Modelle – nur Policy/Heuristik.
    """

    def __init__(
        self,
        strategies_path: str = "config/strategies.json",
        feedback_log_path: str = "data/logs/task_feedback.jsonl",
        versions_path: str = "config/strategies_versions.jsonl",
    ) -> None:
        self.strategies_file = Path(strategies_path)
        self.feedback_log_file = Path(str(feedback_log_path))
        self.versions_file = Path(str(versions_path))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(self) -> Dict[str, Any]:
        """
        Führt eine komplette Policy-Optimierung aus und gibt ein Summary zurück.

        Rückgabe:
            {
              "version_id": str,
              "tool_rewards": {tool_name: avg_reward, ...},
              "current_strategies": {...},
              "optimized_strategies": {...},
            }
        """
        current = self._load_current_strategies()
        feedback_entries = self._load_feedback_entries()
        tool_rewards = self._compute_tool_rewards(feedback_entries)

        optimized = self._apply_rewards_to_strategies(current, tool_rewards)
        version_id = self._save_version(current, optimized, tool_rewards)

        return {
            "version_id": version_id,
            "tool_rewards": tool_rewards,
            "current_strategies": current,
            "optimized_strategies": optimized,
        }

    # ------------------------------------------------------------------
    # Intern: Strategien laden
    # ------------------------------------------------------------------

    def _load_current_strategies(self) -> Dict[str, Any]:
        """
        Lädt config/strategies.json oder liefert einen Default zurück.
        """
        if self.strategies_file.is_file():
            try:
                with self.strategies_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

        # Fallback-Default (kompatibel zu Phase 6)
        return {
            "version": 1,
            "updated_at": "1970-01-01T00:00:00Z",
            "tool_priorities": {},
            "planner": {
                "default_max_steps": 3,
            },
            "retries": {
                "tool_call": 1,
            },
        }

    # ------------------------------------------------------------------
    # Intern: Feedback laden
    # ------------------------------------------------------------------

    def _load_feedback_entries(self) -> List[Dict[str, Any]]:
        """
        Lädt alle Task-Feedback-Einträge aus data/logs/task_feedback.jsonl, falls vorhanden.
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
                        continue
        except Exception:
            return []

        return entries

    # ------------------------------------------------------------------
    # Intern: Rewards berechnen
    # ------------------------------------------------------------------

    def _compute_tool_rewards(self, feedback_entries: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Berechnet durchschnittliche Rewards pro Tool.

        Heuristik:
        - Basis:
            - Keine Errors -> base_reward = 1.0
            - Mit Errors   -> base_reward = 0.3
        - Dauer-Penalty:
            - duration_sec wird auf 0..30s gecappt
            - time_penalty = duration_sec / 30
            - reward = base_reward - 0.5 * time_penalty
        - Für jedes Tool in used_tools wird dieser reward addiert.
        - Am Ende durchschnittlicher Reward pro Tool.
        """
        total: Dict[str, float] = {}
        counts: Dict[str, int] = {}

        for entry in feedback_entries:
            try:
                used_tools = entry.get("used_tools") or []
                if not isinstance(used_tools, list):
                    continue

                errors = entry.get("errors") or []
                duration = float(entry.get("duration_sec") or 0.0)

                base_reward = 1.0 if not errors else 0.3
                d = max(0.0, min(duration, 30.0))
                time_penalty = d / 30.0
                reward = base_reward - 0.5 * time_penalty

                for t in used_tools:
                    if not isinstance(t, str):
                        continue
                    total[t] = total.get(t, 0.0) + reward
                    counts[t] = counts.get(t, 0) + 1
            except Exception:
                continue

        avg_rewards: Dict[str, float] = {}
        for tool, sum_reward in total.items():
            c = counts.get(tool, 0)
            if c > 0:
                avg_rewards[tool] = float(round(sum_reward / float(c), 4))

        return avg_rewards

    # ------------------------------------------------------------------
    # Intern: Rewards auf Strategien anwenden
    # ------------------------------------------------------------------

    def _apply_rewards_to_strategies(
        self,
        strategies: Dict[str, Any],
        tool_rewards: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Passt tool_priorities an, basierend auf den berechneten Rewards.

        Heuristik:
        - Wir betrachten den Durchschnitts-Reward pro Tool.
        - Berechnen den globalen Mittelwert.
        - Für jedes Tool:
            delta_raw = reward - mean_reward
            delta = clamp(delta_raw * 0.5, -0.3, +0.3)
            new_priority = old_priority + delta
        - old_priority Default = 0.5
        """
        optimized = dict(strategies)
        priorities = dict(optimized.get("tool_priorities") or {})

        if not tool_rewards:
            # Keine Daten -> Strategie unverändert, aber Timestamp updaten
            optimized["updated_at"] = datetime.utcnow().isoformat()
            optimized["tool_priorities"] = priorities
            return optimized

        values = list(tool_rewards.values())
        mean_reward = sum(values) / float(len(values)) if values else 0.0

        for tool, reward in tool_rewards.items():
            base = float(priorities.get(tool, 0.5))

            delta_raw = reward - mean_reward
            delta = delta_raw * 0.5

            if delta > 0.3:
                delta = 0.3
            elif delta < -0.3:
                delta = -0.3

            new_priority = base + delta
            priorities[tool] = float(round(new_priority, 4))

        optimized["tool_priorities"] = priorities
        optimized["updated_at"] = datetime.utcnow().isoformat()

        return optimized

    # ------------------------------------------------------------------
    # Intern: Version speichern
    # ------------------------------------------------------------------

    def _save_version(
        self,
        current: Dict[str, Any],
        optimized: Dict[str, Any],
        tool_rewards: Dict[str, float],
    ) -> str:
        """
        Speichert eine neue Strategien-Version in config/strategies_versions.jsonl.
        """
        version_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

        record: Dict[str, Any] = {
            "version_id": version_id,
            "created_at": datetime.utcnow().isoformat(),
            "tool_rewards": tool_rewards,
            "optimized_strategies": optimized,
        }

        try:
            self.versions_file.parent.mkdir(parents=True, exist_ok=True)
            with self.versions_file.open("a", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False)
                f.write("\n")
        except Exception:
            # Versionierung ist Best-Effort, darf nie den Core crashen
            pass

        return version_id