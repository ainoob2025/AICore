import sys
import json
from pathlib import Path

# Projekt-Root eintragen, damit "core" importiert werden kann
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.policy.policy_optimizer import PolicyOptimizer
from core.benchmarks.benchmark_suite import BenchmarkSuite


def _print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


def run_ab_benchmark() -> None:
    """
    Führt einen A/B-Benchmark durch:
    - A = Original-Strategien
    - B = Optimierte Strategien
    """
    _print_section("Phase 9 – A/B Benchmark: ORIGINAL STRATEGIEN")
    suite_a = BenchmarkSuite(run_name="phase9_A_original")
    summary_a = suite_a.run_all()
    print(json.dumps(summary_a, ensure_ascii=False, indent=2))

    _print_section("Phase 9 – Optimierung per PolicyOptimizer")
    optimizer = PolicyOptimizer()
    result = optimizer.optimize()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    _print_section("Phase 9 – A/B Benchmark: OPTIMIERTE STRATEGIEN")
    suite_b = BenchmarkSuite(run_name="phase9_B_optimized")
    summary_b = suite_b.run_all()
    print(json.dumps(summary_b, ensure_ascii=False, indent=2))

    _print_section("A/B Benchmark abgeschlossen")
    print("A-Run-ID:", summary_a["run_id"])
    print("B-Run-ID:", summary_b["run_id"])
    print("Vergleichswerte wurden nach data/metrics/ geschrieben.")


def main() -> None:
    _print_section("Phase 9 – Policy-Optimizer Test")
    optimizer = PolicyOptimizer()
    result = optimizer.optimize()

    print("PolicyOptimizer result:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    run_ab_benchmark()


if __name__ == "__main__":
    main()