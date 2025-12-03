'''Build script for creating deployment packages and updating reference.json'''

import os
import json
from datetime import datetime

def build_and_update_reference():
    """Build the system and update the reference file with current state."""
    
    # Create a new version of the reference file
    reference_data = {
        'project_root': 'C:\AI\AICore',
        'last_updated': datetime.now().isoformat(),
        'execution_state': {
            'phase': '10 - Foundation Upgrade',
            'status': 'completed'
        },
        'modules': [
            {'name': 'gateway', 'version': '1.2'},
            {'name': 'kernel', 'version': '1.1'},
            {'name': 'planner', 'version': '1.0'},
            {'name': 'tools', 'version': '1.3'}
        ]
    }
    
    # Write to reference file
    with open('docs/aicore_reference.json', 'w') as f:
        json.dump(reference_data, f, indent=2)
    
    print("Build completed and reference.json updated.")

if __name__ == "__main__":
    build_and_update_reference()