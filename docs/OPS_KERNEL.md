# AI Core Kernel – Operations

## Scope
Operational contract for:
- `core/kernel/master_agent.py` (MasterAgent)
- `core/kernel/planner.py` (Planner)
- Plan state store: `.runtime/plans/<plan_id>.json`

## MasterAgent
- Planner-driven orchestration (plan → batches → ToolRouter → final)
- Tool execution exclusively via ToolRouter
- Tool canonicalization is centralized:
  - `core/tools/tool_canonicalization.py`

### LLM Health
- MasterAgent exposes:
  - `health_llm() -> (ok: bool, details: dict)`
- Used by Gateway `/health/llm`
- `details` includes the actual checked URL and status info.

### Checkpointing / Resume
- Plan checkpoints stored at: `.runtime/plans/<plan_id>.json` (atomic write)
- `/chat` accepts optional `plan_id` to resume deterministically.

## Gateway Metrics (checkpoint persistence)
Gateway `/metrics` exports:
- `plans_saved_total`
- `last_plan_id`

## Gates (required)
- Kernel invariants gate: `ops/kernel_gate.py` (imports canonicalization + checks MasterAgent wiring)
- Full-system gate: `ops/gate.ps1`
