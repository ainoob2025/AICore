'''RAG manager dashboard with clear blocks and emojis'''

from typing import Dict, Any

class RAGManager:
    def __init__(self):
        self.documents = [
            {'name': 'AI Core Masterplan', 'status': 'ingested'},
            {'name': 'Project Requirements', 'status': 'active'},
            {'name': 'User Guidelines', 'status': 'active'}
        ]

    def display(self) -> Dict[str, Any]:
        """Return formatted RAG manager output."""
        return {
            'title': "📚 RAG Manager",
            'status': "Active",
            'documents_count': len(self.documents),
            'document_list': self.documents
        }