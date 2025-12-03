from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

class AgentMonitor:
    def __init__(self):
        self.app = FastAPI()
        
    @self.app.get("/agents")
    async def agents_home(self):
        return {"message": "Alle Agenten sind aktiv.", "status": "ready", "agent_count": 8, "active_agents": ["research", "code", "debug", "websearch"]}
    
    @self.app.get("/agents/status")
    async def agents_status(self, request: Request):
        data = await request.json()
        return {"response": f"Status für Agent '{data.get('name', '')}' ist '{data.get('status', 'active')}'.", "status": "monitoring"}