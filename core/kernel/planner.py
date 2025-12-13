"""Kernel Planner (enterprise-grade): scalable plan model + validation + chunking.

This Planner does NOT try to "be smart" without an LLM.
Its job is to:
- Define a robust plan schema (steps, dependencies, checkpoints)
- Validate and normalize plans produced by an LLM or other generators
- Provide deterministic chunking/paging for very large plans (thousands of steps)
- Provide execution-ready tool_calls batches for ToolRouter

Schema (normalized):
Plan = {
  "ok": bool,
  "plan": {
    "plan_id": str,
    "goal": str,
    "created_ts": float,
    "status": "new|running|done|failed",
    "steps": [Step...],
    "checkpoints": [Checkpoint...],
  },
  "error": str|None,
  "details": dict|None,
}

Step = {
  "id": str,                  # unique
  "title": str,
  "type": "tool"|"llm"|"note",
  "depends_on": [str...],      # step ids
  "tool": {"name":str,"method":str,"args":dict}|None,
  "prompt": str|None,          # for llm steps
  "status": "pending|done|failed|skipped",
  "result": dict|None,
}

Checkpoint = {
  "at_step": str,
  "ts": float,
  "summary": str
}

This file is designed for "massive plans" (3..3000+ steps).
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple


MAX_STEPS_HARD = 10000
MAX_TITLE_LEN = 200
MAX_PROMPT_LEN = 8000


def _sha_id(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:16]


class Planner:
    def __init__(self) -> None:
        pass

    # -------------------------
    # Public API
    # -------------------------

    def new_plan(self, goal: str) -> Dict[str, Any]:
        if not isinstance(goal, str) or not goal.strip():
            return {"ok": False, "error": "INVALID_GOAL", "details": None}
        ts = time.time()
        pid = _sha_id(f"{goal.strip()}|{ts}")
        return {
            "ok": True,
            "plan": {
                "plan_id": pid,
                "goal": goal.strip(),
                "created_ts": ts,
                "status": "new",
                "steps": [],
                "checkpoints": [],
            },
            "error": None,
            "details": None,
        }

    def normalize_plan(self, plan_obj: Any, goal_fallback: str = "") -> Dict[str, Any]:
        """
        Takes arbitrary input (e.g., from LLM) and returns a normalized, validated plan structure.
        Supports two incoming formats:
        A) Full Plan dict with 'steps'
        B) Simple tool_calls dict: {'tool_calls':[...], 'final': '...'} -> becomes small plan
        """
        try:
            if isinstance(plan_obj, dict) and "steps" in plan_obj:
                return self._normalize_full_plan(plan_obj, goal_fallback)
            if isinstance(plan_obj, dict) and "tool_calls" in plan_obj:
                return self._normalize_toolcalls_plan(plan_obj, goal_fallback)
            return {"ok": False, "error": "UNSUPPORTED_PLAN_FORMAT", "details": {"type": type(plan_obj).__name__}}
        except Exception as exc:
            return {"ok": False, "error": "PLANNER_NORMALIZE_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}

    def get_ready_tool_batch(self, plan: Dict[str, Any], batch_size: int = 20) -> Dict[str, Any]:
        """
        Returns next batch of executable tool calls from pending steps whose deps are done.
        Output:
        { ok, tool_calls:[{name,method,args, _step_id}], remaining:int }
        """
        try:
            if not isinstance(plan, dict) or "steps" not in plan:
                return {"ok": False, "error": "INVALID_PLAN", "details": None}

            steps: List[Dict[str, Any]] = plan.get("steps", [])
            if not isinstance(steps, list):
                return {"ok": False, "error": "INVALID_STEPS", "details": None}
            if not isinstance(batch_size, int) or batch_size <= 0 or batch_size > 200:
                return {"ok": False, "error": "INVALID_BATCH_SIZE", "details": {"batch_size": batch_size}}

            done = {s.get("id") for s in steps if s.get("status") == "done"}
            pending_tool_steps = []
            for s in steps:
                if s.get("status") != "pending":
                    continue
                if s.get("type") != "tool":
                    continue
                deps = s.get("depends_on") or []
                if all(d in done for d in deps):
                    pending_tool_steps.append(s)

            tool_calls: List[Dict[str, Any]] = []
            for s in pending_tool_steps[:batch_size]:
                tool = s.get("tool") or {}
                tool_calls.append({
                    "name": tool.get("name"),
                    "method": tool.get("method"),
                    "args": tool.get("args") or {},
                    "_step_id": s.get("id"),
                })

            remaining = len(pending_tool_steps) - len(tool_calls)
            return {"ok": True, "tool_calls": tool_calls, "remaining": max(0, remaining)}
        except Exception as exc:
            return {"ok": False, "error": "PLANNER_BATCH_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}

    def apply_tool_results(self, plan: Dict[str, Any], tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Maps ToolRouter results back to steps (by _step_id if present) and marks steps done/failed.
        """
        try:
            if not isinstance(plan, dict) or "steps" not in plan:
                return {"ok": False, "error": "INVALID_PLAN", "details": None}
            if not isinstance(tool_results, list):
                return {"ok": False, "error": "INVALID_TOOL_RESULTS", "details": {"type": type(tool_results).__name__}}

            steps: List[Dict[str, Any]] = plan["steps"]
            idx = {s.get("id"): s for s in steps if isinstance(s, dict)}

            for r in tool_results:
                if not isinstance(r, dict):
                    continue
                # Router result may not carry _step_id; allow mapping by name/method only as fallback
                step_id = r.get("_step_id")
                target = idx.get(step_id) if isinstance(step_id, str) else None

                if target is None:
                    # fallback: first pending step with matching name/method
                    n = r.get("name")
                    m = r.get("method")
                    for s in steps:
                        if s.get("status") == "pending" and s.get("type") == "tool":
                            tool = s.get("tool") or {}
                            if tool.get("name") == n and tool.get("method") == m:
                                target = s
                                break

                if target is None:
                    continue

                ok = bool(r.get("ok"))
                target["result"] = r
                target["status"] = "done" if ok else "failed"

            return {"ok": True, "plan": plan, "error": None, "details": None}
        except Exception as exc:
            return {"ok": False, "error": "PLANNER_APPLY_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}

    def checkpoint(self, plan: Dict[str, Any], at_step: str, summary: str) -> Dict[str, Any]:
        try:
            if not isinstance(plan, dict) or "checkpoints" not in plan:
                return {"ok": False, "error": "INVALID_PLAN"}
            if not isinstance(at_step, str) or not at_step.strip():
                return {"ok": False, "error": "INVALID_STEP_ID"}
            if not isinstance(summary, str):
                return {"ok": False, "error": "INVALID_SUMMARY"}

            plan["checkpoints"].append({"at_step": at_step.strip(), "ts": time.time(), "summary": summary[:2000]})
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": "PLANNER_CHECKPOINT_EXCEPTION", "details": {"type": type(exc).__name__, "message": str(exc)}}

    # -------------------------
    # Normalization internals
    # -------------------------

    def _normalize_full_plan(self, obj: Dict[str, Any], goal_fallback: str) -> Dict[str, Any]:
        plan_id = str(obj.get("plan_id") or _sha_id(json.dumps(obj, ensure_ascii=False)[:2000]))
        goal = str(obj.get("goal") or goal_fallback or "task").strip()
        created_ts = float(obj.get("created_ts") or time.time())
        status = str(obj.get("status") or "new")

        steps_in = obj.get("steps", [])
        if not isinstance(steps_in, list):
            return {"ok": False, "error": "INVALID_STEPS"}

        if len(steps_in) > MAX_STEPS_HARD:
            return {"ok": False, "error": "TOO_MANY_STEPS", "details": {"max": MAX_STEPS_HARD, "got": len(steps_in)}}

        steps: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for i, s in enumerate(steps_in):
            if not isinstance(s, dict):
                continue
            sid = str(s.get("id") or _sha_id(f"{plan_id}|{i}|{s.get('title','')[:50]}"))
            if sid in seen:
                sid = _sha_id(sid + str(i))
            seen.add(sid)

            stype = str(s.get("type") or "note")
            if stype not in ("tool", "llm", "note"):
                stype = "note"

            title = str(s.get("title") or f"step-{i}").strip()[:MAX_TITLE_LEN]
            deps = s.get("depends_on") or []
            if not isinstance(deps, list):
                deps = []
            deps2 = [str(d) for d in deps if isinstance(d, (str, int, float))]

            tool = s.get("tool")
            tool_norm = None
            if stype == "tool":
                tool_norm = self._normalize_tool(tool)

            prompt = s.get("prompt")
            prompt_norm = None
            if stype == "llm":
                prompt_norm = str(prompt or "").strip()[:MAX_PROMPT_LEN]

            status_norm = str(s.get("status") or "pending")
            if status_norm not in ("pending", "done", "failed", "skipped"):
                status_norm = "pending"

            steps.append({
                "id": sid,
                "title": title,
                "type": stype,
                "depends_on": deps2,
                "tool": tool_norm,
                "prompt": prompt_norm,
                "status": status_norm,
                "result": s.get("result") if isinstance(s.get("result"), dict) else None,
            })

        plan = {
            "plan_id": plan_id,
            "goal": goal,
            "created_ts": created_ts,
            "status": status,
            "steps": steps,
            "checkpoints": obj.get("checkpoints") if isinstance(obj.get("checkpoints"), list) else [],
        }
        return {"ok": True, "plan": plan, "error": None, "details": None}

    def _normalize_toolcalls_plan(self, obj: Dict[str, Any], goal_fallback: str) -> Dict[str, Any]:
        goal = str(obj.get("goal") or goal_fallback or "task").strip()
        base = self.new_plan(goal)
        if not base.get("ok"):
            return base
        plan = base["plan"]

        tc = obj.get("tool_calls", [])
        if not isinstance(tc, list):
            tc = []

        steps: List[Dict[str, Any]] = []
        for i, c in enumerate(tc):
            tool = self._normalize_tool(c)
            steps.append({
                "id": _sha_id(f"{plan['plan_id']}|tool|{i}|{tool.get('name','')}|{tool.get('method','')}"),
                "title": f"tool:{tool.get('name')}:{tool.get('method')}",
                "type": "tool",
                "depends_on": [],
                "tool": tool,
                "prompt": None,
                "status": "pending",
                "result": None,
            })

        # final note step
        final_text = str(obj.get("final") or "").strip()
        steps.append({
            "id": _sha_id(f"{plan['plan_id']}|note|final"),
            "title": "final",
            "type": "note",
            "depends_on": [s["id"] for s in steps if s["type"] == "tool"],
            "tool": None,
            "prompt": None,
            "status": "pending" if steps else "done",
            "result": {"final": final_text} if final_text else None,
        })

        plan["steps"] = steps
        return {"ok": True, "plan": plan, "error": None, "details": None}

    def _normalize_tool(self, tool_obj: Any) -> Dict[str, Any]:
        if not isinstance(tool_obj, dict):
            tool_obj = {}
        name = tool_obj.get("name")
        method = tool_obj.get("method")
        args = tool_obj.get("args")

        name_s = str(name).strip() if isinstance(name, str) else ""
        method_s = str(method).strip() if isinstance(method, str) else ""
        args_d = args if isinstance(args, dict) else {}

        return {"name": name_s, "method": method_s, "args": args_d}


if __name__ == "__main__":
    p = Planner()
    base = p.new_plan("demo")
    print(base["ok"], base["plan"]["plan_id"])
    small = p.normalize_plan({"tool_calls": [{"name": "browser", "method": "http_get", "args": {"url": "https://example.com"}}], "final": "done"}, "demo")
    print(small["ok"], len(small["plan"]["steps"]))
    b = p.get_ready_tool_batch(small["plan"], batch_size=10)
    print(b)
