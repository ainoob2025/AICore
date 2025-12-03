'''Chat interface with dark mode, clear blocks and emojis'''

from typing import Dict, Any

class ChatInterface:
    def __init__(self):
        self.messages = []

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the chat history."""
        self.messages.append({
            'role': role,
            'content': content
        })

    def display(self) -> Dict[str, Any]:
        """Return formatted chat interface output."""
        return {
            'title': "💬 Chat Interface",
            'status': "Active",
            'messages_count': len(self.messages),
            'message_list': self.messages
        }