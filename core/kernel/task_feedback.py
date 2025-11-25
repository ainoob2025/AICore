from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class TaskFeedbackLogger:
    """
    Einfacher Logger für Task-Feedback (Phase 6 – Selbstoptimierung).

    Schreibt pro Task einen JSON-Eintrag in eine .jsonl-Datei.
    Noch keine Auswertung – nur Logging.
    """

    def __init__(self, base_dir: str = "data/logs", filename: str = "task_feedback.jsonl") -> None:
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.file_path = self.base_path / filename

    def log_entry(self, entry: Dict[str, Any]) -> None:
        """
        Hängt einen Eintrag ans Logfile an (JSON-Lines: ein Eintrag pro Zeile).
        Fehler im Logging dürfen den Core nicht beeinflussen.
        """
        try:
            if "timestamp" not in entry:
                entry["timestamp"] = datetime.utcnow().isoformat()

            with self.file_path.open("a", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write("\n")
        except Exception:
            # Logging darf niemals den Core crashen.
            # Fehler werden bewusst geschluckt.
            pass