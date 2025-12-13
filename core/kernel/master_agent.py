"""Kernel MasterAgent (enterprise-grade): Planner-driven execution + tool-call canonicalization + checkpoints + resume."""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.kernel.plan_state_store import PlanStateStore
from core.kernel.planner import Planner
from core.memory.context_policy import ContextPolicy
from core.memory.memory_os import MemoryOS
from core.rag.rag_engine import RAGEngine
from core.tools.tool_router import ToolRouter


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def _find_first(patterns: List[str], text: str) -> Optional[str]:
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            v = (m.group(1) or "").strip().strip("'\"")
            if v:
                return v
    return None


def _resolve_lm_config() -> Tuple[str, str]:
    env_url = (os.environ.get("AICORE_LMSTUDIO_BASE_URL") or "").strip()
    env_model = (os.environ.get("AICORE_MAIN_MODEL_ID") or "").strip()
    if env_url and env_model:
        return env_url.rstrip("/"), env_model

    providers = _read_text(os.path.join("config", "providers.yaml"))
    models = _read_text(os.path.join("config", "models.yaml"))

    url = _find_first([r"base_url\s*:\s*(.+)$", r"url\s*:\s*(.+)$", r"endpoint\s*:\s*(.+)$"], providers)
    model_id = _find_first([r"model_id\s*:\s*(.+)$", r"id\s*:\s*(.+)$", r"model\s*:\s*(.+)$"], models)

    if not url:
        url = env_url or "http://localhost:1234"
    if not model_id:
        model_id = env_model or "local-model"

    return url.rstrip("/"), model_id


