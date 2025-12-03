class BasicAgent:
    def execute(self, task: dict) -> str:
        """Execute basic tasks"""
        return f"Basic agent executed: {task.get('command', 'no command')}"