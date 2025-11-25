# AI Core – API Reference (Kernel Input Types & Tools)

Dieses Dokument listet alle Kernel-APIs (CoreRequest-input_types) und alle Tools auf.

---

## 🔷 Kernel Input Types (CoreRequest)

### **1. chat**
- `message: str`
- Antwort des Models + Memory-Update

### **2. tool**
- `tool_name: str`
- `tool_payload: dict`

### **3. tool_select**
- LLM-basierte Tool-Ranking-Abfrage

### **4. planner**
- `message: str`
- Liefert planner_trace

### **5. planner_agent**
- Multi-Step-Agent mit AgentStateManager

### **6. agent_step**
- Führt nächsten Step eines Agents aus

### **7. agent_run**
- Vollautomatischer next-step-Runner

### **8. self_improve**
- Startet SelfImprovementAgent

---

## 🔷 Tools (ToolRouter)

### **Text-Tools**
- `echo`
- `uppercase`

### **Reasoning-Tools**
- `thinking_reason`

### **Vision**
- `vision_analyze`

### **RAG**
- `rag_query`

### **Browser**
- `browser_get`
- `browser_extract`
- `browser_click`

### **Terminal (sandboxed)**
- `shell_run`

### **File-Tools**
- `file_read`
- `file_write`
- `file_list`
- `file_summary`

### **Audio-Tools**
- `speech_to_text`
- `text_to_speech`

---

## 🔷 Antworten (CoreResponse)

- `messages: [{role, content}]`
- `tool_calls: []`
- `memory_ops: []`
- `planner_trace: []`
- `agent_updates: {}`
- `errors: []`

---

## 🔷 Fehlerkategorien

- `planning_error`
- `tool_error`
- `memory_miss`
- `timeout`
- `hallucination_suspect`
- `unknown`
- `ok`

---