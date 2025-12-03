'''Metrics collector for system performance and failure tracking'''

from typing import Dict, Any, List
import json
from datetime import datetime

class MetricsCollector:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self._ensure_log_directory()

    def _ensure_log_directory(self) -> None:
        """Ensure the logs directory exists."""
        os.makedirs(self.log_dir, exist_ok=True)

    def collect(self, module: str, metric_name: str, value: Any, category: str = 'performance') -> bool:
        """Collect a single metric for a specific module."""
        log_entry = {
            'module': module,
            'metric_name': metric_name,
            'value': value,
            'category': category,
            'timestamp': datetime.now().isoformat(),
            'status': 'collected'
        }
        
        log_file = os.path.join(self.log_dir, f"metrics_{module}_{metric_name}.json")
        
        # Write to file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)
        
        return True

    def log_failure(self, module: str, error_message: str, failure_category: str = 'system_error') -> bool:
        """Log a system failure with category."""
        log_entry = {
            'module': module,
            'error_message': error_message,
            'failure_category': failure_category,
            'timestamp': datetime.now().isoformat(),
            'status': 'failed'
        }
        
        log_file = os.path.join(self.log_dir, f"failures_{module}.json")
        
        # Write to file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)
        
        return True

    def get_metrics(self, module: str, metric_name: str) -> Dict[str, Any]:
        """Retrieve a specific metric."""
        log_file = os.path.join(self.log_dir, f"metrics_{module}_{metric_name}.json")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}