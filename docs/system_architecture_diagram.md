# AI Core – Architekturdiagramm (Phase 0–9)

                   ┌──────────────────────────────┐
                   │          Gateway (API)        │
                   │ FastAPI: /chat, /tool, /plan  │
                   └───────────────┬───────────────┘
                                   │
                              CoreRequest
                                   │
                   ┌───────────────▼───────────────┐
                   │         MasterAgent            │
                   │  - handle_request()            │
                   │  - Thinking / Planner / Tools  │
                   └───────┬──────────┬────────────┘
                           │          │
                           │          │
            ┌──────────────▼───┐   ┌──▼────────────────┐
            │   MemoryRouter   │   │     ToolRouter     │
            │ conversation/…   │   │ echo/upper/…       │
            └──────┬───────────┘   │ Browser/Terminal   │
                   │               │ File/Audio/RAG ... │
                   │               └──────────┬──────────┘
          ┌────────▼────────┐               Tool-Handlers
          │  Memory Core    │
          │ Conversation    │
          │ Episodic        │
          │ Semantic (RAG)  │
          └─────────────────┘

   ┌──────────────────────────────┐
   │          Planner             │
   │  Schrittpläne erzeugen       │
   │  planner_trace               │
   └──────────────────────────────┘

   ┌──────────────────────────────┐
   │      Phase 6 Layer           │
   │ TaskFeedbackLogger           │
   │ SelfImprovementAgent         │
   └──────────────────────────────┘

   ┌──────────────────────────────┐
   │       Phase 7 Tools          │
   │ Browser / Terminal / File    │
   │ Audio / Vision / Reasoning   │
   └──────────────────────────────┘

   ┌──────────────────────────────┐
   │       Phase 8 (Metrics)      │
   │ BenchmarkSuite + MetricsLog  │
   └──────────────────────────────┘

   ┌──────────────────────────────┐
   │   Phase 9 (PolicyOptimizer)  │
   │ RL-light: Reward → Strategy  │
   └──────────────────────────────┘


Dieses Diagramm soll vollständig den aktuellen Stand widerspiegeln.