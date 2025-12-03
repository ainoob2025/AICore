from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from core.kernel.master_agent import MasterAgent

app = FastAPI(title="AI Core Gateway", version="1.0")
agent = MasterAgent()  # ECHTER MasterAgent mit Planner, Tools, Memory

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.get("/")
async def root():
    return {"message": "AI Core Gateway läuft – Josie ist bereit"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = agent.handle_chat(req.message)
    return ChatResponse(response=result["response"])

if __name__ == "__main__":
    print("AI Core Gateway mit ECHTEM MasterAgent läuft auf Port 10010")
    uvicorn.run(app, host="127.0.0.1", port=10010)