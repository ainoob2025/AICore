"""
Agent Factory for creating and managing specialized agents.

Provides methods to create, register, and manage agent instances with specific capabilities.
"""

class AgentFactory:
    """
    Factory class for creating specialized agents based on requirements.
    
    Attributes:
        - registered_agents: Dictionary of registered agent names and their configurations
        - default_runtime: Default runtime for new agents (e.g., 'core_runtime')
    """
    def __init__(self):
        self.registered_agents = {}
        self.default_runtime = 'core_runtime'

    def create_agent(self, name: str, type: str = None, 
                     runtime: str = None, capabilities: list = None) -> dict:
        """
        Create a new agent instance with specified configuration.
        
        Args:
            name: Unique identifier for the agent
            type: Type of agent (e.g., 'research', 'code', 'debug', 'memory')
            runtime: Runtime to use for the agent (if applicable)
            capabilities: List of specific capabilities the agent should have
        
        Returns:
            Dictionary with agent configuration and status
        """
        if not name.strip():
            return {
                'status': 'error',
                'message': 'Agent name is required',
                'action_required': 'Provide a valid agent name'
            }
        
        # Set default values
        runtime = runtime or self.default_runtime
        capabilities = capabilities or []
        
        # Create agent configuration
        agent_config = {
            'name': name,
            'type': type or 'default',
            'runtime': runtime,
            'capabilities': capabilities,
            'status': 'created',
            'creation_timestamp': self._get_timestamp()
        }
        
        # Store in registry
        self.registered_agents[name] = agent_config
        
        return {
            'status': 'success',
            'message': f'Agent {name} created successfully',
            'configuration': agent_config
        }

    def register_agent(self, name: str, config: dict) -> dict:
        """
        Register an existing agent configuration.
        
        Args:
            name: Name of the agent to register
            config: Dictionary with agent configuration details
        
        Returns:
            Dictionary with registration status and message
        """
        if not name.strip():
            return {
                'status': 'error',
                'message': 'Agent name is required',
                'action_required': 'Provide a valid agent name'
            }
        
        # Validate configuration
        if not config:
            return {
                'status': 'error',
                'message': 'Configuration data is required',
                'action_required': 'Provide agent details'
            }
        
        # Update registry
        self.registered_agents[name] = config
        
        return {
            'status': 'success',
            'message': f'Agent {name} registered successfully',
            'configuration': config
        }

    def get_agent(self, name: str) -> dict:
        """
        Retrieve an agent configuration by name.
        
        Args:
            name: Name of the agent to retrieve
        
        Returns:
            Dictionary with agent configuration or None if not found
        """
        return self.registered_agents.get(name)

    def list_agents(self) -> list:
        """
        Return a list of all registered agents.
        
        Returns:
            List of agent configurations
        """
        return list(self.registered_agents.values())

    def update_agent_capabilities(self, name: str, new_capabilities: list) -> dict:
        """
        Update the capabilities of an existing agent.
        
        Args:
            name: Name of the agent to update
            new_capabilities: List of new capabilities
        
        Returns:
            Dictionary with update status and message
        """
        if not name.strip():
            return {
                'status': 'error',
                'message': 'Agent name is required',
                'action_required': 'Provide a valid agent name'
            }
        
        if not new_capabilities:
            return {
                'status': 'error',
                'message': 'Capabilities list is required',
                'action_required': 'Provide at least one capability'
            }
        
        # Update capabilities in registry
        if name in self.registered_agents:
            agent = self.registered_agents[name]
            agent['capabilities'] = new_capabilities
            agent['last_updated'] = self._get_timestamp()
            
            return {
                'status': 'success',
                'message': f'Capabilities updated for agent {name}',
                'configuration': agent
            }
        else:
            return {
                'status': 'error',
                'message': f'Agent {name} not found in registry',
                'action_required': 'Create the agent first'
            }

    def delete_agent(self, name: str) -> dict:
        """
        Delete an agent from the registry.
        
        Args:
            name: Name of the agent to delete
        
        Returns:
            Dictionary with deletion status and message
        """
        if not name.strip():
            return {
                'status': 'error',
                'message': 'Agent name is required',
                'action_required': 'Provide a valid agent name'
            }
        
        if name in self.registered_agents:
            del self.registered_agents[name]
            
            return {
                'status': 'success',
                'message': f'Agent {name} deleted successfully',
                'configuration': None
            }
        else:
            return {
                'status': 'error',
                'message': f'Agent {name} not found in registry',
                'action_required': 'Create the agent first'
            }

    def _get_timestamp(self) -> str:
        """
        Generate a formatted timestamp.
        
        Returns:
            Formatted timestamp string
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")