"""ContextPolicy (enterprise-grade): task context assembly + post-task cleanup/distillation.

Purpose:
- Before each task: retrieve only necessary context from Episodic (MemoryOS) + Semantic (RAGEngine)
- After each task: distill outcome into long-term Semantic memory (RAGEngine) + keep short episodic trace
- Deterministic, resource-aware (hard budgets), safe defaults, no external deps

Contract:
- build_context(task: str, session_id: str="default") -> dict
- finalize_task(task: str, assistant_output: str, session_id: str="default", status: str="ok") -> dict
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional

from core.memory.memory_os import MemoryOS
from core.rag.rag_engine import RAGEngine


class ContextPolicy:
    def __init__(
        self,
        memory: Optional[MemoryOS] = None,
        rag: Optional[RAGEngine] = None,
        max_ephemeral_chars: int = 18_000,
        max_episodic_turns: int = 20,
        rag_hits: int = 8,
        rag_snippet_chars: int = 900,
    ) -> None:
        self.memory = memory or MemoryOS()
        self.rag = rag or RAGEngine()

        # Hard budgets (deterministic, cheap)
        self.max_ephemeral_chars = int(max_ephemeral_chars)
        self.max_episodic_turns = int(max_episodic_turns)
        self.rag_hits = int(rag_hits)
        self.rag_snippet_chars = int(rag_snippet_chars)

    def build_context(self, task: str, session_id: str = "default") -> Dict[str, Any]:
        """
        Returns a context package for an agent/model:
        {
          ok: bool,
          task: str,
          session_id: str,
          episodic: [turns...],
          semantic: [hits...],
          context_text: str,
          budget: {...},
          error/details...
        }
        """
        out: Dict[str, Any] = {
            "ok": False,
            "task": task,
            "session_id": session_id,
            "episodic": [],
            "semantic": [],
            "context_text": "",
            "budget": {
                "max_ephemeral_chars": self.max_ephemeral_chars,
                "max_episodic_turns": self.max_episodic_turns,
                "rag_hits": self.rag_hits,
                "rag_snippet_chars": self.rag_snippet_chars,
            },
            "error": None,
            "details": None,
        }

        try:
            if not isinstance(task, str) or not task.strip():
                out["error"] = "INVALID_TASK"
                return out

            # 1) Episodic slice (recent turns)
            turns = self.memory.get_conversation(session_id=session_id, limit=self.max_episodic_turns)
            out["episodic"] = turns

            # 2) Semantic retrieval (RAG)
            rag_res = self.rag.search(task.strip(), limit=self.rag_hits)
            if rag_res.get("ok"):
                hits = rag_res.get("hits", [])
                # Normalize to a compact shape for prompt injection
                semantic = []
                for h in hits:
                    snippet = (h.get("snippet") or "")[: self.rag_snippet_chars]
                    semantic.append(
                        {
                            "source_id": h.get("source_id"),
                            "chunk_id": h.get("chunk_id"),
                            "snippet": snippet,
                            "score": h.get("score"),
                        }
                    )
                out["semantic"] = semantic
            else:
                out["semantic"] = []
                out["details"] = {"rag_error": rag_res.get("error"), "rag_details": rag_res.get("details")}

            # 3) Compose deterministic context text (hard char budget)
            parts: List[str] = []
            parts.append("### TASK")
            parts.append(task.strip())

            parts.append("\n### EPISODIC (recent conversation)")
            for t in turns:
                role = str(t.get("role", "user"))
                msg = str(t.get("message", ""))
                parts.append(f"- {role}: {msg}")

            parts.append("\n### SEMANTIC (retrieved knowledge snippets)")
            if out["semantic"]:
                for h in out["semantic"]:
                    sid = h.get("source_id")
                    cid = h.get("chunk_id")
                    sn = h.get("snippet", "")
                    parts.append(f"- [{sid}/{cid}] {sn}")
            else:
                parts.append("- (none)")

            ctx = "\n".join(parts)

            # enforce max_ephemeral_chars
            if len(ctx) > self.max_ephemeral_chars:
                ctx = ctx[-self.max_ephemeral_chars :]

            out["context_text"] = ctx
            out["ok"] = True
            return out

        except Exception as exc:
            out["error"] = "CONTEXT_BUILD_EXCEPTION"
            out["details"] = {"type": type(exc).__name__, "message": str(exc)}
            return out

    def finalize_task(
        self,
        task: str,
        assistant_output: str,
        session_id: str = "default",
        status: str = "ok",
    ) -> Dict[str, Any]:
        """
        Distills the finished task into long-term semantic memory + minimal episodic trace.
        Writes:
        - MemoryOS: adds an assistant turn (output)
        - RAGEngine: upserts a distilled summary chunk under source_id = "task_summaries"
        """
        out: Dict[str, Any] = {"ok": False, "error": None, "details": None, "summary_chunk": None}

        try:
            if not isinstance(task, str) or not task.strip():
                out["error"] = "INVALID_TASK"
                return out
            if not isinstance(assistant_output, str):
                out["error"] = "INVALID_ASSISTANT_OUTPUT"
                return out
            if not isinstance(status, str) or not status.strip():
                out["error"] = "INVALID_STATUS"
                return out

            # 1) Always keep episodic trace (short, deterministic)
            self.memory.add_turn("assistant", assistant_output, session_id=session_id, status=status.strip())

            # 2) Distill summary for long-term semantic memory
            # Deterministic, compact, with hash-based chunk_id to avoid duplicates.
            now = time.strftime("%Y-%m-%d", time.localtime())
            raw = f"{session_id}|{now}|{task.strip()}|{assistant_output[:2000]}"
            chunk_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

            distilled = self._distill(task.strip(), assistant_output)

            meta = {
                "session_id": session_id,
                "status": status.strip(),
                "date": now,
                "ts": time.time(),
                "kind": "task_summary",
            }

            res = self.rag.upsert_chunk("task_summaries", chunk_id, distilled, meta)
            if not res.get("ok"):
                out["error"] = "RAG_UPSERT_FAILED"
                out["details"] = res
                return out

            out["summary_chunk"] = {"source_id": "task_summaries", "chunk_id": chunk_id}
            out["ok"] = True
            return out

        except Exception as exc:
            out["error"] = "FINALIZE_EXCEPTION"
            out["details"] = {"type": type(exc).__name__, "message": str(exc)}
            return out

    def _distill(self, task: str, assistant_output: str) -> str:
        """
        Deterministic distillation without LLM calls:
        - Keep task
        - Keep first N chars of output
        - Keep last N chars of output (often contains final result)
        """
        head_n = 1200
        tail_n = 1200
        out = assistant_output.strip()

        head = out[:head_n]
        tail = out[-tail_n:] if len(out) > tail_n else ""

        parts = [
            "### TASK",
            task,
            "",
            "### RESULT (distilled)",
            head,
        ]
        if tail and tail != head:
            parts += ["", "### RESULT (tail)", tail]

        # Hard cap to keep semantic memory clean
        text = "\n".join(parts)
        if len(text) > 5000:
            text = text[:5000]
        return text


if __name__ == "__main__":
    cp = ContextPolicy()
    ctx = cp.build_context("test task: remember that cats are mammals", session_id="tctx")
    print(ctx["ok"], len(ctx["context_text"]))
    fin = cp.finalize_task("test task", "done. cats are mammals.", session_id="tctx")
    print(fin)