@dataclass(frozen=True)
class LLMResult:
    ok: bool
    text: str
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class LMStudioClient:
    def __init__(self, base_url: str, model_id: str, timeout_sec: int = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.timeout_sec = int(timeout_sec)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 1800) -> LLMResult:
        try:
            payload = {
                "model": self.model_id,
                "messages": messages,
                "temperature": float(temperature),
                "max_tokens": int(max_tokens),
                "stream": False,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/v1/chat/completions",
                data=data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw = resp.read()
            obj = json.loads(raw.decode("utf-8", errors="replace"))
            choices = obj.get("choices") or []
            if not choices:
                return LLMResult(False, "", "NO_CHOICES", {"response": obj})
            msg = (choices[0].get("message") or {})
            text = msg.get("content") or ""
            if not isinstance(text, str):
                text = str(text)
            return LLMResult(True, text)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            return LLMResult(False, "", "HTTP_ERROR", {"code": exc.code, "reason": str(exc.reason), "body": body})
        except Exception as exc:
            return LLMResult(False, "", "LLM_EXCEPTION", {"type": type(exc).__name__, "message": str(exc)})


class MasterAgent:
    def __init__(self) -> None:
        self.memory = MemoryOS()
        self.rag = RAGEngine()
        self.context = ContextPolicy(memory=self.memory, rag=self.rag)
        self.tools = ToolRouter()
        self.planner = Planner()
        self.plan_store = PlanStateStore(root_dir=".runtime/plans")

        base_url, model_id = _resolve_lm_config()
        self.llm = LMStudioClient(base_url=base_url, model_id=model_id)

        self._warmup_lock = threading.Lock()
        self._warmup_started = False
        self._warmup_done = False
        self._warmup_ok = False
        self._warmup_ms = 0
        self._warmup_error: Optional[Dict[str, Any]] = None

    def warmup_status(self) -> Dict[str, Any]:
        with self._warmup_lock:
            return {
                "warmup_started": self._warmup_started,
                "warmup_done": self._warmup_done,
                "warmup_ok": self._warmup_ok,
                "warmup_ms": self._warmup_ms,
                "warmup_error": self._warmup_error,
            }

    def ensure_warmup_async(self) -> None:
        with self._warmup_lock:
            if self._warmup_started:
                return
            self._warmup_started = True

        def _run() -> None:
            t0 = time.perf_counter()
            ok = False
            err: Optional[Dict[str, Any]] = None
            try:
                r = self.llm.chat(
                    [{"role": "system", "content": "Reply with exactly: OK"}, {"role": "user", "content": "OK"}],
                    temperature=0.0,
                    max_tokens=8,
                )
                ok = bool(r.ok)
                if not r.ok:
                    err = {"error": r.error, "details": r.details}
            except Exception as exc:
                ok = False
                err = {"type": type(exc).__name__, "message": str(exc)}
            ms = int((time.perf_counter() - t0) * 1000)

            with self._warmup_lock:
                self._warmup_done = True
                self._warmup_ok = ok
                self._warmup_ms = ms
                self._warmup_error = err

        threading.Thread(target=_run, daemon=True).start()

    def _checkpoint(self, plan: Dict[str, Any], session_id: str, status: str) -> Dict[str, Any]:
        if not isinstance(plan.get("plan_id"), str) or not plan.get("plan_id"):
            plan["plan_id"] = f"{session_id}_{int(time.time()*1000)}"
        if "goal" not in plan or not isinstance(plan.get("goal"), str):
            plan["goal"] = str(plan.get("goal") or "")

        try:
            state = self.plan_store.wrap(plan, status=status, cursors={"session_id": session_id})
            res = self.plan_store.save(state)
            return {"ok": True, "status": status, "path": res.path, "bytes": res.bytes, "plan_id": plan.get("plan_id")}
        except Exception as exc:
            return {"ok": False, "status": status, "error": {"type": type(exc).__name__, "message": str(exc)}}

    def _adapt_plan_obj(self, plan_obj: Dict[str, Any], goal_fallback: str) -> Dict[str, Any]:
        if not isinstance(plan_obj, dict):
            return {"goal": goal_fallback, "steps": []}

        if "steps" in plan_obj and isinstance(plan_obj.get("steps"), list):
            if "goal" not in plan_obj or not isinstance(plan_obj.get("goal"), str):
                plan_obj["goal"] = goal_fallback
            return plan_obj

        tool_calls = plan_obj.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            steps: List[Dict[str, Any]] = []
            for i, tc in enumerate(tool_calls, start=1):
                if not isinstance(tc, dict):
                    continue
                name = tc.get("name")
                method = tc.get("method")
                args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                steps.append(
                    {
                        "id": f"s{i}",
                        "title": f"Tool: {name}.{method}",
                        "type": "tool",
                        "depends_on": [],
                        "tool": {"name": name, "method": method, "args": args},
                    }
                )
            return {"goal": goal_fallback, "steps": steps}

        return {"goal": goal_fallback, "steps": []}

    def handle_chat(self, message: str, session_id: str = "default", plan_id: Optional[str] = None) -> Dict[str, Any]:
        self.ensure_warmup_async()

        t_total0 = time.perf_counter()
        timing_ms: Dict[str, int] = {
            "total": 0,
            "memory_add": 0,
            "context_build": 0,
            "llm_plan": 0,
            "planner_tools": 0,
            "llm_final": 0,
        }

        tool_calls_count = 0
        tool_batches = 0

        out: Dict[str, Any] = {
            "ok": False,
            "session_id": session_id,
            "final": "",
            "tool_results": [],
            "plan": None,
            "error": None,
            "details": None,
            "timing_ms": timing_ms,
            "tool_calls_count": 0,
            "tool_batches": 0,
            "checkpoint": None,
        }

        plan: Optional[Dict[str, Any]] = None
        resumed = False

        try:
            if not isinstance(message, str) or not message.strip():
                out["error"] = "INVALID_MESSAGE"
                return out

            t0 = time.perf_counter()
            self.memory.add_turn("user", message, session_id=session_id)
            timing_ms["memory_add"] = int((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            ctx = self.context.build_context(message, session_id=session_id)
            timing_ms["context_build"] = int((time.perf_counter() - t0) * 1000)

            if not ctx.get("ok"):
                out["error"] = "CONTEXT_BUILD_FAILED"
                out["details"] = {"ctx": ctx}
                return out

            # RESUME: if plan_id provided and exists, load plan and continue without re-planning
            if isinstance(plan_id, str) and plan_id:
                try:
                    state = self.plan_store.load(plan_id)
                    loaded_plan = state.get("plan")
                    if isinstance(loaded_plan, dict):
                        plan = loaded_plan
                        plan["plan_id"] = plan_id
                        out["plan"] = plan
                        resumed = True
                        out["checkpoint"] = self._checkpoint(plan, session_id, "running")
                except Exception as exc:
                    out["error"] = "RESUME_FAILED"
                    out["details"] = {"type": type(exc).__name__, "message": str(exc), "plan_id": plan_id}
                    return out

            # If not resumed, do normal LLM planning + normalization
            llm_plan_text = ""
            if not resumed:
                system = (
                    "Output STRICT JSON ONLY. Allowed formats:\n"
                    "A) {\"goal\":str, \"steps\":[{\"id\":str(optional),\"title\":str,\"type\":\"tool\"|\"llm\"|\"note\",\"depends_on\":[str...],\"tool\":{name,method,args} (tool),\"prompt\":str (llm)}...]}\n"
                    "B) {\"tool_calls\":[{\"name\":str,\"method\":str,\"args\":object}...],\"final\":str}\n"
                    "No markdown. No extra text."
                )

                t0 = time.perf_counter()
                llm_plan = self.llm.chat(
                    [{"role": "system", "content": system}, {"role": "user", "content": ctx["context_text"]}],
                    temperature=0.2,
                    max_tokens=1800,
                )
                timing_ms["llm_plan"] = int((time.perf_counter() - t0) * 1000)

                if not llm_plan.ok:
                    out["error"] = llm_plan.error
                    out["details"] = llm_plan.details
                    return out

                llm_plan_text = llm_plan.text
                plan_obj_raw = self._parse_best_json(llm_plan.text)
                if plan_obj_raw is None:
                    final_text = llm_plan.text.strip()
                    self.context.finalize_task(message, final_text, session_id=session_id, status="ok")
                    out.update(ok=True, final=final_text)
                    return out

                plan_obj = self._adapt_plan_obj(plan_obj_raw, goal_fallback=message)

                norm = self.planner.normalize_plan(plan_obj, goal_fallback=message)
                if not norm.get("ok"):
                    debug_plan: Dict[str, Any] = {
                        "plan_id": f"{session_id}_{int(time.time()*1000)}",
                        "goal": message,
                        "raw_plan": plan_obj_raw,
                        "adapted_plan": plan_obj,
                        "normalize": norm,
                        "llm_plan_text_preview": llm_plan.text[:1200],
                    }
                    out["checkpoint"] = self._checkpoint(debug_plan, session_id, "failed_normalize")
                    out.update(ok=True, final=llm_plan.text.strip(), error="PLAN_NORMALIZE_FAILED", details=norm, plan=debug_plan)
                    return out

                plan = norm["plan"]
                out["plan"] = plan
                out["checkpoint"] = self._checkpoint(plan, session_id, "running")

            # Execute remaining tool batches from plan
            all_tool_results: List[Dict[str, Any]] = []
            t_tools0 = time.perf_counter()

            while True:
                batch = self.planner.get_ready_tool_batch(plan, batch_size=25) if isinstance(plan, dict) else {"ok": False}
                if not batch.get("ok"):
                    break
                calls = batch.get("tool_calls", [])
                if not calls:
                    break

                tool_batches += 1
                tool_calls_count += len(calls)

                router_calls: List[Dict[str, Any]] = []
                step_ids: List[str] = []
                for c in calls:
                    name = c.get("name")
                    method = c.get("method")
                    args = c.get("args") or {}
                    step_id = c.get("_step_id")
                    name2, method2, args2 = self._canonicalize_tool_call(name, method, args)
                    router_calls.append({"name": name2, "method": method2, "args": args2})
                    step_ids.append(step_id)

                results = self.tools.execute(router_calls)

                for i in range(min(len(results), len(step_ids))):
                    results[i]["_step_id"] = step_ids[i]

                all_tool_results.extend(results)
                if isinstance(plan, dict):
                    self.planner.apply_tool_results(plan, results)
                    out["checkpoint"] = self._checkpoint(plan, session_id, "running")

            timing_ms["planner_tools"] = int((time.perf_counter() - t_tools0) * 1000)
            out["tool_results"] = all_tool_results

            # Final answer synthesis
            system2 = "Return STRICT JSON ONLY: {\"final\": str}. No extra keys. No extra text."

            t0 = time.perf_counter()
            llm_final = self.llm.chat(
                [
                    {"role": "system", "content": system2},
                    {"role": "user", "content": ctx["context_text"]},
                    {"role": "user", "content": "PLAN_STATUS:\n" + json.dumps(self._plan_status(plan or {}), ensure_ascii=False)},
                    {"role": "user", "content": "TOOL_RESULTS:\n" + json.dumps(all_tool_results, ensure_ascii=False)},
                ],
                temperature=0.2,
                max_tokens=1800,
            )
            timing_ms["llm_final"] = int((time.perf_counter() - t0) * 1000)

            if llm_final.ok:
                obj2 = self._parse_best_json(llm_final.text) or {}
                final_text = str(obj2.get("final", llm_final.text)).strip()
            else:
                final_text = llm_final.text.strip()

            if not final_text:
                final_text = "(no output)"

            self.context.finalize_task(message, final_text, session_id=session_id, status="ok")
            out.update(ok=True, final=final_text)

            if isinstance(plan, dict):
                out["checkpoint"] = self._checkpoint(plan, session_id, "done")

            return out

        except Exception as exc:
            out["error"] = "MASTERAGENT_EXCEPTION"
            out["details"] = {"type": type(exc).__name__, "message": str(exc)}
            if isinstance(plan, dict):
                out["checkpoint"] = self._checkpoint(plan, session_id, "failed")
            return out

        finally:
            timing_ms["total"] = int((time.perf_counter() - t_total0) * 1000)
            out["tool_calls_count"] = tool_calls_count
            out["tool_batches"] = tool_batches

    def _canonicalize_tool_call(self, name: Any, method: Any, args: Any) -> Tuple[str, str, Dict[str, Any]]:
        n = str(name).strip() if isinstance(name, str) else ""
        m = str(method).strip() if isinstance(method, str) else ""
        a = args if isinstance(args, dict) else {}

        if n == "browser":
            if m in ("fetch", "get", "get_url", "download", "httpget"):
                m = "http_get"
        elif n == "terminal":
            if m in ("exec", "run", "cmd"):
                m = "run_cmd"
        elif n == "file":
            if m == "read":
                m = "read_text"
            elif m == "write":
                m = "write_text"
            elif m in ("ls", "dir"):
                m = "list_dir"
            elif m == "mkdir":
                m = "mkdirs"

        return n, m, a

    def _parse_best_json(self, text: str) -> Optional[Dict[str, Any]]:
        if not isinstance(text, str):
            return None
        s = text.strip()
        if not (s.startswith("{") and s.endswith("}")):
            m = re.search(r"\{.*\}", s, flags=re.DOTALL)
            if not m:
                return None
            s = m.group(0)
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    def _plan_status(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        steps = plan.get("steps", [])
        total = len(steps) if isinstance(steps, list) else 0
        done = failed = pending = 0
        for s in (steps or []):
            st = (s.get("status") if isinstance(s, dict) else None)
            if st == "done":
                done += 1
            elif st == "failed":
                failed += 1
            elif st == "pending":
                pending += 1
        return {"plan_id": plan.get("plan_id"), "goal": plan.get("goal"), "total": total, "done": done, "failed": failed, "pending": pending}
