import sys
import json
from pathlib import Path

# Projekt-Root hinzufügen, damit "core" importiert werden kann
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.benchmarks.benchmark_suite import BenchmarkSuite


def main() -> None:
    print("================================================================================")
    print("Phase 8 – Benchmark Suite")
    print("================================================================================")

    suite = BenchmarkSuite()

    summary = suite.run_all()

    print("\n--- Benchmark Summary ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    print("\nDie vollständigen Metriken findest du in:")
    print(f"  data/metrics/{suite.metrics.run_id}.jsonl")

    print("\n================================================================================")
    print("Phase 8 – ALLE CHECKS OK (Benchmark-Suite lief erfolgreich).")
    print("================================================================================")


if __name__ == "__main__":
    main()