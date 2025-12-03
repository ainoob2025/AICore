"""
Knowledge Graph core module.

The Knowledge Graph stores entities, concepts, events, and relations,
and provides methods for querying, searching, and cross-memory integration.
"""

class Graph:
    """
    The central knowledge graph engine.
    
    Attributes:
        - entities: List of Entity instances
        - relations: List of tuples (entity1, entity2, relation_type)
        - memory_links: Dictionary linking entities to memory layers (conversation, episodic, semantic)
    """
    def __init__(self):
        self.entities = []
        self.relations = []
        self.memory_links = {}

    def add_entity(self, entity: 'Entity') -> None:
        """
        Add a new entity to the graph.
        
        Args:
            entity: An Entity instance to be added
        """
        self.entities.append(entity)

    def remove_entity(self, name: str) -> bool:
        """
        Remove an entity by its name.
        
        Args:
            name: The name of the entity to remove
        
        Returns:
            True if entity was found and removed, False otherwise
        """
        for i, entity in enumerate(self.entities):
            if entity.name == name:
                self.entities.pop(i)
                return True
        return False

    def add_relation(self, entity1: str, entity2: str, relation_type: str) -> None:
        """
        Add a relation between two entities.
        
        Args:
            entity1: Name of the first entity
            entity2: Name of the second entity
            relation_type: Type of relation (e.g., 'has', 'part_of')
        """
        self.relations.append((entity1, entity2, relation_type))

    def get_entities(self) -> list:
        """
        Return all entities in the graph.
        
        Returns:
            List of Entity instances
        """
        return self.entities.copy()

    def search(self, pattern: str = None, type_filter: str = None, 
               properties_filter: dict = None) -> list:
        """
        Search for entities matching a pattern.
        
        Args:
            pattern: String to match in names or properties
            type_filter: Filter by entity type
            properties_filter: Dictionary of property-value pairs
        
        Returns:
            List of Entity instances that match the criteria
        """
        return Query(self).find_entities(
            pattern=pattern, type_filter=type_filter, properties_filter=properties_filter)

    def get_related(self, entity_name: str, relation_type: str) -> list:
        """
        Get entities related to a given entity by relation type.
        
        Args:
            entity_name: Name of the entity to find relations for
            relation_type: Type of relation (e.g., 'has', 'part_of')
        
        Returns:
            List of Entity instances that are related to the given entity
        """
        return Query(self).get_related(entity_name, relation_type)

    def filter_by_type(self, entity_type: str) -> list:
        """
        Get all entities of a specific type.
        
        Args:
            entity_type: Type to filter by (e.g., 'person', 'task')
        
        Returns:
            List of Entity instances of the given type
        """
        return Query(self).filter_by_type(entity_type)

    def search_with_properties(self, properties_filter: dict) -> list:
        """
        Find entities with specific property values.
        
        Args:
            properties_filter: Dictionary of property-value pairs to filter on
        
        Returns:
            List of matching Entity instances
        """
        return Query(self).search_with_properties(properties_filter)

    def build_memory_link(self, entity_name: str, memory_type: str) -> None:
        """
        Link an entity to a specific memory layer.
        
        Args:
            entity_name: Name of the entity
            memory_type: Type of memory (e.g., 'conversation', 'episodic')
        """
        self.memory_links[entity_name] = memory_type
        
        # Returns a dictionary with the entity name and its memory type for cross-memory search integration
        return {"entity": entity_name, "memory_type": memory_type}