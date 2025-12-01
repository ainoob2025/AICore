# AI Core – System Masterplan (Supervisor Version)

This document defines the canonical architecture and implementation plan
for the AI Core system. It is written for machine supervisors and must
be sufficient for any fresh supervisor instance without prior context.

All information in this document is normative. There is no concept of
"optional" features. Every feature listed here is part of the system and
must be implemented and integrated.

---

## 1. System goals

AI Core is a fully local, host-based AI operating system with the
following properties:

- runs on a single host under `C:\AI\AICore`
- uses local models via a model server
- provides a central MasterAgent for orchestration
- has a unified Memory OS (conversation, episodic, semantic, RAG, graph)
- has a Planner for task decomposition
- has an Agent system for specialized sub-agents
- has a Tool system with a ToolRouter and statistics
- has a RAG engine and knowledge graph
- has a self-improvement and evaluation layer
- has a plugin and marketplace system for tools/agents/workflows
- exposes a local API and later a local UI

The system is designed as a long-term, extensible foundation.

---

## 2. Deployment and environment

### 2.1 Host-only deployment

- AI Core runs as a set of **host processes** under Windows.
- The canonical project root is:
  - `C:\AI\AICore`
- All services (gateway, kernel, rag-engine, metrics, etc.) run directly
  on the host as Python processes or other executables.
- Containerization (Docker or similar) is not part of this specification.

### 2.2 Ports and services

Port ranges:

- UI / Frontend: `8000–8990`
- Agentic tools (external agent services): `9000–9990`
- Core / kernel services: `10000–10990`
- Audio services: `11000–11990`
- Video services: `12000–12990`

Rules:

- Ports are assigned only in steps of 10 (last digit is always 0).
- Each category uses its own range.

Core service assignments:

- Gateway API: 10010
- Kernel internal API (optional, if separate): 10020
- RAG engine: 10040
- Benchmark runner: 10050
- Policy engine: 10060
- Metrics server: 10080

---

## 3. Directory layout (top level)

The project root `C:\AI\AICore` has the following top-level structure:

- `core/`
  - `kernel/`
  - `planner/`
  - `agents/`
  - `tools/`
  - `hooks/`
  - `memory/`
  - `rag/`
  - `graph/`
  - `workflows/`
  - `self_improve/`
  - `policies/`
  - `metrics/`
  - `plugins_core/`
  - `os_layer/`
  - `rl/`
- `gateway/`
- `ui/`
- `plugins/`
  - `tools/`
  - `agents/`
  - `workflows/`
  - `marketplace/`
- `config/`
- `data/`
- `models/`
- `scripts/`
- `docs/`
- `reference/`
- `pyproject.toml`
- `README.md`

All supervisor steps must respect this structure and extend it, not
replace it.

---

## 4. Core components

### 4.1 Gateway

Directory:

- `gateway/`

Responsibilities:

- provide a local HTTP API for chat and tools
- accept model-compatible requests
- translate external requests into internal structures
- send responses as HTTP responses

The gateway is the only external entry point into the system.

### 4.2 Kernel and MasterAgent

Directory:

- `core/kernel/`

Responsibilities:

- define internal request/response/error types
- manage sessions and context
- orchestrate Planner, Agents, Tools, Memory, RAG, Graph
- route requests to:
  - chat handling
  - tool usage
  - planner and agents
  - workflows
  - self-improvement and policy evaluation

The MasterAgent is the central decision-maker of the system.

### 4.3 Memory OS

Directory:

- `core/memory/`

Conceptual layers:

- conversation memory
- episodic memory
- semantic memory
- autobiographical memory
- RAG-linked memory
- graph-linked memory
- cross-memory search

Responsibilities:

- store and retrieve task-related information
- perform cross-memory search across all layers
- maintain consistency and summaries
- decide what is important enough to keep long term

### 4.4 Planner

Directory:

- `core/planner/`

Responsibilities:

- decompose goals into plans and steps
- define step types (tool call, agent call, reasoning, workflow)
- evaluate step results and determine next actions
- integrate with Agents, Tools, RAG, Memory and Graph

### 4.5 Agents

Directory:

- `core/agents/`

Responsibilities:

- define agent state and lifecycle
- create specialized agents (research, code, debug, websearch, memory, workflow, etc.)
- manage communication between agents
- execute agent steps based on plans and tools

### 4.6 Tools and ToolRouter

Directory:

- `core/tools/`

Responsibilities:

- define a unified tool interface
- register and manage tools (text, file, browser, terminal, audio, video, rag, vision, thinking, etc.)
- route tool calls based on plan steps and context
- track tool statistics and failures

### 4.7 RAG engine

Directory:

- `core/rag/`

Responsibilities:

- ingest documents into vector storage
- perform semantic retrieval
- maintain a consistent knowledge index
- integrate with Memory OS and Graph

### 4.8 Graph engine

Directory:

- `core/graph/`

Responsibilities:

- store entities, concepts, events and relations
- support queries over structured knowledge
- integrate with Memory and Planner

### 4.9 Self-improvement and policies

Directories:

- `core/self_improve/`
- `core/policies/`

Responsibilities:

- log task performance and feedback
- analyze logs and propose new strategies
- maintain a policy layer that adjusts planner and tool parameters
- apply RL-light methods over logged data when appropriate

### 4.10 Plugins and ecosystem

Directories:

- `core/plugins_core/`
- `plugins/`

