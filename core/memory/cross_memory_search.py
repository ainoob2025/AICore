from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.memory.episodic_memory import EpisodicMemory
from core.memory.semantic_memory import SemanticMemory
from core.rag.rag_service import RagService
from core.graph.graph_engine import GraphEngine


@dataclass
class CrossMemoryResult:
    source: str  # "episodic", "semantic", "rag", "graph"
    score: float
    data: Dict[str, Any]


class CrossMemorySearch:
    """
    Simple cross memory search over episodic, semantic, rag and graph.
    No LLM involved, just cheap heuristics.
    """

    def __init__(
        self,
        episodic: Optional[EpisodicMemory] = None,
        semantic: Optional[SemanticMemory] = None,
        rag_service: Optional[RagService] = None,
        graph_engine: Optional[GraphEngine] = None,
    ) -> None:
        self.episodic = episodic
        self.semantic = semantic
        self.rag_service = rag_service
        self.graph_engine = graph_engine

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    def cross_search(
        self,
        user_id: str,
        query: str,
        scopes: List[str],
        top_k: int = 10,
    ) -> List[CrossMemoryResult]:
        """
        Unified search over the requested scopes.
        scopes can contain any of: "episodic", "semantic", "rag", "graph".
        Returns a flat list of CrossMemoryResult sorted by score (desc).
        """
        scopes_set = set(scopes)
        results: List[CrossMemoryResult] = []

        if "episodic" in scopes_set and self.episodic is not None:
            results.extend(self._search_episodic(user_id=user_id, query=query))

        if "semantic" in scopes_set and self.semantic is not None:
            results.extend(self._search_semantic(user_id=user_id, query=query))

        if "rag" in scopes_set and self.rag_service is not None:
            results.extend(self._search_rag(user_id=user_id, query=query, top_k=top_k))

        if "graph" in scopes_set and self.graph_engine is not None:
            results.extend(self._search_graph(query=query, top_k=top_k))

        # sort by score desc
        results.sort(key=lambda r: r.score, reverse=True)
        if top_k > 0:
            results = results[:top_k]
        return results

    # ----------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------

    def _search_episodic(self, user_id: str, query: str) -> List[CrossMemoryResult]:
        # simple substring heuristic over recent events
        events = self.episodic.get_events(user_id=user_id, limit=50)
        q_lower = query.lower()
        results: List[CrossMemoryResult] = []

        for e in events:
            text = (
                str(e.get("user_message", "")) + " " +
                str(e.get("assistant_reply", ""))
            ).lower()
            if q_lower in text:
                # score = number of occurrences
                score = text.count(q_lower)
                results.append(
                    CrossMemoryResult(
                        source="episodic",
                        score=float(score),
                        data=e,
                    )
                )
        return results

    def _search_semantic(self, user_id: str, query: str) -> List[CrossMemoryResult]:
        items = self.semantic.get_knowledge(user_id=user_id, limit=100)
        q_lower = query.lower()
        results: List[CrossMemoryResult] = []

        for item in items:
            content = str(item.get("content", "")).lower()
            if q_lower in content:
                score = content.count(q_lower)
                results.append(
                    CrossMemoryResult(
                        source="semantic",
                        score=float(score),
                        data=item,
                    )
                )
        return results

    def _search_rag(
        self,
        user_id: str,
        query: str,
        top_k: int,
    ) -> List[CrossMemoryResult]:
        results: List[CrossMemoryResult] = []
        try:
            rag_results = self.rag_service.query(
                user_id=user_id,
                query_text=query,
                top_k=top_k,
                filters=None,
            )
        except Exception:
            return results

        for r in rag_results:
            score = float(r.get("score", 0.0))
            results.append(
                CrossMemoryResult(
                    source="rag",
                    score=score,
                    data=r,
                )
            )
        return results

    def _search_graph(
        self,
        query: str,
        top_k: int,
    ) -> List[CrossMemoryResult]:
        # interpret query as label in the graph
        try:
            related = self.graph_engine.query_related(
                label=query,
                relation=None,
                max_depth=1,
                top_k=top_k,
            )
        except Exception:
            return []

        results: List[CrossMemoryResult] = []
        for entry in related:
            # score can be simplified: 1.0 for now
            results.append(
                CrossMemoryResult(
                    source="graph",
                    score=1.0,
                    data=entry,
                )
            )
        return results