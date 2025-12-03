'''Policy version manager for tracking policy changes and enabling rollbacks'''

from typing import Dict, Any
import json
from datetime import datetime

class PolicyVersionManager:
    def __init__(self):
        self.versions = {}
        self.current_version = None

    def create_policy_version(self, policy_name: str, version: str, config: Dict[str, Any]) -> bool:
        """Create a new version of a policy."""
        if policy_name not in self.versions:
            self.versions[policy_name] = []
        
        version_entry = {
            'version': version,
            'config': config,
            'timestamp': datetime.now().isoformat(),
            'status': 'active'
        }
        self.versions[policy_name].append(version_entry)
        
        if self.current_version is None:
            self.current_version = version
        
        return True

    def get_policy_version(self, policy_name: str, version: str) -> Dict[str, Any]:
        """Retrieve a specific policy version."""
        if policy_name in self.versions:
            for entry in self.versions[policy_name]:
                if entry['version'] == version:
                    return entry
        
        return None

    def rollback_to_version(self, policy_name: str, version: str) -> bool:
        """Roll back to a specific policy version."""
        if policy_name in self.versions:
            for entry in self.versions[policy_name]:
                if entry['version'] == version:
                    self.current_version = version
                    return True
        
        return False

    def list_versions(self, policy_name: str) -> List[Dict[str, Any]]:
        """List all versions of a policy."""
        if policy_name in self.versions:
            return self.versions[policy_name]
        else:
            return []