class MemoryOS:
    def __init__(self):
        self.conversation = []
        self.episodic = {}
        self.semantic = {}
    def add_turn(self, role, content):
        self.conversation.append(f'{role}: {content}')
    def get_conversation(self, limit=20):
        return '\n'.join(self.conversation[-limit:])
    def add_episodic(self, event):
        self.episodic[len(self.episodic)] = event
    def add_semantic(self, fact):
        self.semantic[len(self.semantic)] = fact