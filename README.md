# AICore

## 1. Zielbild

AI Core ist ein vollständig lokales, modular aufgebautes KI‑Betriebssystem. Es soll:

- als persönlicher Assistent, Companion und Arbeits‑OS dienen,
- Aufgaben von "einfacher Chat" bis zu komplexen Projekten eigenständig planen und ausführen,
- eine eigene Agenten‑"Belegschaft" steuern,
- Wissen aus einer lokalen, ständig aktualisierten Wissensschicht nutzen,
- ohne Cloud‑Abhängigkeiten funktionieren.

Das System läuft auf dem Host unter:

- Projektverzeichnis: `C:\AI\AICore`
- Lokale Modelle (über LM Studio)
- Alle Daten und Konfigurationen liegen im Projektverzeichnis.

---

## 2. Grundprinzipien

1. **Vollständig lokal**
   Alle KI‑Funktionen laufen auf der eigenen Hardware. Externe Dienste werden nur genutzt, wenn ausdrücklich konfiguriert.

2. **Host‑basiert, keine Containerpflicht**
   AI Core läuft als normale Prozesse auf dem Host. Container‑ oder Docker‑Lösungen sind nicht Teil dieses Masterplans.

3. **Modularer Aufbau**
   Jeder Bereich (Kernel, Memory, Tools, Agents, RAG, Graph, Plugins, UI) ist als eigenständiges Modul ausgelegt, das austauschbar und erweiterbar ist.

4. **Zentrale Memory‑Schicht**
   Alle Erfahrungen, Dokumente, Fakten, Agenten‑Runs und Tools werden in einer gemeinsamen Memory‑Schicht verwaltet (EverMemOS‑Prinzip).

5. **Autonomer Planner & Master‑Agent**
   Ein zentraler Master‑Agent orchestriert alles: er zerlegt Aufgaben, wählt Tools, erzeugt Sub‑Agenten, nutzt Memory und bewertet Ergebnisse.

6. **Klare Schnittstellen & Ports**
   Kommunikation zwischen Modulen erfolgt über klar definierte APIs und Ports. Die Port‑Ranges sind festgelegt und werden für Tools und Services einheitlich genutzt.

7. **Selbstverbesserung**
   Das System wertet eigene Läufe aus, lernt aus Fehlern und passt Strategien, Tool‑Prioritäten und Planungsparameter an.

8. **Erweiterbares Ökosystem**
   Neue Tools, Agenten und Workflows können als Plugins installiert werden. AI Core verwaltet ein lokales Plugin‑Ökosystem.

9. **Keine "optionalen" Features**
   Alle im Masterplan beschriebenen Funktionen gelten als TODO und werden gebaut und integriert. Es gibt keine unverbindlichen Erweiterungen.

---

## 3. Architektur – Überblick

AI Core besteht aus mehreren Kernkomponenten, die zusammen wie ein Betriebssystem für KI‑Agenten funktionieren.

### 3.1 Gateway

- Stellt eine API für UIs und externe Clients bereit (z. B. Chat‑UI).
- Nimmt Anfragen entgegen (Chat, Tools, Planner, Agents, Workflows).
- Reicht sie intern an den Kernel/Master‑Agent weiter.
- Ist das einzige "öffentliche" Eingangstor in das System.

### 3.2 Kernel / Master‑Agent

- Zentrale Orchestrierungseinheit.
- Aufgaben:
  - Parsen von Requests,
  - Laden des Sitzungskontexts,
  - Auswählen und Aufrufen von Planner, Agents, Tools, Memory, RAG und Graph,
  - Zusammenführen aller Ergebnisse zu einer Antwort.
- Arbeitet eng mit:
  - Planner,
  - Agent‑System,
  - Tool‑Router,
  - Memory‑Router,
  - RAG‑Engine,
  - Graph‑Engine,
  - Self‑Improvement‑Layer.

### 3.3 Memory‑OS

Memory ist in Schichten organisiert:

- **Conversation Memory** – aktueller Dialogkorridor.
- **Episodic Memory** – Ereignisse, Tasks, Tool‑Runs, Fehlersituationen.
- **Semantic Memory** – strukturiertes Wissen (Fakten, Dokumente, Notizen).
- **RAG Layer** – Vektor‑basierte Suche über Dokumente und Inhalte.
- **Graph Memory** – Wissensgraph aus Entities, Relationen, Ereignissen.
- **Autobiographical Memory** – was das System über sich selbst lernt (Strategien, Policies, Performance).
- **Cross‑Memory Search** – ein Layer, der alle oben genannten Quellen in einer Suche zusammenführt.

Das Memory‑OS dient allen Agenten und Tools als zentrale Wissensquelle.

### 3.4 RAG‑Engine

