'''Relation manager for storing and querying entity relationships'''

from typing import List, Dict, Any
from .entity_store import EntityStore

class RelationManager:
    def __init__(self, entity_store: EntityStore):
        self.entity_store = entity_store
        self.relations: Dict[str, List[Dict[str, Any]]] = {}

    def add_relation(self, from_entity: str, to_entity: str, relation_type: str, attributes: Dict[str, Any] = None) -> bool:
        """Add a relationship between two entities."""
        if from_entity not in self.relations:
            self.relations[from_entity] = []
        
        relation_data = {
            'to': to_entity,
            'type': relation_type,
            'attributes': attributes or {}
        }
        self.relations[from_entity].append(relation_data)
        return True

    def get_relations(self, entity_id: str) -> List[Dict[str, Any]]:
        """Retrieve all relations for a specific entity."""
        return self.relations.get(entity_id, [])

    def list_all_relations(self) -> List[Dict[str, Any]]:
        """Return all stored relations."""
        result = []
        for from_entity, relations in self.relations.items():
            for relation in relations:
                result.append({
                    'from': from_entity,
                    'to': relation['to'],
                    'type': relation['type'],
                    'attributes': relation['attributes']
                })
        return result