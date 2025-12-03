from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

class MemoryViewer:
    def __init__(self):
        self.app = FastAPI()
        
    @self.app.get("/memory")
    async def memory_home(self):
        return {"message": "Aktuelle Erinnerungen und Episoden geladen.", "status": "ready", "memory_layers": ["conversation", "episodic", "semantic"]}
    
    @self.app.get("/memory/search")
    async def memory_search(self, request: Request):
        data = await request.json()
        return {"results": f"Suche nach '{data.get('query', '')}' in allen Erinnerungsschichten.", "status": "searching", "count": 5}