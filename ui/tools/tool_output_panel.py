'''Tool output panel with clear blocks and emojis'''

from typing import Dict, Any

class ToolOutputPanel:
    def __init__(self):
        self.tool_outputs = []

    def add_output(self, tool_name: str, content: str) -> None:
        """Add a tool output to the panel."""
        self.tool_outputs.append({
            'tool': tool_name,
            'output': content
        })

    def display(self) -> Dict[str, Any]:
        """Return formatted tool output panel output."""
        return {
            'title': "🔧 Tool Output Panel",
            'status': "Active",
            'outputs_count': len(self.tool_outputs),
            'output_list': self.tool_outputs
        }