"""
Agent Runtime for managing agent lifecycle and execution.

Provides methods to create, start, stop, and monitor agent processes with shared runtimes.
"""

import time
import uuid
from typing import Dict, List, Optional

class AgentRuntime:
    """
    Runtime manager for executing agents within shared Python environments.
    
    Attributes:
        - runtime_name: Name of the runtime (e.g., 'core_runtime', 'plugin_runtime')
        - processes: Dictionary of running agent processes
        - status: Current health and operational status
    """
    def __init__(self, runtime_name: str = 'core_runtime'):
        self.runtime_name = runtime_name
        self.processes = {}
        self.status = {
            'health': 'healthy',
            'uptime': 0,
            'active_agents': 0
        }
        self.start_time = time.time()

    def create_process(self, agent_name: str, command: str) -> dict:
        """
        Create a new process for an agent.
        
        Args:
            agent_name: Name of the agent to execute
            command: Command string or function to run
        
        Returns:
            Dictionary with process information and status
        """
        if not agent_name.strip():
            return {
                'status': 'error',
                'message': 'Agent name is required',
                'action_required': 'Provide a valid agent name'
            }
        
        pid = self._generate_pid()
        
        process_config = {
            'agent_name': agent_name,
            'command': command,
            'status': 'created',
            'start_timestamp': self._get_timestamp(),
            'pid': pid
        }
        
        self.processes[pid] = process_config
        
        return {
            'status': 'success',
            'message': f'Process created for agent {agent_name}',
            'process_id': pid,
            'configuration': process_config
        }

    def start_process(self, process_id: str) -> dict:
        """
        Start an existing process.
        
        Args:
            process_id: ID of the process to start
        
        Returns:
            Dictionary with start status and message
        """
        if not process_id.strip():
            return {
                'status': 'error',
                'message': 'Process ID is required',
                'action_required': 'Provide a valid process ID'
            }
        
        if process_id in self.processes:
            process = self.processes[process_id]
            process['status'] = 'running'
            process['start_time'] = self._get_timestamp()
            self.status['active_agents'] = len([p for p in self.processes.values() if p['status'] == 'running'])
            
            return {
                'status': 'success',
                'message': f'Process {process_id} started successfully',
                'configuration': process
            }
        else:
            return {
                'status': 'error',
                'message': f'Process {process_id} not found in registry',
                'action_required': 'Create the process first'
            }

    def stop_process(self, process_id: str) -> dict:
        """
        Stop an existing process.
        
        Args:
            process_id: ID of the process to stop
        
        Returns:
            Dictionary with stop status and message
        """
        if not process_id.strip():
            return {
                'status': 'error',
                'message': 'Process ID is required',
                'action_required': 'Provide a valid process ID'
            }
        
        if process_id in self.processes:
            process = self.processes[process_id]
            process['status'] = 'stopped'
            process['stop_time'] = self._get_timestamp()
            self.status['active_agents'] = len([p for p in self.processes.values() if p['status'] == 'running'])
            
            return {
                'status': 'success',
                'message': f'Process {process_id} stopped successfully',
                'configuration': process
            }
        else:
            return {
                'status': 'error',
                'message': f'Process {process_id} not found in registry',
                'action_required': 'Create the process first'
            }

    def monitor_process(self, process_id: str) -> dict:
        """
        Monitor the current status of a process.

        Args:
            process_id: ID of the process to monitor

        Returns:
            Dictionary with monitoring status and details
        """
        if not process_id.strip():
            return {
                'status': 'error',
                'message': 'Process ID is required',
                'action_required': 'Provide a valid process ID'
            }

        if process_id in self.processes:
            process = self.processes[process_id]
            return {
                'status': 'success',
                'message': f'Process {process_id} is currently {process["status"]}',
                'process_details': process
            }
        else:
            return {
                'status': 'error',
                'message': f'Process {process_id} not found in registry',
                'action_required': 'Create the process first'
            }

    def list_processes(self) -> dict:
        """
        List all processes in the runtime.
        
        Returns:
            Dictionary with list of all processes
        """
        return {
            'status': 'success',
            'runtime_name': self.runtime_name,
            'total_processes': len(self.processes),
            'processes': self.processes
        }

    def get_runtime_status(self) -> dict:
        """
        Get the current status of the runtime.
        
        Returns:
            Dictionary with runtime health and statistics
        """
        self.status['uptime'] = int(time.time() - self.start_time)
        self.status['active_agents'] = len([p for p in self.processes.values() if p['status'] == 'running'])
        
        return {
            'status': 'success',
            'runtime_name': self.runtime_name,
            'runtime_status': self.status,
            'total_processes': len(self.processes)
        }

    def cleanup(self) -> dict:
        """
        Clean up stopped processes from the runtime.
        
        Returns:
            Dictionary with cleanup results
        """
        stopped_processes = [pid for pid, proc in self.processes.items() if proc['status'] == 'stopped']
        
        for pid in stopped_processes:
            del self.processes[pid]
        
        return {
            'status': 'success',
            'message': f'Cleaned up {len(stopped_processes)} stopped processes',
            'removed_count': len(stopped_processes)
        }

    def _generate_pid(self) -> str:
        """
        Generate a unique process ID.
        
        Returns:
            Unique process identifier string
        """
        return f"{self.runtime_name}_{uuid.uuid4().hex[:8]}"

    def _get_timestamp(self) -> float:
        """
        Get the current timestamp.
        
        Returns:
            Current Unix timestamp
        """
        return time.time()
