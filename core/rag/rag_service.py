from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RagDocument:
    """
    Ein einzelnes Dokument für den RAG-Index.
    """
    id: str
    user_id: str
    text: str
    metadata: Dict[str, Any]


class RagService:
    """
    Sehr einfache dateibasierte RAG-Implementierung.

    Funktionen dieser Version:
    - Persistenter Index unter data/rag/index.json
    - ingest(document_text, metadata) fügt neue Einträge hinzu
    - query(...) liefert Treffer durch einfache Wortüberschneidung
    - list_documents() für Debug/Inspect
    """

    def __init__(self) -> None:
        # Projekt-Root = .../AICore
        self._root = Path(__file__).resolve().parents[2]
        self._data_dir = self._root / "data" / "rag"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._index_path = self._data_dir / "index.json"
        self._index: List[Dict[str, Any]] = []
        self._load_index()

    # ----------------------------------------------------------
    # Laden/Speichern
    # ----------------------------------------------------------

    def _load_index(self) -> None:
        if not self._index_path.exists():
            self._index = []
            return

        try:
            with self._index_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._index = data
            else:
                self._index = []
        except Exception:
            self._index = []

    def _persist_index(self) -> None:
        try:
            with self._index_path.open("w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ----------------------------------------------------------
    # Öffentliche API
    # ----------------------------------------------------------

    def ingest(
        self,
        user_id: str,
        document_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Fügt ein Dokument hinzu.
        """
        if metadata is None:
            metadata = {}

        entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "text": document_text,
            "metadata": metadata,
        }
        self._index.append(entry)
        self._persist_index()
        return entry

    def query(
        self,
        user_id: Optional[str],
        query_text: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lieferung relevanter Einträge durch simple Wortüberschneidung.
        """
        if filters is None:
            filters = {}

        query_tokens = _tokenize(query_text)
        results: List[Dict[str, Any]] = []

        for entry in self._index:
            if user_id is not None and entry.get("user_id") != user_id:
                continue

            if not _match_filters(entry.get("metadata", {}), filters):
                continue

            score = _overlap_score(query_tokens, _tokenize(entry.get("text", "")))
            if score <= 0.0:
                continue

            results.append(
                {
                    "id": entry["id"],
                    "user_id": entry["user_id"],
                    "score": score,
                    "text_preview": entry["text"][:200],
                    "metadata": entry["metadata"],
                }
            )

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def list_documents(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Liefert eine kompakte Debug-Liste aller Einträge oder eines Users.
        """
        docs: List[Dict[str, Any]] = []
        for entry in self._index:
            if user_id is not None and entry.get("user_id") != user_id:
                continue
            docs.append(
                {
                    "id": entry["id"],
                    "user_id": entry["user_id"],
                    "metadata": entry["metadata"],
                    "text_preview": entry["text"][:120],
                }
            )
        return docs


# ----------------------------------------------------------
# Hilfsfunktionen
# ----------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    return [
        t for t in "".join(
            (ch.lower() if ch.isalnum() else " ") for ch in text
        ).split()
        if t
    ]


def _match_filters(metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if metadata.get(key) != expected:
            return False
    return True


def _overlap_score(query_tokens: List[str], doc_tokens: List[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    qs = set(query_tokens)
    ds = set(doc_tokens)
    overlap = len(qs & ds)
    if overlap == 0:
        return 0.0
    return float(overlap) / float(len(qs) + 1)