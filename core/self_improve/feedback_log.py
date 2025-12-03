'''Feedback logger for task performance and user input'''

import json
import os
from datetime import datetime

class FeedbackLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self._ensure_log_directory()

    def _ensure_log_directory(self) -> None:
        """Ensure the logs directory exists."""
        os.makedirs(self.log_dir, exist_ok=True)

    def log_task_feedback(self, task_id: str, user_input: str, agent_output: str, metrics: dict) -> bool:
        """Log feedback for a specific task."""
        log_entry = {
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'agent_output': agent_output,
            'metrics': metrics,
            'status': 'completed'
        }
        
        log_file = os.path.join(self.log_dir, f"task_{task_id}.json")
        
        # Write to file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)
        
        return True

    def get_task_feedback(self, task_id: str) -> dict:
        """Retrieve feedback for a specific task."""
        log_file = os.path.join(self.log_dir, f"task_{task_id}.json")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}