- Verantwortlich für:
  - Embeddings,
  - Vektor‑Index,
  - Chunking von Dokumenten,
  - Ingest (Aufnahme neuer Inhalte),
  - Query (Abfragen).
- Bindet sich an das Memory‑OS an, damit Ergebnisse in Semantic/Graph/Autobiographical Memory landen können.

### 3.5 Graph‑Engine

- Verwaltet einen Wissensgraph:
  - Knoten (Entitäten, Konzepte, Ereignisse),
  - Kanten (Beziehungen).
- Unterstützt:
  - Faktenspeicherung,
  - Beziehungsabfragen,
  - Konsistenzprüfungen.

### 3.6 Tool‑System

- Zentraler Tool‑Router, der Tools auswählt und aufruft.
- Tools umfassen u. a.:
  - Text‑Tools,
  - File‑Tools (lesen, schreiben, listen, zusammenfassen),
  - Browser‑Tools,
  - Terminal‑Tools (in sicherem Modus),
  - Audio‑Tools (STT/TTS),
  - Video‑Tools,
  - RAG‑Tools,
  - Vision‑Tools,
  - Thinking‑Tools (z. B. spezielles Reasoning‑Modell).
- Alle Tools haben eine einheitliche Beschreibung (Name, Input‑/Output‑Schema, Kosten, Latenz, Erfolgsraten).

### 3.7 Planner

- Zerlegt Aufgaben in Pläne mit klaren Schritten.
- Bestimmt:
  - welche Sub‑Agenten notwendig sind,
  - welche Tools in welcher Reihenfolge aufgerufen werden,
  - wann Memory/RAG/Graph genutzt werden.
- Bewertet Zwischenergebnisse und entscheidet über nächste Schritte (weiter, wiederholen, abbrechen).

### 3.8 Agent‑System

- AgentFactory erzeugt spezialisierte Agenten, z. B.:
  - Research‑Agent,
  - Code‑Agent,
  - Debug‑Agent,
  - Websearch‑Agent,
  - Memory‑Agent,
  - Workflow‑Agent.
- AgentRuntime führt die Agenten aus:
  - nutzt deren Tools,
  - greift auf Memory zu,
  - schreibt Logs und Episoden.
- AgentComm ermöglicht Multi‑Agent‑Kommunikation und Delegation.

### 3.9 Self‑Improvement & Policies

- Sammeln von Feedback, Logs und Kennzahlen pro Task.
- Self‑Improvement‑Agent analysiert diese Daten und schlägt neue Strategien vor.
- Policy‑Ebene ("RL‑Light") passt z. B. an:
  - Tool‑Prioritäten,
  - Planner‑Grenzen,
  - Retry‑Logik.

### 3.10 Plugin‑System & Ecosystem

- Plugins können neue:
  - Tools,
  - Agenten,
  - Workflows
  liefern.
- Plugins werden in einer klaren Struktur abgelegt (z. B. `plugins/tools`, `plugins/agents`, `plugins/workflows`).
- Ein Plugin‑Installer verwaltet:
  - Installation,
  - Auflistung,
  - Entfernung.
- Plugins verwenden definierte Runtimes (siehe Abschnitt 5).

### 3.11 UI & Developer Experience

- Lokales UI (z. B. Web‑UI) für:
  - Chat,
  - Tool‑Ausgaben,
  - Memory‑Viewer,
  - Agent‑Monitor,
  - Planner‑Inspector,
  - RAG‑Explorer,
  - Benchmark‑Dashboard,
  - Policy‑History.
- Developer‑Konsole zur direkten Interaktion mit Core‑APIs (z. B. Tests, Debugging).

### 3.12 OS‑Layer

- Personas (z. B. Companion, Personal Assistant, CTO, DevOps).
- Goal‑Interface: der Nutzer gibt ein Ziel an, das System plant und führt aus.

---

## 4. Phasenplan (Übersicht)

Der Aufbau von AI Core erfolgt in Phasen. Jede Phase hat klare Ziele und baut auf den vorherigen auf. Alle Phasen sind Teil dieses Masterplans.

### Phase 0 – Fundament & Konfiguration

- Projektstruktur und Ports festlegen.
- Basis‑Konfiguration:
  - Einstellungen (Ports, Pfade, Limits),
  - Modelle (Main, Thinking, Vision, Embeddings),
  - Tools, RAG, Agents, Strategien.
- Supervisor‑/Worker‑Regeln und Referenzdateien einführen.

### Phase 1 – Kernel & Gateway

- Interne Request/Response‑Typen definieren.
- Master‑Agent als zentrale Orchestrierung implementieren.
- Gateway mit HTTP‑API (z. B. `/chat`, `/tool`, `/planner`, `/agent`).
- Logging und Tracing aufsetzen.

### Phase 2 – Planner & Agentensystem

