AI Core – Architekturdiagramm (Stand Phase 3)
Übersicht
                         ┌───────────────────────────┐
                         │          GATEWAY          │
                         │   FastAPI (Port 10010)    │
                         │ /chat /tool /planner ...  │
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │        MasterAgent        │
                         │  core/kernel/master_agent │
                         └─────────────┬─────────────┘
       ┌───────────────────────────────┼───────────────────────────────────────────┐
       ▼                               ▼                                           ▼
┌───────────────┐              ┌──────────────────┐                         ┌────────────────┐
│ MemoryRouter  │              │   ToolRouter      │                         │ SessionManager │
│ core/memory   │              │ core/tools        │                         │ core/kernel    │
└──────┬────────┘              └──────┬────────────┘                         └────────────────┘
       │                               │
       ▼                               ▼
┌──────────────┐               ┌─────────────────────────┐
│ MemoryCore   │               │   Tool Registry JSON     │
│ Episodic     │               │ core/tools/tool_catalog  │
│ Semantic     │               └─────────────┬───────────┘
└──────────────┘                             │
                                              ▼
                                      ┌──────────────────────┐
                                      │   Tool Statistics    │
                                      │ data/tools/stats.json│
                                      └─────────────┬────────┘
                                                    │
                                                    ▼
                                        ┌─────────────────────┐
                                        │   LM Studio Server  │
                                        │  Main/Think/Vision  │
                                        └─────────────────────┘


       ┌─────────────────────────────┬─────────────────────────────┐
       ▼                             ▼                             ▼
┌───────────────┐           ┌────────────────┐            ┌─────────────────┐
│   Planner     │           │ PlannerAgent   │            │  AgentFactory   │
│ core/planner  │           │ Link           │            │ core/agents     │
└──────┬────────┘           │ core/planner   │            └───────┬─────────┘
       │                    └──────┬─────────┘                    │
       │                           │                              │
       ▼                           ▼                              ▼
┌───────────────┐          ┌────────────────┐            ┌─────────────────────┐
│   Plans       │          │ Plan + Agent   │            │ AgentStateManager   │
│ (planner.py)  │          │ (combined)     │            │ + AgentRunner       │
└───────────────┘          └────────────────┘            └─────────────────────┘
                                                           │
                                                           ▼
                                                   ┌────────────────┐
                                                   │  Agent-JSON    │
                                                   │ data/agents    │
                                                   └────────────────┘

API-Endpunkte (funktional)

GET /health

POST /chat

POST /tool

POST /tool_select (optional via Kernel, nicht als separater Endpoint nötig)

POST /thinker_assist

POST /planner

POST /agent/create

POST /agent/step

POST /agent/run

GET /episodes/{user_id}

GET /semantic/{user_id}

Neue Flüsse seit Phase 3
Tool-Autodetektion (LLM + Failsafe-Heuristik)
Gateway → MasterAgent (input_type="tool_select")
         → ToolRouter.select_tools()
              → LLM-Ranking über Main Model
              → Fallback: reliability > cost > latency
         → Kandidatenliste zurück an Gateway / Kernel

Tool-Ausführung (vereinheitlicht)
Gateway /tool → MasterAgent → ToolRouter.run_tool(...)
    → Modellaufruf (Vision / Thinking / Main)
    → Timing / Fehlererfassung
    → Statistikspeicherung unter data/tools/stats.json

Bestehende Kernflüsse
Normaler Chat
/chat → MasterAgent (input_type="chat")
      → MemoryRouter
      → Build LLM context (10 Nachrichten)
      → Main Model
      → Antwort + Memory-Update

Planner
/planner → MasterAgent (input_type="planner")
         → Planner
         → Rückgabe plan_trace

Planner + Agent
/agent/create → MasterAgent (input_type="planner_agent")
               → PlannerAgentLink
                    → Planner
                    → AgentFactory (Template)
               → Plan + persistenter Agent

Agent Step
/agent/step → MasterAgent (input_type="agent_step")
            → AgentStateManager.add_step()

Agent Run
/agent/run → MasterAgent (input_type="agent_run")
           → AgentRunner.run_next_step()
           → Step: pending → running → done

Memory-Abfragen
Episodic
/episodes/{user_id}
→ get_recent_events()
→ episodic_memory

Semantic
/semantic/{user_id}
→ get_semantic_memory()
→ semantic_memory

Diagramm-Kommentar

Diese Darstellung zeigt den Zustand nach Abschluss von Phase 3:

ToolRegistry integriert

ToolStats integriert

LLM-Tool-Ranking + Failsafe-Heuristik

Unified Tool Execution

input_type="tool_select" im Kernel

neue Test-Suite (test_tool_autodetect)

Phase 4–6 bauen exakt auf dieser Architektur auf:

RAG-Anbindung

Wissensgraph

Selbstoptimierung / RL