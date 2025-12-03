"""
Planner – vollständige, enterprise-grade Task-Zerlegung nach Masterplan
"""

class Planner:
    def __init__(self):
        self.step_types = {
            'tool_call': 'Execute a specific tool',
            'agent_call': 'Activate or interact with an agent',
            'reasoning': 'Perform deep analysis or complex thinking',
            'workflow': 'Execute a predefined workflow'
        }
        self.evaluation_criteria = [
            {'metric': 'success_rate', 'target_value': 0.85, 'operator': '>='},
            {'metric': 'completion_time', 'target_value': 120, 'operator': '<='}
        ]
        self.history = []

    def decompose_goal(self, goal: str) -> list:
        if not goal or not goal.strip():
            return []

        steps = []
        lower_goal = goal.lower()

        # Tool-Calls
        if any(k in lower_goal for k in ['öffne', 'browser', 'suche', 'datei', 'terminal']):
            steps.append({
                'type': 'tool_call',
                'action': 'tool_call',
                'description': 'Browser oder File-Tool verwenden',
                'context': {'goal': goal}
            })

        # Agent-Interaktion
        if any(k in lower_goal for k in ['team', 'agent', 'hilfe']):
            steps.append({
                'type': 'agent_call',
                'action': 'agent_call',
                'description': 'Agent aktivieren',
                'context': {'goal': goal}
            })

        # Reasoning
        if any(k in lower_goal for k in ['analyse', 'erkläre', 'recherche', 'denke']):
            steps.append({
                'type': 'reasoning',
                'action': 'reasoning',
                'description': 'Tiefgehende Analyse',
                'context': {'goal': goal}
            })

        # Fallback
        if not steps:
            steps.append({
                'type': 'reasoning',
                'action': 'reasoning',
                'description': 'Direkte Antwort',
                'context': {'goal': goal}
            })

        for step in steps:
            step['evaluation_criteria'] = self.evaluation_criteria.copy()

        self.history.append({"goal": goal, "steps": steps})
        return steps

    def decompose(self, context: str) -> dict:
        goal = context.split("User:")[-1].strip() if "User:" in context else context
        steps = self.decompose_goal(goal)
        return {
            "goal": goal,
            "steps": steps,
            "tools": ["browser"] if any("browser" in s["description"].lower() for s in steps) else [],
            "needs_knowledge": any("recherche" in s["description"].lower() for s in steps)
        }