- Planner‑Modul implementieren (Tasks → Steps → Tools/Agents).
- AgentFactory & AgentRuntime aufbauen.
- Sub‑Agenten für typische Aufgaben definieren (Research, Code, Debug, Websearch, Memory, Workflow).
- Pläne und Agenten‑Läufe persistieren.

### Phase 3 – Tool‑System & Hooks

- Tool‑Router, Tool‑Registry, Tool‑Statistiken.
- Basic‑Tools (Echo, Uppercase, File, Browser, Terminal, Vision, Thinking, RAG).
- Hook‑System (z. B. `audio.input`, `audio.output`, `text.preprocess`, `tool.pre_call`, `tool.post_call`).

### Phase 4 – RAG‑Integration

- RAG‑Engine (Embeddings, Index, Chunking, Query).
- RAG‑Tools (`rag_ingest`, `rag_query`, `rag_stats`, `rag_export`).
- Einheitliches Schema für Wissenseinträge.
- Integration mit Semantic Memory.

### Phase 5 – Wissensgraph & Cross‑Memory

- Graph‑Engine implementieren.
- Cross‑Memory‑Search über:
  - Episodic,
  - Semantic,
  - RAG,
  - Graph,
  - Autobiographical.
- Integration in Planner und Master‑Agent.

### Phase 6 – Selbstoptimierung

- Feedback‑Logging pro Task.
- Self‑Improvement‑Agent für Analyse und Strategievorschläge.
- Strategien‑Konfiguration (Tool‑Prioritäten, Limits, Retries) versionieren.

### Phase 7 – Ökosystem‑Tools

- Browser‑Tools (GET, Extract).
- Terminal‑Tools (Shell‑Befehle mit Whitelists und Limits).
- File‑Tools (lesen, schreiben, listen, zusammenfassen).
- Audio‑Tools (Speech‑to‑Text, Text‑to‑Speech).
- Video‑Tools (Analyse, Transkription).
- Sicherheits‑ und Freigabe‑Mechanismen.

### Phase 8 – Evaluation & Benchmarks

- Benchmark‑Suite für:
  - Chat,
  - Tools,
  - RAG,
  - Planner,
  - Agents,
  - Memory.
- Metriken & Failure‑Kategorien.
- Grundlegende Stabilitäts‑ und Performance‑Checks.

### Phase 9 – Policy & RL‑Light

- Reward‑Schema (Erfolg, Zeit, Kosten, Feedback).
- Policy‑Layer, der Strategien aus Logs ableitet.
- Experiment‑Framework für A/B‑Tests.
- Policy‑Versionierung und Rollback.

### Phase 10 – Foundation‑Upgrade

- Vereinheitlichte Tests (z. B. pytest‑Suite).
- Konsolidiertes Config‑System.
- Build‑Skripte für Host‑Deployment.
- Verbesserte Port‑ und Service‑Organisation.

### Phase 11 – UI & Developer Experience

- Vollständige lokale UI (Chat, Memory‑Explorer, Tool‑Viewer, etc.).
- Developer‑Konsole (interaktive Aufrufe in das System).
- Debugging‑Layer (Traces für Requests, Memory, Tools, RAG, Self‑Improve).

### Phase 12 – Autonomous System Layer

- Multi‑Agent‑Kommunikation (Delegation, Synchronisation).
- Workflow‑System (JSON‑Workflows für typische Aufgaben).
- Long‑Running‑Tasks (Queue, Monitor, History).

### Phase 13 – Full RAG Suite

- RAG‑Engine als eigenständige Komponente.
- RAG‑Explorer im UI.
- RAG‑Benchmarks.

### Phase 14 – Ecosystem‑Layer (Plugins & Marketplace)

- Plugin‑System für Tools, Agents, Workflows.
- Plugin‑Sandbox mit Limits und Debug‑Traces.
- Plugin‑Installer und lokale Plugin‑Verwaltung.

### Phase 15 – Enterprise‑Layer

- Monitoring‑Dashboard.
- Metrics‑Server.
- Snapshot‑System (Backups).
- Disaster‑Recovery‑Mechanismen.

---

## 5. Runtimes & Plugins (Grundsatz)

- Es gibt eine definierte Menge von Runtimes (z. B. für Kernsystem und ML‑schwere Plugins).
- Plugins dürfen nur eine dieser Runtimes nutzen oder laufen als externe Services.
- Ziel:
  - wenige gemeinsame Runtimes,
  - keine unkontrollierte Vervielfachung von Python‑Installationen,
  - klar dokumentierte Abhängigkeiten pro Plugin.

Die exakte Liste der Runtimes und deren Einsatz wird in einer separaten Konfigurationsdatei definiert und ist Teil der späteren Implementierung.

---

Dieses Dokument ist der lesbare Masterplan für AI Core. Die technischen Details sind in eigenen Dokumenten definiert.
