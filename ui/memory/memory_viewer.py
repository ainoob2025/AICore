'''Memory viewer with clear blocks and emojis'''

from typing import Dict, Any

class MemoryViewer:
    def __init__(self):
        self.memory_layers = {
            'conversation': [],
            'episodic': [],
            'semantic': [],
            'autobiographical': []
        }

    def add_entry(self, layer: str, entry: Dict[str, Any]) -> None:
        """Add an entry to a specific memory layer."""
        self.memory_layers[layer].append(entry)

    def display(self) -> Dict[str, Any]:
        """Return formatted memory viewer output."""
        return {
            'title': "🧠 Memory Viewer",
            'status': "Ready",
            'layers': self.memory_layers
        }