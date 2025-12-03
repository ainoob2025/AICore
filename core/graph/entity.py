"""
Entity representation for the Knowledge Graph.

An entity is a fundamental concept, event, or object in the system's knowledge.
Entities can be linked to other entities via relations.
"""

class Entity:
    """
    A single entity in the graph.
    
    Attributes:
        - name: The unique identifier of the entity
        - type: The category or domain (e.g., 'person', 'task', 'document')
        - properties: A dictionary of key-value pairs describing the entity
        - relations: A list of tuples (related_entity, relation_type)
    """
    def __init__(self, name: str, type: str, properties: dict = None, relations: list = None):
        self.name = name
        self.type = type
        self.properties = properties or {}
        self.relations = relations or []

    def to_dict(self) -> dict:
        """
        Convert the entity instance to a dictionary for serialization.
        """
        return {
            'name': self.name,
            'type': self.type,
            'properties': self.properties,
            'relations': self.relations
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Entity':
        """
        Create an entity instance from a dictionary.
        """
        return cls(
            name=data['name'],
            type=data['type'],
            properties=data.get('properties', {}),
            relations=data.get('relations', [])
        )