Responsibilities:

- load and register tools/agents/workflows from plugins
- isolate plugin working directories
- manage plugin installation, listing and removal
- support a local marketplace index

### 4.11 UI and OS layer

Directories:

- `ui/`
- `core/os_layer/`

Responsibilities:

- provide a local user interface (later phase)
- manage personas, roles and goal-based interfaces
- expose high-level goal-only interaction

---

## 5. Models and language policy

### 5.1 Model configuration

All models are defined in configuration files under `config/`, for
example:

- main model (chat)
- thinking model (deep reasoning)
- vision model (image/multimodal)
- embedding model (retrieval)

Models are accessed through a local model server via HTTP endpoints.

### 5.2 Language rules

- Internal processing, prompts and system messages: English.
- Default user language: German.
- User-facing answers from the main model must be in German, unless
  explicitly overridden.
- Tool and system prompts must remain in English.

---

## 6. Runtimes and plugins

### 6.1 Runtimes

AI Core uses a small number of shared runtimes, for example:

- `core_runtime` – main runtime for kernel, gateway, tools, memory, rag, agents, planner
- `plugin_runtime` – shared runtime for most Python-based plugins

Rules:

- Plugins must use one of the defined runtimes.
- Plugins must not bring their own separate Python installations.
- Exceptions (very large or incompatible tools) must be implemented as
  `external_service` plugins running on their own port.
- All runtimes are host-based and live inside the project structure
  (for example under `.runtimes/`).

### 6.2 Plugin types

The system supports multiple plugin types:

- `config_plugin` – configuration, prompts, workflows, no code
- `python_plugin` – runs inside a shared runtime
- `external_service` – runs as a separate process on a dedicated port
- `shell_plugin` – executed via a shell command interface

Each plugin provides a manifest (for example `plugin.yaml`) with:

- id and name
- type
- runtime (if applicable)
- entry points
- declared dependencies
- required ports (if external_service)

---

## 7. Phases and steps (high-level plan)

The implementation is organized into phases. Each phase consists of one
or more steps identified as `PHASE X / STEP Y.Z`. All features listed in
these phases are mandatory and will be built and integrated.

### Phase 0 – Foundation

- define project structure and ports
- create core configuration files (settings, models, tools, rag, agents, strategies, services)
- create supervisor workflow and the reference schema (worker behaviour is fully defined via worker prompts)

### Phase 1 – Kernel and gateway

- define internal request/response types
- implement MasterAgent skeleton and routing
- implement gateway service and schemas

### Phase 2 – Planner and agent system

- implement planner module with plan objects and evaluation
- implement agent state, factory and runtime
- integrate planner and agents with MasterAgent

### Phase 3 – Tools and ToolRouter

- define tool catalog and tool types
- implement ToolRouter and basic tools (echo, text, file, browser, terminal)
- track tool statistics and failures

### Phase 4 – RAG integration

- implement RAG engine (embedding, index, ingest, query)
- define knowledge item schema
- integrate RAG as tools and with Memory OS

### Phase 5 – Knowledge graph and cross-memory search

- implement graph engine and fact storage
- implement cross-memory search across all memory layers and RAG/graph
- integrate cross-memory into planner decisions

### Phase 6 – Self-improvement

- implement feedback logging per task
- implement self-improvement agent
- define strategies configuration and apply it to planner and tools

### Phase 7 – Ecosystem tools (browser, terminal, file, audio, video)

- implement browser tools
- implement terminal tools with safety limits
- implement file tools
- implement audio and video tools where applicable

### Phase 8 – Evaluation, benchmarks and stabilization

- implement benchmark suite for chat, tools, planner, memory, rag
- implement metrics collection and failure categories
- store metrics in structured format

### Phase 9 – Policy optimization (RL-light)

- define reward schema over task performance
- implement policy optimization layer
- apply updated policies to planner and tools

### Phase 10 – Foundation upgrade

- unify test suite and coverage reporting
- consolidate configuration system
- refine service discovery and port management

### Phase 11 – UI and developer experience

- implement local UI (chat, memory viewer, tool output, agent monitor, planner inspector, rag manager, benchmark dashboard, policy history)
- implement developer console and debugging layer

### Phase 12 – Autonomous system layer

- implement multi-agent communication
- implement workflow system (JSON workflows)
- implement auto-tools (tool generation and validation)
- implement long-running task support

### Phase 13 – Full RAG suite

- refine RAG engine into a full suite
- integrate RAG tools and UI modules
- implement RAG benchmarks

### Phase 14 – Ecosystem and plugin marketplace

- implement plugin system for tools/agents/workflows
- implement plugin sandboxing and isolation
- implement plugin installer and CLI
- implement plugin integrity checks

### Phase 15 – Enterprise and production features

- implement monitoring dashboard and metrics server
- implement snapshot and disaster recovery system
- implement memory consistency checks

---

## 8. Reference and execution state

The file `docs/aicore_reference.json` is a machine-readable index
of the AI Core project. It contains:

- project root
- modules
- tools
- agents
- workflows
- config entries
- execution state (last completed step, next step)

Every supervisor step must:

- update the relevant entries in `docs/aicore_reference.json`
  through a `REFERENCE_UPDATE` snippet
- ensure that `execution_state` always reflects the true progress

This masterplan, together with the supervisor workflow specification and
the reference file, is sufficient for any supervisor instance to plan
and execute implementation steps without additional context.