AI Core – Systemdokumentation (Stand: Ende Phase 3)

Diese Dokumentation beschreibt den aktuellen Stand des AI Core Systems nach Abschluss der Phasen 0–3.
Sie dient dazu, das System schnell zu verstehen, zu replizieren und stabil zu erweitern.

1. Ziel des Systems

AI Core ist ein lokales KI-Betriebssystem mit:

lokaler Autonomie (Agenten, Planner, Tools)

persistenter Speicherstruktur:

Conversation Memory

Episodic Memory

Semantic Memory

Multi-Model-Layer:

Main Model

Thinking Model

Vision Model

Tool-basierten Erweiterungen:

ToolRouter

ToolRegistry

LLM-basierte Tool-Auswahl

Tool-Statistiken

einheitlicher Kernel-API:

CoreRequest

CoreResponse

klaren System-Komponenten:

Gateway (HTTP)

Kernel (MasterAgent)

Memory

Tools

Planner

Agents (State, Factory, Runner)

Das System ist modular, erweiterbar und vollständig lokal lauffähig.

2. Ordnerstruktur (Stand nach Phase 3)
AICore/
│
├── core/
│   ├── kernel/
│   │   ├── master_agent.py
│   │   └── request_types.py
│   │
│   ├── memory/
│   │   ├── memory_core.py
│   │   ├── episodic_memory.py
│   │   ├── semantic_memory.py
│   │   └── memory_router.py
│   │
│   ├── tools/
│   │   ├── tool_router.py
│   │   ├── model_switcher.py
│   │   └── tool_catalog.json
│   │
│   ├── planner/
│   │   ├── planner.py
│   │   └── planner_agent_link.py
│   │
│   ├── agents/
│   │   ├── agent_state.py
│   │   ├── agent_factory.py
│   │   ├── agent_runner.py
│   │   └── templates/
│   │       ├── research_agent.json
│   │       ├── code_agent.json
│   │       ├── debug_agent.json
│   │       ├── memory_agent.json
│   │       └── workflow_agent.json
│   │
│   ├── cli.py
│   ├── test_smoke.py
│   ├── test_planner.py
│   ├── test_agent_flow.py
│   └── test_tool_autodetect.py
│
├── gateway/
│   └── gateway.py
│
├── data/
│   ├── conversation/
│   ├── episodic/
│   ├── semantic/
│   ├── agents/
│   ├── tools/
│   │   └── stats.json
│   └── logs/
│
├── models/
│   └── model_config.json
│
└── docs/
    ├── readme.md
    └── system_architecture_diagram.md

3. Komponentenübersicht
3.1 Kernel (core/kernel)
master_agent.py

Zentrale Steuerkomponente des Systems.

verarbeitet CoreRequest

erzeugt CoreResponse

Routing nach:

"chat"

"tool"

"tool_select"

"planner"

"planner_agent"

"agent_step"

"agent_run"

steuert:

MemoryRouter

ToolRouter

Planner

PlannerAgentLink

AgentFactory

AgentRunner

Logging unter data/logs/core.log

zusätzliche Gateway-Methoden:

get_recent_events(user_id, limit)

get_semantic_memory(user_id, limit)

request_types.py

Definiert die Standard-Kernel-API:

CoreRequest

CoreResponse

CoreError

input_type unterstützt:

chat

tool

tool_select

planner

planner_agent

agent_step

agent_run

3.2 Memory-System (core/memory)
memory_core.py

Conversation Memory (Kurzzeit)

speichert Chatverläufe unter data/conversation/

episodic_memory.py

Event-/Interaktionsspeicher

loggt:

Tool-Aufrufe

Fehler

Modellantworten

speichert pro User in data/episodic/

semantic_memory.py

Langzeitwissen (Fakten, Tags, Importance)

persistiert unter data/semantic/

memory_router.py

verbindet alle Memory-Komponenten

extrahiert Fakten

bewertet Importance

