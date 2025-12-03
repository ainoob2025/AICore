from core.memory.memory_os import MemoryOS
from core.rag.rag_engine import RAGEngine
from core.graph.graph_engine import GraphEngine
from core.planner.planner import Planner
from core.tools.tool_router import ToolRouter

class MasterAgent:
    def __init__(self):
        self.memory = MemoryOS()
        self.rag = RAGEngine()
        self.graph = GraphEngine()
        self.planner = Planner()
        self.tools = ToolRouter()
    def handle_chat(self, message):
        history = self.memory.get_conversation()
        plan = self.planner.decompose(f'{history}\\nUser: {message}')
        tools_used = self.tools.execute(getattr(plan, 'tools', [])) if hasattr(plan, 'tools') else []
        response = f'Josie antwortet auf: {message} (Tools: {tools_used})'
        self.graph.add_conversation(message, response, tools_used)
        return {'response': response, 'tools_used': tools_used}