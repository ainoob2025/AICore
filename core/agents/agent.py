from typing import Dict, Any

class Agent:
    def __init__(self, name: str):
        self.name = name
        self.capabilities = []

    def execute(self, task: str) -> str:
        """Execute a task"""
        print(f"[Agent:{self.name}] Executing task: {task}")
        return f"Task completed by {self.name}: {task}"

    def add_capability(self, capability: str):
        """Add capability to agent"""
        self.capabilities.append(capability)

    def get_capabilities(self) -> list:
        """Get list of agent capabilities"""
        return self.capabilities.copy()

    def __str__(self):
        return f"Agent(name={self.name}, capabilities={self.capabilities})"

    def __repr__(self):
        return self.__str__()

class AgentFactory:
    def __init__(self):
        self.agents = {}

    def create_agent(self, agent_type: str) -> Agent:
        """Create agent based on type"""
        if agent_type not in self.agents:
            name_map = {
                'chat': 'ChatAgent',
                'data_processor': 'DataProcessorAgent',
                'general': 'GeneralAgent'
            }
            agent = Agent(name=name_map.get(agent_type, agent_type))
            self.agents[agent_type] = agent
        return self.agents[agent_type]

    def list_agents(self) -> Dict[str, Agent]:
        """List all available agents"""
        return self.agents

    def get_agent(self, agent_type: str) -> Agent:
        """Get existing agent by type"""
        return self.agents.get(agent_type)

    def remove_agent(self, agent_type: str) -> bool:
        """Remove agent by type"""
        if agent_type in self.agents:
            del self.agents[agent_type]
            return True
        return False
