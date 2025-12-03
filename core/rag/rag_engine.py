class RAGEngine:
    def ingest(self, docs):
        return 'Ingested '
    def query(self, q):
        return {'answer': f'RAG-Antwort zu: {q}'}