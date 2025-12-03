from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

class ChatInterface:
    def __init__(self):
        self.app = FastAPI()
        
    @self.app.get("/chat")
    async def chat_home(self):
        return {"message": "Willkommen zur AI Core-Chat-UI!", "status": "ready"}
    
    @self.app.post("/chat")
    async def chat_message(self, request: Request):
        data = await request.json()
        return {"response": f"AI Core hat Ihre Nachricht verarbeitet: '{data.get('message', '')}'", "status": "processed"}