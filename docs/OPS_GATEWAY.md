# AI Core Gateway – Operations

## Network Contract
- Host: `127.0.0.1`
- Port: `10010` (fixed, not configurable)
- Entry point: `gateway_init_.py` (project root)

## Endpoints

### `GET /health`
- `200` → `{"ok": true}`

### `GET /health/llm`
- Purpose: real LM Studio reachability check via MasterAgent
- `200` → `{"ok": true, "details": {...}}`
- `503` → `{"ok": false, "error": "LLM_UNREACHABLE", "details": {...}}`
- `details` includes (minimum):
  - `base_url`
  - `model_id`
  - `url` (actual checked endpoint)
  - `status_code`
  - `models_count` (best-effort)

### `GET /metrics`
- `200` → JSON metrics snapshot
- Includes (minimum):
  - `latency_ms_p50`, `latency_ms_p95`, `latency_ms_p99`, `latency_samples`
  - `chat_p95_ms`, `chat_samples`
  - `rate_limited_total`
  - `chat_inflight`, `max_chat_inflight`, `chat_busy_total`
  - `plans_saved_total`
  - `last_plan_id`

### `POST /chat`
- Request JSON:
  - `session_id` (string, required)
  - `message` (string, required)
  - `plan_id` (string, optional; enables deterministic resume)
- Responses:
  - `200` → `{"ok": true, ...}`
  - `429` → `{"ok": false, "error": "RATE_LIMITED"}` + `Retry-After`
  - `503` → `{"ok": false, "error": "BUSY"}`

## Security Controls
- Rate limit `/chat`: `30` requests / `60s` / IP
- Concurrency guard `/chat`: max `4` in-flight per process

## Logging
- JSONL request log: `logs/gateway_requests.jsonl`

## Gates (required)
- Full-system gate: `ops/gate.ps1`
- Kernel gate: `ops/kernel_gate.py`
