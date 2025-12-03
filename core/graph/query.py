"""
Query operations for the Knowledge Graph.

Provides methods to search, filter, and retrieve entities from the graph.
"""

class Query:
    """
    A query builder for the Knowledge Graph.
    
    Methods:
        - find_entities: Search for entities matching a pattern
        - get_related: Retrieve entities related to a given entity by type
        - filter_by_type: Get all entities of a specific type
        - search_with_properties: Find entities with specific property values
        - build_query: Construct a query string from the builder state
    """
    def __init__(self, graph):
        self.graph = graph
        self.filters = {}
        self.conditions = []

    def find_entities(self, pattern: str = None, type_filter: str = None, 
                      properties_filter: dict = None) -> list:
        """
        Find entities that match a given pattern.
        
        Args:
            pattern: A string or regex to search within entity names or properties
            type_filter: Filter entities by their type (e.g., 'task', 'person')
            properties_filter: Dictionary of property-value pairs to filter on
        
        Returns:
            List of matching Entity instances.
        """
        results = []
        for entity in self.graph.entities:
            if pattern and (pattern.lower() not in entity.name.lower() and 
                           pattern.lower() not in str(entity.properties).lower()):
                continue
            if type_filter and entity.type != type_filter:
                continue
            if properties_filter:
                match = True
                for prop, value in properties_filter.items():
                    if str(entity.properties.get(prop)) != str(value):
                        match = False
                        break
                if not match:
                    continue
            results.append(entity)
        return results

    def get_related(self, entity_name: str, relation_type: str) -> list:
        """
        Retrieve all entities related to a given entity by a specific relation type.
        
        Args:
            entity_name: The name of the entity to find relations for
            relation_type: The type of relation (e.g., 'has', 'part_of')
        
        Returns:
            List of Entity instances that are related to the given entity.
        """
        results = []
        for entity in self.graph.entities:
            if (entity.name == entity_name and 
                any(rel[1] == relation_type for rel in entity.relations)):
                results.append(entity)
        return results

    def filter_by_type(self, entity_type: str) -> list:
        """
        Get all entities of a specific type.
        
        Args:
            entity_type: The type to filter by (e.g., 'person', 'task')
        
        Returns:
            List of Entity instances of the given type.
        """
        return [entity for entity in self.graph.entities if entity.type == entity_type]

    def search_with_properties(self, properties_filter: dict) -> list:
        """
        Find entities with specific property values.
        
        Args:
            properties_filter: Dictionary of property-value pairs to filter on
        
        Returns:
            List of matching Entity instances.
        """
        return self.find_entities(properties_filter=properties_filter)

    def build_query(self) -> str:
        """
        Construct a query string from the current builder state.
        
        Returns:
            A formatted SQL-like query string that can be used for cross-memory search integration.
        """
        query_parts = []
        if self.filters:
            query_parts.append(f'WHERE {self.filters}')
        if self.conditions:
            query_parts.append('AND '.join(self.conditions))
        return ' '.join(query_parts)