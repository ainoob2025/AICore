"""RAGEngine (enterprise-grade): persistent local knowledge base with SQLite FTS5.

Purpose:
- Store "knowledge chunks" (text + metadata) locally.
- Fast retrieval via FTS5 for small foundation models.
- Deterministic APIs, safe IO, no external dependencies.

Contract:
- upsert_chunk(source_id: str, chunk_id: str, text: str, meta: dict|None) -> dict
- delete_source(source_id: str) -> dict
- search(query: str, limit: int = 8, source_filter: list[str]|None = None) -> dict
- stats() -> dict
- vacuum() -> dict
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class RAGEngine:
    def __init__(self, db_path: Optional[str] = None) -> None:
        repo_root = Path(__file__).resolve().parents[2]  # core/rag -> repo
        default = repo_root / "data" / "rag" / "knowledge.sqlite"
        self._db_path = Path(db_path).resolve() if db_path else default
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self._db_path))
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        con.execute("PRAGMA temp_store=MEMORY;")
        con.execute("PRAGMA foreign_keys=ON;")
        return con

    def _init_db(self) -> None:
        with self._lock:
            con = self._connect()
            try:
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chunks (
                        source_id TEXT NOT NULL,
                        chunk_id  TEXT NOT NULL,
                        text      TEXT NOT NULL,
                        meta_json TEXT,
                        updated_ts REAL NOT NULL,
                        PRIMARY KEY (source_id, chunk_id)
                    );
                    """
                )
                # FTS5 virtual table with external content for fast search + snippet
                con.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
                    USING fts5(source_id, chunk_id, text, content='chunks', content_rowid='rowid');
                    """
                )
                # Triggers to keep FTS in sync
                con.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                      INSERT INTO chunks_fts(rowid, source_id, chunk_id, text) VALUES (new.rowid, new.source_id, new.chunk_id, new.text);
                    END;
                    """
                )
                con.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                      INSERT INTO chunks_fts(chunks_fts, rowid, source_id, chunk_id, text) VALUES('delete', old.rowid, old.source_id, old.chunk_id, old.text);
                    END;
                    """
                )
                con.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                      INSERT INTO chunks_fts(chunks_fts, rowid, source_id, chunk_id, text) VALUES('delete', old.rowid, old.source_id, old.chunk_id, old.text);
                      INSERT INTO chunks_fts(rowid, source_id, chunk_id, text) VALUES (new.rowid, new.source_id, new.chunk_id, new.text);
                    END;
                    """
                )
                con.commit()
            finally:
                con.close()

    def upsert_chunk(self, source_id: str, chunk_id: str, text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            if not isinstance(source_id, str) or not source_id.strip():
                return {"ok": False, "error": "INVALID_SOURCE_ID"}
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                return {"ok": False, "error": "INVALID_CHUNK_ID"}
            if not isinstance(text, str) or not text.strip():
                return {"ok": False, "error": "INVALID_TEXT"}
            if meta is not None and not isinstance(meta, dict):
                return {"ok": False, "error": "INVALID_META"}

            meta_json = json.dumps(meta, ensure_ascii=False) if meta else None
            ts = time.time()

            with self._lock:
                con = self._connect()
                try:
                    con.execute(
                        """
                        INSERT INTO chunks(source_id, chunk_id, text, meta_json, updated_ts)
                        VALUES(?,?,?,?,?)
                        ON CONFLICT(source_id, chunk_id) DO UPDATE SET
                          text=excluded.text,
                          meta_json=excluded.meta_json,
                          updated_ts=excluded.updated_ts;
                        """,
                        (source_id.strip(), chunk_id.strip(), text, meta_json, ts),
                    )
                    con.commit()
                finally:
                    con.close()

            return {"ok": True, "source_id": source_id.strip(), "chunk_id": chunk_id.strip()}
        except Exception as exc:
            return {"ok": False, "error": "RAG_UPSERT_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}

    def delete_source(self, source_id: str) -> Dict[str, Any]:
        try:
            if not isinstance(source_id, str) or not source_id.strip():
                return {"ok": False, "error": "INVALID_SOURCE_ID"}
            with self._lock:
                con = self._connect()
                try:
                    cur = con.execute("DELETE FROM chunks WHERE source_id = ?;", (source_id.strip(),))
                    con.commit()
                    return {"ok": True, "deleted": cur.rowcount}
                finally:
                    con.close()
        except Exception as exc:
            return {"ok": False, "error": "RAG_DELETE_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}

    def search(self, query: str, limit: int = 8, source_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            if not isinstance(query, str) or not query.strip():
                return {"ok": False, "error": "INVALID_QUERY"}
            if not isinstance(limit, int) or limit <= 0 or limit > 50:
                return {"ok": False, "error": "INVALID_LIMIT"}

            q = query.strip()
            filt = [s.strip() for s in (source_filter or []) if isinstance(s, str) and s.strip()]

            with self._lock:
                con = self._connect()
                try:
                    if filt:
                        # Build deterministic placeholders
                        ph = ",".join(["?"] * len(filt))
                        sql = f"""
                        SELECT source_id, chunk_id,
                               snippet(chunks_fts, 2, '[', ']', ' … ', 18) as snippet,
                               bm25(chunks_fts) as score
                        FROM chunks_fts
                        WHERE chunks_fts MATCH ? AND source_id IN ({ph})
                        ORDER BY score
                        LIMIT ?;
                        """
                        params: Tuple[Any, ...] = tuple([q] + filt + [limit])
                    else:
                        sql = """
                        SELECT source_id, chunk_id,
                               snippet(chunks_fts, 2, '[', ']', ' … ', 18) as snippet,
                               bm25(chunks_fts) as score
                        FROM chunks_fts
                        WHERE chunks_fts MATCH ?
                        ORDER BY score
                        LIMIT ?;
                        """
                        params = (q, limit)

                    rows = con.execute(sql, params).fetchall()
                    hits = [{"source_id": r[0], "chunk_id": r[1], "snippet": r[2], "score": float(r[3])} for r in rows]
                    return {"ok": True, "query": q, "limit": limit, "hits": hits}
                finally:
                    con.close()
        except Exception as exc:
            return {"ok": False, "error": "RAG_SEARCH_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}

    def stats(self) -> Dict[str, Any]:
        try:
            with self._lock:
                con = self._connect()
                try:
                    total = con.execute("SELECT COUNT(*) FROM chunks;").fetchone()[0]
                    sources = con.execute("SELECT COUNT(DISTINCT source_id) FROM chunks;").fetchone()[0]
                    return {"ok": True, "chunks": int(total), "sources": int(sources), "db_path": str(self._db_path)}
                finally:
                    con.close()
        except Exception as exc:
            return {"ok": False, "error": "RAG_STATS_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}

    def vacuum(self) -> Dict[str, Any]:
        try:
            with self._lock:
                con = self._connect()
                try:
                    con.execute("VACUUM;")
                    con.commit()
                    return {"ok": True}
                finally:
                    con.close()
        except Exception as exc:
            return {"ok": False, "error": "RAG_VACUUM_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}


if __name__ == "__main__":
    r = RAGEngine()
    r.upsert_chunk("manual", "1", "AI Core is a local modular AI operating system.", {"tags": ["aicore"]})
    print(r.stats())
    print(r.search("modular operating system", limit=5))
