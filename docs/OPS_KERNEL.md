# AI Core Kernel – Operations Contract

## Scope
This document defines the operational contract for:
- `core/kernel/master_agent.py` (MasterAgent)
- `core/kernel/planner.py` (Planner)
- `core/tools/tool_router.py` (ToolRouter integration point)
- `core/kernel/plan_state_store.py` (PlanStateStore)

This is an operations document (facts only): what exists, what is returned, what is guaranteed.

## MasterAgent
### Location
- `core/kernel/master_agent.py`
- Called by Gateway: `MasterAgent.handle_chat(message, session_id, plan_id=None) -> dict`

### High-level Behavior
- Planner-driven execution (DAG-style plan)
- Tool execution exclusively via ToolRouter
- Produces final answer + tool results + plan summary
- Supports resume via `plan_id`

### Response Shape (minimum keys)
- `ok` (bool)
- `session_id` (string)
- `final` (string)
- `tool_results` (list)
- `plan` (object|null)
- `error` (string|null)
- `details` (object|null)
- `checkpoint` (object|null)

### Timing Telemetry
`handle_chat` returns `timing_ms` with deterministic stage names:
- `total`
- `memory_add`
- `context_build`
- `llm_plan`
- `planner_tools`
- `llm_final`

Also returned:
- `tool_calls_count` (int)
- `tool_batches` (int)

### Checkpointing
- MasterAgent writes plan checkpoints through PlanStateStore.
- `checkpoint` object includes (minimum):
  - `ok` (bool)
  - `status` (string: `running`, `done`, `failed`, `failed_normalize`)
  - `path` (string, absolute)
  - `bytes` (int)
  - `plan_id` (string)

### Resume
- If `plan_id` is provided and exists:
  - PlanStateStore loads `.runtime/plans/<plan_id>.json`
  - MasterAgent continues execution from that plan state
- If load fails:
  - `error = RESUME_FAILED`

## PlanStateStore
### Location
- `core/kernel/plan_state_store.py`

### Storage
- Directory: `.runtime/plans/`
- File: `<plan_id>.json`
- Atomic write: `.tmp` + `os.replace`

### Schema (v1)
Top-level keys:
- `schema_version`
- `plan_id`
- `goal`
- `created_utc`
- `updated_utc`
- `status`
- `cursors`
- `tool_results_ref`
- `plan` (full plan object)

## Planner
### Location
- `core/kernel/planner.py`

### Requirements (operational)
- Supports very large plans (3–10,000+ steps)
- Batching for tool execution (caller requests tool batches)
- Plan state must be serializable for resume/checkpoints

### Plan Execution Signals (minimum expectations)
- Plan normalization is deterministic
- Steps have a `status` (e.g., `pending`, `done`, `failed`)
- Planner exposes a “ready batch” concept for tool calls

## ToolRouter
### Contract
- All tool execution occurs through ToolRouter
- Tool calls are canonicalized before execution

### Tool Results
- Tool results are returned as objects and attached under `tool_results`
- Tool results may include internal `_step_id` correlation fields
