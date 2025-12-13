# AI Core Gateway – Operations Contract

## Network Contract (fixed)
- Host: 127.0.0.1
- Port: 10010
- Entry point: `gateway_init_.py` (project root)

## Endpoints
- `GET /health` (fast)
  - 200: `{"ok": true}`
  - 503: `{"ok": false, "error": "WARMUP_FAILED"}` (only if warmup is done AND failed)
  - Response header: `X-Request-Id: <uuid>`

- `GET /health/llm` (deep check)
  - Purpose: LM Studio reachability check (`/v1/models`, hard timeout)
  - 200: `{"ok": true}`
  - 503: `{"ok": false, "error": "LLM_UNREACHABLE", "details": {...}}`
  - Response header: `X-Request-Id: <uuid>`

- `GET /metrics`
  - 200: JSON metrics snapshot
  - Includes warmup fields: `warmup_started`, `warmup_done`, `warmup_ok`, `warmup_ms`, `warmup_error`
  - Includes chat metrics: `chat_p95_ms`, `chat_samples`
  - Includes security metrics: `rate_limited_total`
  - Includes stability metrics: `chat_inflight`, `max_chat_inflight`, `chat_busy_total`
  - Response header: `X-Request-Id: <uuid>`

- `POST /chat`
  - Request JSON: `{"session_id": "<string>", "message": "<string>", "plan_id": "<string optional>"}`
  - Behavior:
    - Without `plan_id`: normal run (LLM planning + execution)
    - With `plan_id`: resume run (load saved plan state and continue)
  - 200: agent response JSON (schema defined by MasterAgent)
  - 429: `{"ok": false, "error": "RATE_LIMITED", "retry_after_s": <int>}` + header `Retry-After: <seconds>`
  - 503: `{"ok": false, "error": "BUSY"}`
  - Response header: `X-Request-Id: <uuid>`

## Hard Limits (deterministic)
- Max request body: 256 KB
- Max `message`: 32,000 chars
- Validation errors:
  - 400: `INVALID_JSON`, `INVALID_SCHEMA`
  - 413: `PAYLOAD_TOO_LARGE`

## Security
- Rate limit (`/chat`): 30 requests per 60 seconds per remote IP
  - On limit: HTTP 429 + `Retry-After` header
- Rate-limit store: bounded + cleanup (prevents unbounded memory growth)

## Stability
- Concurrency guard (`/chat`): max 4 in-flight requests per process
  - On limit: HTTP 503 + `BUSY`
  - Metrics: `chat_inflight`, `max_chat_inflight`, `chat_busy_total`

## Observability
### Request Log (JSONL)
- File: `logs/gateway_requests.jsonl`
- One line per request (JSON object)
- Fields (minimum):
  - `ts` (UTC ISO8601)
  - `request_id` (UUID)
  - `remote`
  - `method`
  - `path`
  - `status`
  - `latency_ms`
  - `session_id` (only for `/chat`, if available)
  - `plan_id` (only for `/chat`, if provided)
  - `chat_total_ms` (only for `/chat`, if available)

### Log Rotation (daily + retention)
- Rotator script: `ops/rotate_gateway_logs.ps1`
- Output directory: `logs/requests/`
- Daily archive filename: `gateway_requests_YYYY-MM-DD.jsonl`
- Retention: 30 days (files older than 30 days removed)

### Scheduled Task
- Task name: `AICore_GatewayLogRotate`
- Runs as: `SYSTEM`
- Schedule: daily 00:05
- Command:
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\AI\AICore\ops\rotate_gateway_logs.ps1"`

## Service (Windows)
### Wrapper
- NSSM binary (project-local): `bin/nssm.exe`
- Service name: `AICoreGateway`

### Install/Control
- Installer: `ops/install_service.ps1`
  - `install`, `uninstall`, `start`, `stop`, `status`, `logs`

### Hardening
- Hardening: `ops/harden_service.ps1 apply`
- Account: `NT AUTHORITY\LocalService`
- Recovery:
  - Restart after 2s, 2s, 2s
  - Reset period: 60s
- ServicesPipeTimeout:
  - `HKLM:\SYSTEM\CurrentControlSet\Control\ServicesPipeTimeout = 30000`

## Local Run (non-service)
- Script: `run.ps1`
  - `start`, `stop`, `restart`, `status`, `health`, `logs`
