'''Merged configuration system for consolidating settings from multiple sources'''

from typing import Dict, Any, List
import json

class MergedConfiguration:
    def __init__(self):
        self.config_sources = {
            'settings': {},
            'models': {},
            'rag': {},
            'policies': {},
            'tools': {}
        }

    def load_source(self, source: str, config_path: str) -> bool:
        """Load configuration from a specific source."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            self.config_sources[source] = content
            return True
        except Exception as e:
            print(f"Error loading {source} from {config_path}: {str(e)}")
            return False

    def merge(self) -> Dict[str, Any]:
        """Merge all configuration sources into a single consolidated structure."""
        merged = {}
        
        # Merge settings first
        for key, value in self.config_sources['settings'].items():
            if isinstance(value, dict):
                merged[key] = value
        
        # Add models
        for key, value in self.config_sources['models'].items():
            if isinstance(value, dict):
                merged['models'][key] = value
        
        # Add RAG configuration
        for key, value in self.config_sources['rag'].items():
            if isinstance(value, dict):
                merged['rag'][key] = value
        
        # Add policies
        for key, value in self.config_sources['policies'].items():
            if isinstance(value, dict):
                merged['policies'][key] = value
        
        return merged