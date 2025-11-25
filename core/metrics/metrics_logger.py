from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class MetricsLogger:
    """
    Einfacher Metrics-Logger für Phase 8.

    - Schreibt JSONL-Datei in data/metrics/
    - Eintrag pro Event:
      {
        "timestamp": ...,
        "event_type": "...",
        "payload": { ... }
      }
    """

    def __init__(self, base_dir: str = "data/metrics", run_name: Optional[str] = None) -> None:
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

        if run_name:
            self.run_id = run_name
        else:
            self.run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

        self.file_path = self.base_path / f"{self.run_id}.jsonl"

    def log_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Hängt ein Metrics-Event ans Logfile an.
        Fehler im Logging dürfen den Core NICHT beeinflussen.
        """
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "payload": payload,
            }
            with self.file_path.open("a", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write("\n")
        except Exception:
            # Metrics dürfen nie das System crashen
            pass