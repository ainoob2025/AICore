from typing import List

class Planner:
    def __init__(self):
        pass

    def decompose(self, goal: str) -> List[str]:
        """Decompose high-level goal into executable steps"""
        print(f"[Planner] Decomposing goal: {goal}")
        
        # Simple decomposition strategy
        if "chat" in goal.lower() or "query" in goal.lower():
            return ["agent:chat", "tool:response_formatter"]
        elif "analyze" in goal.lower() or "process" in goal.lower():
            return ["agent:data_processor", "tool:analyzer"]
        else:
            return ["agent:general", "tool:helper"]

    def generate_workflow(self, steps: List[str]) -> dict:
        """Generate workflow from steps"""
        workflow = {}
        for i, step in enumerate(steps):
            workflow[f'step_{i+1}'] = step
        return workflow