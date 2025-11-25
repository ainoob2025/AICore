AI Core – Systemdokumentation (Phase 0–9)

AI Core ist ein vollständig lokales, containerfähiges KI-Betriebssystem bestehend aus:
- Kernel‐Agent (MasterAgent)
- Memory-Subsystem (Conversation, Episodic, Semantic, Cross-Memory Routing)
- Planner (Aufgabenzerlegung)
- Tool-System (ToolRouter + Tools)
- RAG-Engine
- Self-Improvement-Layer (Phase 6)
- Tool-Ökosystem (Phase 7)
- Benchmark- & Metrics-System (Phase 8)
- Policy-Optimizer (Phase 9, RL-light)

Alle Komponenten sind modular, sicherheitsfokussiert, minimal-invasiv und vollständig offline ausführbar.

---

## ✔ Architekturüberblick

Der Core besteht aus folgenden Hauptbereichen:

### **1. Kernel**
- `master_agent.py` – zentrale Steuerinstanz
- Routing für:
  - Chat
  - Tools
  - Planner
  - Planner-Agenten
  - Thinker-Assist
  - Self-Improve

### **2. Memory**
- Conversation Memory (chronologisch)
- Episodic Memory (LLM-optimierter Kontext)
- Semantic Memory (Vektorsuche / Wissensbasis)
- MemoryRouter (automatische Auswahl des Speichers)

### **3. Planner**
- Erstellung grober Schrittpläne
- Integration mit Agenten
- Planner-Trace in allen CoreResponses

### **4. Tools (Phase 1–5)**
- echo
- uppercase
- vision_analyze
- thinking_reason
- rag_query

### **5. Phase-6 Layer**
- TaskFeedbackLogger
- SelfImprovementAgent
- strategies.json
- Strategiebasierte Priorisierung im ToolRouter

### **6. Phase-7 Tool-Ökosystem**
- Browser-Tools (GET / Extract / Click)
- Terminal-Tool (sandboxed)
- File-Tools (read/write/list/summary)
- Audio-Tools (speech_to_text, text_to_speech)

### **7. Phase-8 Benchmarking**
- BenchmarkSuite
- MetricsLogger
- Standard-Benchmarks:
  - chat_simple
  - tool_uppercase
  - rag_query_simple
  - planner_simple
- Output nach: `data/metrics/*.jsonl`

### **8. Phase-9 Policy-Optimierung**
- Offline-PolicyOptimizer
- Reward-Berechnung auf Basis von:
  - Fehlern
  - Dauer
  - Tool-Nutzung
- Erzeugt versionslog:
  - `config/strategies_versions.jsonl`

---

## ✔ Code-Struktur

core/
kernel/
memory/
tools/
rag/
planner/
agents/
metrics/
benchmarks/
config/
data/
docs/
gateway/
models/

yaml
Code kopieren

---

## ✔ Laufzeit (CLI)

python core/cli.py "Frage"

yaml
Code kopieren

---

## ✔ Tests / Debug

- Phase 6: `python core/test_phase6_self_improvement.py`
- Phase 7: `python core/test_phase7_tools.py`
- Phase 8: `python core/test_phase8_benchmarks.py`
- Phase 9: `python core/test_phase9_policy.py`

---

## ✔ Metriken & Logs

- Task-Feedback: `data/logs/task_feedback.jsonl`
- Tool-Stats: `data/tools/stats.json`
- Benchmark-Runs: `data/metrics/<ID>.jsonl`
- Policy-Versionen: `config/strategies_versions.jsonl`

---

## ✔ Security & Isolation

- File-Tools strikt unter `data/files/`
- Terminal-Sandbox: `data/terminal_sandbox/`
- Audio-I/O: `data/audio/`, `data/audio_out/`
- Browser-Timeout + Byte-Limit
- Kein Tool kann Systeme außerhalb seines Roots berühren

---

Diese Datei vollständig ersetzen, keine alten Inhalte übernehmen.