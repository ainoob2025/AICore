"""
Feedback logger for task performance and user interactions.

Records feedback, logs, and metrics to enable self-improvement.
"""

class FeedbackLogger:
    """
    Central component for logging feedback from tasks and user interactions.
    
    Attributes:
        - log_file: Path to the feedback log file
        - entries: List of logged events (task, success, issues, feedback)
    """
    def __init__(self, log_file: str = 'feedback.log'):
        self.log_file = log_file
        self.entries = []

    def log_task(self, task_id: str, description: str, status: str, 
                 user_feedback: str = None) -> None:
        """
        Log a completed task with its outcome and feedback.
        
        Args:
            task_id: Unique identifier for the task
            description: Brief description of the task
            status: Status ('success', 'partial', 'failed')
            user_feedback: Optional feedback from the user or system
        """
        entry = {
            'task_id': task_id,
            'description': description,
            'status': status,
            'user_feedback': user_feedback,
            'timestamp': self._get_timestamp()
        }
        self.entries.append(entry)
        self._write_to_file(entry)

    def log_issue(self, issue_type: str, details: str) -> None:
        """
        Log a system or task issue.
        
        Args:
            issue_type: Type of issue (e.g., 'tool_failure', 'planning_error')
            details: Details about the issue
        """
        entry = {
            'issue_type': issue_type,
            'details': details,
            'timestamp': self._get_timestamp()
        }
        self.entries.append(entry)
        self._write_to_file(entry)

    def _get_timestamp(self) -> str:
        """
        Generate a formatted timestamp.
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _write_to_file(self, entry: dict) -> None:
        """
        Write the entry to the log file in JSON format.
        """
        import json
        
        # Open file with append mode and ensure it's properly closed
        with open(self.log_file, 'a', encoding='utf-8') as f:
            if self.entries:
                # Write header only once for the first entry
                if not f.tell():
                    json.dump([entry], f, indent=2, ensure_ascii=False)
                else:
                    json.dump([entry], f, indent=2, ensure_ascii=False)
            else:
                json.dump([entry], f, indent=2, ensure_ascii=False)

    def get_feedback(self) -> list:
        """
        Return all logged feedback entries.
        
        Returns:
            List of logged events
        """
        return self.entries.copy()

    def clear_logs(self) -> None:
        """
        Clear the log file and reset entries.
        """
        with open(self.log_file, 'w', encoding='utf-8') as f:
            pass  # Clear the file
        self.entries = []