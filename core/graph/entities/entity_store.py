'''Entity store for storing concepts, events and facts'''

from typing import Dict, List, Any

class EntityStore:
    def __init__(self):
        self.entities: Dict[str, Dict[str, Any]] = {}

    def add(self, entity_id: str, entity_data: Dict[str, Any]) -> bool:
        """Add a new entity to the store."""
        if entity_id not in self.entities:
            self.entities[entity_id] = entity_data
            return True
        else:
            # Update existing entity
            self.entities[entity_id].update(entity_data)
            return True

    def get(self, entity_id: str) -> Dict[str, Any]:
        """Retrieve an entity by ID."""
        return self.entities.get(entity_id, {})

    def list_all(self) -> List[Dict[str, Any]]:
        """Return all entities in the store."""
        return list(self.entities.values())