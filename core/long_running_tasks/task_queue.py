'''Task queue for managing long-running tasks and their execution'''

from typing import List, Dict, Any
import json

class TaskQueue:
    def __init__(self):
        self.tasks = []

    def add_task(self, task_id: str, description: str, timeout_seconds: int) -> bool:
        """Add a new long-running task to the queue."""
        task = {
            'task_id': task_id,
            'description': description,
            'status': 'pending',
            'timeout_seconds': timeout_seconds,
            'created_at': json.dumps({
                'timestamp': '2024-01-20T10:30:00Z'
            })
        }
        self.tasks.append(task)
        return True

    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update the status of a specific task."""
        for task in self.tasks:
            if task['task_id'] == task_id:
                task['status'] = status
                return True
        
        return False

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Retrieve the current status of a specific task."""
        for task in self.tasks:
            if task['task_id'] == task_id:
                return task
        
        return {
            'task_id': task_id,
            'status': 'not_found',
            'message': "Task not found."
        }