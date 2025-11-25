from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from pathlib import Path

from core.kernel.master_agent import MasterAgent
from core.kernel.request_types import CoreRequest, CoreResponse, CoreError
from core.metrics.metrics_logger import MetricsLogger


class BenchmarkSuite:
    """
    Benchmark-Suite für Phase 8 – Evaluation / Benchmarks / Stabilisierung.

    Ziele:
    - Standard-Tasks ausführen (Chat, Tool, Planner).
    - Laufzeit und Kernmetriken pro Task messen.
    - Failure-Kategorien ableiten.
    - Ergebnisse als JSONL unter data/metrics/ ablegen.
    """

    def __init__(self, run_name: Optional[str] = None) -> None:
        self.agent = MasterAgent()
        self.metrics = MetricsLogger(base_dir="data/metrics", run_name=run_name)

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    def run_all(self) -> Dict[str, Any]:
        """
        Führt die Standard-Benchmarks aus und gibt eine Zusammenfassung zurück.

        Aktuell:
        - chat_simple
        - tool_uppercase
        - rag_query_simple
        - planner_simple
        """
        results: Dict[str, Any] = {}

        results["chat_simple"] = self._run_chat_simple()
        results["tool_uppercase"] = self._run_tool_uppercase()
        results["rag_query_simple"] = self._run_rag_query_simple()
        results["planner_simple"] = self._run_planner_simple()

        summary = {
            "run_id": self.metrics.run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "tasks": results,
        }

        # Zusammenfassung separat loggen
        self.metrics.log_event("benchmark_summary", summary)

        return summary

    # ------------------------------------------------------------------
    # Einzel-Benchmarks
    # ------------------------------------------------------------------

    def _run_chat_simple(self) -> Dict[str, Any]:
        """
        Einfache Chat-Aufgabe.
        """
        req = CoreRequest(
            trace_id="",
            session_id="bench-chat",
            user_id="benchmark",
            input_type="chat",
            message="Erkläre in 2–3 Sätzen den Unterschied zwischen RAM und SSD.",
            tool_name=None,
            tool_payload=None,
            context_hints=[],
        )

        start = time.perf_counter()
        res = self.agent.handle_request(req)
        duration = max(time.perf_counter() - start, 0.0)

        metrics = self._build_metrics("chat_simple", req, res, duration)
        self._log_benchmark_result(metrics)
        return metrics

    def _run_tool_uppercase(self) -> Dict[str, Any]:
        """
        Tool-Benchmark: uppercase-Tool.
        """
        payload = {"text": "phase 8 benchmark"}
        req = CoreRequest(
            trace_id="",
            session_id="bench-tool-uppercase",
            user_id="benchmark",
            input_type="tool",
            message=None,
            tool_name="uppercase",
            tool_payload=payload,
            context_hints=[],
        )

        start = time.perf_counter()
        res = self.agent.handle_request(req)
        duration = max(time.perf_counter() - start, 0.0)

        metrics = self._build_metrics("tool_uppercase", req, res, duration)
        self._log_benchmark_result(metrics)
        return metrics

    def _run_rag_query_simple(self) -> Dict[str, Any]:
        """
        RAG-Benchmark: einfache Wissensabfrage.
        """
        payload = {"query": "Was ist AI Core in einem Satz?"}
        req = CoreRequest(
            trace_id="",
            session_id="bench-rag",
            user_id="benchmark",
            input_type="tool",
            message=None,
            tool_name="rag_query",
            tool_payload=payload,
            context_hints=[],
        )

        start = time.perf_counter()
        res = self.agent.handle_request(req)
        duration = max(time.perf_counter() - start, 0.0)

        metrics = self._build_metrics("rag_query_simple", req, res, duration)
        self._log_benchmark_result(metrics)
        return metrics

    def _run_planner_simple(self) -> Dict[str, Any]:
        """
        Planner-Benchmark: einfacher Planungs-Task.
        """
        req = CoreRequest(
            trace_id="",
            session_id="bench-planner",
            user_id="benchmark",
            input_type="planner",
            message="Plane in kurzen Schritten, wie ich meinen Arbeitstag strukturiere.",
            tool_name=None,
            tool_payload=None,
            context_hints=[],
        )

        start = time.perf_counter()
        res = self.agent.handle_request(req)
        duration = max(time.perf_counter() - start, 0.0)

        metrics = self._build_metrics("planner_simple", req, res, duration)
        self._log_benchmark_result(metrics)
        return metrics

    # ------------------------------------------------------------------
    # Metrics-Aufbau
    # ------------------------------------------------------------------

    def _build_metrics(
        self,
        task_name: str,
        req: CoreRequest,
        res: CoreResponse,
        duration_sec: float,
    ) -> Dict[str, Any]:
        """
        Baut das Metrik-Dict basierend auf CoreRequest/CoreResponse.
        Deckt ab:
        - Laufzeit
        - Fehleranzahl
        - Failure-Kategorie
        - Planner-Schritte
        - Memory-Operationen
        - Kontextgröße (Input-Länge)
        """
        errors: List[CoreError] = list(res.errors or [])
        error_count = len(errors)

        failure_category = self._classify_failure(errors)

        # Planner-Schritte (falls Planner genutzt wurde)
        planner_steps = 0
        if res.planner_trace:
            try:
                # Annahme: erster Eintrag ist der Hauptplan
                plan0 = res.planner_trace[0]
                if isinstance(plan0, dict):
                    steps = plan0.get("steps") or []
                    if isinstance(steps, list):
                        planner_steps = len(steps)
            except Exception:
                planner_steps = 0

        # Memory-Operationen
        memory_ops_count = len(res.memory_ops or [])

        # Kontextgröße: Input-Text-Länge (Heuristik)
        input_text = req.message or ""
        context_chars = len(input_text)

        metrics: Dict[str, Any] = {
            "task_name": task_name,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_sec": float(round(duration_sec, 4)),
            "input_type": req.input_type,
            "failure_category": failure_category,
            "error_count": error_count,
            "planner_steps": planner_steps,
            "memory_ops_count": memory_ops_count,
            "context_chars": context_chars,
            "trace_id": res.trace_id,
            "session_id": req.session_id,
        }

        return metrics

    def _classify_failure(self, errors: List[CoreError]) -> str:
        """
        Ordnet Fehler einer groben Failure-Kategorie zu.

        Roadmap-Kategorien:
        - planning_error
        - tool_error
        - memory_miss
        - timeout
        - hallucination_suspect
        - ok (wenn keine Fehler)
        """
        if not errors:
            return "ok"

        # Wir betrachten den ersten Fehler als Hauptfehler
        err = errors[0]
        etype = (err.error_type or "").lower()
        msg = (err.message or "").lower()

        if "planner" in etype or "plan" in etype:
            return "planning_error"
        if "tool" in etype:
            return "tool_error"
        if "memory" in etype:
            return "memory_miss"
        if "timeout" in etype or "timed out" in msg:
            return "timeout"
        if "hallucination" in etype or "hallucination" in msg:
            return "hallucination_suspect"

        return "unknown"

    # ------------------------------------------------------------------
    # Logging-Helfer
    # ------------------------------------------------------------------

    def _log_benchmark_result(self, metrics: Dict[str, Any]) -> None:
        """
        Loggt ein einzelnes Benchmark-Result als Event in data/metrics.
        """
        try:
            self.metrics.log_event("benchmark_result", metrics)
        except Exception:
            # Metrics-Fehler dürfen nie den Benchmark-Lauf killen
            pass