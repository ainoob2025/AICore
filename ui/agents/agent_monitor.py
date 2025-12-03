'''Agent monitor with clear blocks and emojis'''

from typing import Dict, Any

class AgentMonitor:
    def __init__(self):
        self.agents = {
            'research': {'status': 'active', 'tasks': 3},
            'code': {'status': 'idle', 'tasks': 0},
            'debug': {'status': 'active', 'tasks': 2},
            'websearch': {'status': 'active', 'tasks': 1}
        }

    def display(self) -> Dict[str, Any]:
        """Return formatted agent monitor output."""
        return {
            'title': "🤖 Agent Monitor",
            'status': "Active",
            'agents_count': len(self.agents),
            'agent_status': self.agents
        }