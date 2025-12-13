"""Kernel Gate for AI Core: verifies MasterAgent orchestration invariants.

Run:
  python ops/kernel_gate.py

Exit codes:
  0 = GREEN
  2 = RED (invariant violated)
"""

from __future__ import annotations

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def fail(msg: str) -> None:
    print("KERNEL_GATE: RED")
    print(msg)
    sys.exit(2)


def ok(msg: str) -> None:
    print("KERNEL_GATE: GREEN")
    print(msg)
    sys.exit(0)


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        fail(msg)


def main() -> None:
    # Canonicalization must be importable (single source of truth)
    try:
        from core.tools.tool_canonicalization import canonicalize  # type: ignore
    except Exception as e:
        fail(f"canonicalization import failed: {type(e).__name__}: {e}")
    assert_true(callable(canonicalize), "canonicalize is not callable")

    try:
        from core.kernel.master_agent import MasterAgent  # type: ignore
    except Exception as e:
        fail(f"import MasterAgent failed: {type(e).__name__}: {e}")

    try:
        agent = MasterAgent()
    except Exception as e:
        fail(f"MasterAgent() init failed: {type(e).__name__}: {e}")

    toolrouter = getattr(agent, "tools", None) or getattr(agent, "tool_router", None) or getattr(agent, "_tools", None)
    planner = getattr(agent, "planner", None) or getattr(agent, "_planner", None)
    memory = getattr(agent, "memory", None) or getattr(agent, "_memory", None)
    rag = getattr(agent, "rag", None) or getattr(agent, "_rag", None)

    assert_true(toolrouter is not None, "MasterAgent missing ToolRouter (expected attr tools/tool_router/_tools)")
    assert_true(planner is not None, "MasterAgent missing Planner (expected attr planner/_planner)")
    assert_true(memory is not None, "MasterAgent missing MemoryOS (expected attr memory/_memory)")
    assert_true(rag is not None, "MasterAgent missing RAGEngine (expected attr rag/_rag)")

    assert_true(hasattr(toolrouter, "available_tools"), "ToolRouter missing available_tools()")
    assert_true(hasattr(toolrouter, "execute"), "ToolRouter missing execute()")

    try:
        avail = toolrouter.available_tools()
    except Exception as e:
        fail(f"ToolRouter.available_tools() failed: {type(e).__name__}: {e}")

    assert_true(isinstance(avail, list) and all(isinstance(x, str) for x in avail), "available_tools() must return List[str]")
    assert_true("ping" in set(avail), "ToolRouter missing required baseline tool: ping")

    assert_true(hasattr(agent, "handle_chat"), "MasterAgent missing handle_chat()")

    try:
        res = agent.handle_chat("ping", session_id="kernel_gate", plan_id=None)
    except Exception as e:
        fail(f"handle_chat failed: {type(e).__name__}: {e}")

    assert_true(isinstance(res, dict), "handle_chat did not return dict")

    req_keys = ["ok", "session_id", "final", "tool_results", "plan", "error", "details", "timing_ms", "tool_calls_count", "tool_batches", "checkpoint"]
    for k in req_keys:
        assert_true(k in res, f"handle_chat missing key: {k}")

    assert_true(res.get("ok") is True, f"handle_chat ok!=true: {res.get('error')}")
    assert_true(isinstance(res.get("tool_results"), list), "tool_results must be a list (can be empty)")
    assert_true(isinstance(res.get("tool_calls_count"), int), "tool_calls_count must be int")
    assert_true(isinstance(res.get("tool_batches"), int), "tool_batches must be int")

    tc = int(res.get("tool_calls_count") or 0)
    tr = res.get("tool_results") or []
    if tc > 0:
        assert_true(len(tr) > 0, "tool_calls_count>0 but tool_results empty (pipeline mismatch)")

    cp = res.get("checkpoint")
    assert_true(isinstance(cp, dict), "checkpoint missing or not dict")
    assert_true(cp.get("ok") is True, "checkpoint ok!=true")
    assert_true(isinstance(cp.get("plan_id"), str) and cp.get("plan_id"), "checkpoint.plan_id missing")
    assert_true(isinstance(cp.get("path"), str) and cp.get("path"), "checkpoint.path missing")

    ok(f"plan_id={cp.get('plan_id')} tools={len(avail)} tool_calls_count={tc}")


if __name__ == "__main__":
    main()
