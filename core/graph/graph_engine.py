from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class GraphNode:
    """
    Single node in the knowledge graph.
    type: e.g. "entity", "concept", "event"
    label: human readable name
    metadata: arbitrary extra info
    """
    id: str
    type: str
    label: str
    metadata: Dict[str, Any]


@dataclass
class GraphEdge:
    """
    Single edge between two nodes.
    relation: e.g. "owns", "works_on", "part_of"
    metadata: arbitrary extra info
    """
    id: str
    source_id: str
    target_id: str
    relation: str
    metadata: Dict[str, Any]


class GraphEngine:
    """
    Very simple file-based graph engine.

    Goals of this first version:
    - Persist nodes and edges under data/graph/index.json
    - Provide a simple add_fact(...) helper to create nodes and edges
    - Provide query_related(...) to traverse one hop and return related nodes
    - Keep everything deterministic and cheap, no LLM involved.
    """

    def __init__(self) -> None:
        # Project root: .../AICore
        self._root = Path(__file__).resolve().parents[2]
        self._data_dir = self._root / "data" / "graph"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._index_path = self._data_dir / "index.json"
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}

        self._load_index()

    # ----------------------------------------------------------
    # Loading / saving
    # ----------------------------------------------------------

    def _load_index(self) -> None:
        if not self._index_path.exists():
            self._nodes = {}
            self._edges = {}
            return

        try:
            with self._index_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self._nodes = {}
            self._edges = {}
            return

        nodes_raw = data.get("nodes", [])
        edges_raw = data.get("edges", [])

        self._nodes = {}
        for n in nodes_raw:
            try:
                node = GraphNode(
                    id=n["id"],
                    type=n.get("type", "entity"),
                    label=n.get("label", ""),
                    metadata=n.get("metadata", {}),
                )
                self._nodes[node.id] = node
            except Exception:
                continue

        self._edges = {}
        for e in edges_raw:
            try:
                edge = GraphEdge(
                    id=e["id"],
                    source_id=e["source_id"],
                    target_id=e["target_id"],
                    relation=e.get("relation", ""),
                    metadata=e.get("metadata", {}),
                )
                self._edges[edge.id] = edge
            except Exception:
                continue

    def _persist_index(self) -> None:
        data = {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "metadata": n.metadata,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "id": e.id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation": e.relation,
                    "metadata": e.metadata,
                }
                for e in self._edges.values()
            ],
        }
        try:
            with self._index_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Graph persistence must never crash the whole system
            pass

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    def add_fact(
        self,
        subject_label: str,
        relation: str,
        object_label: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        subject_type: str = "entity",
        object_type: str = "entity",
    ) -> Dict[str, Any]:
        """
        Adds (or reuses) two nodes and creates an edge between them.
        Returns a dict with node and edge ids.
        """
        if metadata is None:
            metadata = {}

        subject = self._get_or_create_node(
            type=subject_type,
            label=subject_label,
            extra_metadata={"source": source},
        )
        obj = self._get_or_create_node(
            type=object_type,
            label=object_label,
            extra_metadata={"source": source},
        )

        edge_id = str(uuid.uuid4())
        edge = GraphEdge(
            id=edge_id,
            source_id=subject.id,
            target_id=obj.id,
            relation=relation,
            metadata={**metadata, "source": source},
        )
        self._edges[edge.id] = edge
        self._persist_index()

        return {
            "subject_id": subject.id,
            "object_id": obj.id,
            "edge_id": edge.id,
        }

    def query_related(
        self,
        label: str,
        relation: Optional[str] = None,
        max_depth: int = 1,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Returns nodes that are related to the given label via one hop.
        For Phase 5 we keep it at depth 1, but the interface allows extension.
        """
        if max_depth < 1:
            max_depth = 1

        # find starting nodes
        start_ids = [
            n.id for n in self._nodes.values()
            if n.label == label
        ]
        if not start_ids:
            return []

        results: List[Dict[str, Any]] = []

        for edge in self._edges.values():
            if edge.source_id not in start_ids and edge.target_id not in start_ids:
                continue
            if relation is not None and edge.relation != relation:
                continue

            if edge.source_id in start_ids:
                other_id = edge.target_id
                direction = "outgoing"
            else:
                other_id = edge.source_id
                direction = "incoming"

            node = self._nodes.get(other_id)
            if not node:
                continue

            results.append(
                {
                    "edge_id": edge.id,
                    "relation": edge.relation,
                    "direction": direction,
                    "node": {
                        "id": node.id,
                        "type": node.type,
                        "label": node.label,
                        "metadata": node.metadata,
                    },
                    "edge_metadata": edge.metadata,
                }
            )

        # sort by label and limit
        results.sort(key=lambda r: r["node"]["label"])
        if top_k > 0:
            results = results[:top_k]
        return results

    # ----------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------

    def _get_or_create_node(
        self,
        type: str,
        label: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> GraphNode:
        """
        Look up an existing node by (type, label) or create a new one.
        """
        if extra_metadata is None:
            extra_metadata = {}

        for node in self._nodes.values():
            if node.type == type and node.label == label:
                # update metadata with any new info
                node.metadata.update(extra_metadata)
                return node

        node_id = str(uuid.uuid4())
        node = GraphNode(
            id=node_id,
            type=type,
            label=label,
            metadata=dict(extra_metadata),
        )
        self._nodes[node.id] = node
        return node