'''Plugin manager for installing, listing and removing plugins from the marketplace'''

from typing import List, Dict, Any
import json

class PluginManager:
    def __init__(self):
        self.plugins = []

    def install_plugin(self, plugin_id: str, plugin_type: str, runtime: str) -> bool:
        """Install a new plugin from the marketplace."""
        plugin = {
            'plugin_id': plugin_id,
            'type': plugin_type,
            'runtime': runtime,
            'status': 'installed',
            'installed_at': json.dumps({
                'timestamp': '2024-01-20T11:00:00Z'
            })
        }
        self.plugins.append(plugin)
        return True

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all installed plugins."""
        return self.plugins

    def remove_plugin(self, plugin_id: str) -> bool:
        """Remove a specific plugin from the marketplace."""
        for plugin in self.plugins:
            if plugin['plugin_id'] == plugin_id:
                self.plugins.remove(plugin)
                return True
        
        return False

    def search_plugins(self, query: str) -> List[Dict[str, Any]]:
        """Search for plugins by name or type."""
        results = []
        for plugin in self.plugins:
            if query.lower() in plugin['type'].lower():
                results.append(plugin)
        
        return results