baut LLM-Kontext-Blöcke (System + Verlauf)

3.3 Tools (core/tools)
tool_router.py (Phase-3 erweitert)

Neue Features:

Tool-Registry
core/tools/tool_catalog.json
enthält:

name

description

input_schema

output_schema

cost / latency / reliability_score

tags

Tool-Statistiken
data/tools/stats.json
automatische Pflege:

success_count

failure_count

avg_latency

last_error

Einheitliche Tool-Ausführung
run_tool(name, args)

misst Latenz

schreibt Stats

liefert ein einheitliches Ergebnisformat

LLM-basierte Tool-Auswahl
select_tools(step_description, context)

Ranking über dein Main-Model

Failsafe-Fallback:

reliability hoch → besser

cost/latency niedrig → besser

Legacy
route_tool_call(...) bleibt als Wrapper.

model_switcher.py

Sorgt dafür, dass LM Studio das passende Modell lädt.

3.4 Planner (core/planner)
planner.py

nimmt Task-Beschreibung

erzeugt:

plan_id

task

3 Basis-Schritte:

Analyse

Bearbeitung

Prüfung

planner_agent_link.py

verbindet Planner mit AgentFactory:

erzeugt Plan

erzeugt passenden Sub-Agent basierend auf Template

3.5 Agents (core/agents)
agent_state.py

persistente Agenten

gespeichert unter data/agents/*.json

enthält:

agent_id

user_id

task

status

steps[]

meta (rolle, erlaubte tools, scope, evaluation)

agent_factory.py

erzeugt Agenten aus Templates:

research_agent

memory_agent

code_agent

debug_agent

workflow_agent

templates/*.json

Definieren:

allowed_tools

work_area

evaluationskriterien

memory_scope

agent_runner.py

Basis-Runner:

findet nächsten pending Schritt

setzt Status von pending → running → done

kein echter Tool-Einsatz (folgt in späteren Phasen)

3.6 Gateway (gateway/gateway.py)

FastAPI-Server, HTTP-Einstieg.

Endpoints:

GET /health

POST /chat

POST /tool

POST /thinker_assist

POST /planner

POST /agent/create

POST /agent/step

POST /agent/run

GET /episodes/{user_id}

GET /semantic/{user_id}
→ nutzt get_recent_events & get_semantic_memory

Alle Endpoints bauen CoreRequest und delegieren an den MasterAgent.

3.7 CLI & Tests (core/*.py)
cli.py

CLI-Interface:

python core/cli.py "Frage"

test_smoke.py

Prüft:

Chat

Basic Tools

Thinker Assist

Memory

test_planner.py

Prüft input_type="planner".

test_agent_flow.py

Prüft:

agent/create

agent/step

agent/run

test_tool_autodetect.py (neu in Phase 3)

Prüft:

run_tool("echo") & run_tool("uppercase")

LLM-Selektionsflow (Fallback aktiv)

4. Logs & Persistenz

Logs:

data/logs/core.log


Speicherverzeichnisse:

data/conversation/

data/episodic/

data/semantic/

data/agents/

data/tools/stats.json

5. Status nach Phase 3
Abgeschlossen:
Phase 0 – Fundament

Basisarchitektur, Projektstruktur, Loader, CLI.

Phase 1 – Kernel-Härtung

CoreRequest/CoreResponse/CoreError
SessionManager
Logging
Smoke-Test
Stabilisierung API-Fluss

Phase 2 – Planner + Agents

Planner
PlannerAgentLink
AgentFactory
AgentState
AgentRunner
AgentFlow-Test

Phase 3 – Tool-Autodetektion

✔ ToolRegistry
✔ ToolStats
✔ LLM-Tool-Ranking + Failsafe-Heuristik
✔ run_tool() unified
✔ input_type="tool_select"
✔ Test-Suite vollständig

Nächste Schritte (Ausblick)

Phase 4: RAG-Integration

Phase 5: Wissensgraph

Phase 6+: Selbstoptimierung / RL