import uuid
import json
import sys
from pathlib import Path

# Projekt-Root eintragen (damit "core" als Modul gefunden wird)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.kernel.task_feedback import TaskFeedbackLogger
from core.agents.self_improvement_agent import SelfImprovementAgent
from core.kernel.master_agent import MasterAgent
from core.kernel.request_types import CoreRequest


def _test_task_feedback_logger() -> None:
    """
    Mini-Test für TaskFeedbackLogger:
    - schreibt einen Eintrag in eine Test-Logdatei
    - lädt die letzte Zeile und prüft auf gültiges JSON
    """

    log_path = Path("data/logs/task_feedback_phase6_logger_test.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = TaskFeedbackLogger(base_dir="data/logs", filename="task_feedback_phase6_logger_test.jsonl")

    entry = {
        "task_id": "test-logger-123",
        "user_id": "phase6-tester",
        "session_id": "logger-session",
        "input_type": "chat",
        "goal": "Logger-Test",
        "result_quality": "unknown",
        "used_tools": ["echo"],
        "plan_structure": [],
        "duration_sec": 0.01,
        "errors": [],
    }

    logger.log_entry(entry)

    # Letzte Zeile lesen und prüfen
    with log_path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    last = lines[-1]
    obj = json.loads(last)

    print("\n--- Phase 6: TaskFeedbackLogger Test ---")
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    print("----------------------------------------")


def _prepare_test_feedback_log(log_path: Path) -> None:
    """
    Erstellt eine kleine Test-Feedback-Logdatei für SelfImprovementAgent.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entries = [
        {
            "task_id": "t1",
            "user_id": "u1",
            "session_id": "s1",
            "input_type": "tool",
            "goal": "Test-Task 1",
            "result_quality": "unknown",
            "used_tools": ["echo"],
            "plan_structure": [],
            "duration_sec": 0.5,
            "errors": [],
        },
        {
            "task_id": "t2",
            "user_id": "u1",
            "session_id": "s1",
            "input_type": "tool",
            "goal": "Test-Task 2",
            "result_quality": "unknown",
            "used_tools": ["thinking_reason"],
            "plan_structure": [],
            "duration_sec": 1.0,
            "errors": ["dummy-error"],
        },
    ]

    with log_path.open("w", encoding="utf-8") as f:
        for e in entries:
            json.dump(e, f, ensure_ascii=False)
            f.write("\n")


def _prepare_test_tool_stats(stats_path: Path) -> None:
    """
    Erstellt eine kleine Test-stats.json für SelfImprovementAgent.
    """
    stats_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "echo": {
            "success_count": 10,
            "failure_count": 0,
            "avg_latency": 0.05,
            "last_error": None,
        },
        "thinking_reason": {
            "success_count": 3,
            "failure_count": 2,
            "avg_latency": 1.0,
            "last_error": None,
        },
    }

    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _test_self_improvement_agent() -> None:
    """
    Testet SelfImprovementAgent.run_analysis() mit separaten Testdateien.
    """

    log_path = Path("data/logs/task_feedback_phase6_test.jsonl")
    stats_path = Path("data/tools/stats_phase6_test.json")
    strategies_path = Path("config/strategies_phase6_test.json")

    _prepare_test_feedback_log(log_path)
    _prepare_test_tool_stats(stats_path)

    agent = SelfImprovementAgent(
        feedback_log_path=str(log_path),
        tool_stats_path=str(stats_path),
        strategies_path=strategies_path,
    )

    strategies = agent.run_analysis()

    print("\n--- Phase 6: SelfImprovementAgent Test ---")
    print(json.dumps(strategies, ensure_ascii=False, indent=2))
    print("------------------------------------------")


def _test_master_agent_self_improve_integration() -> None:
    """
    Testet die Integration von MasterAgent.run_self_improvement()
    über CoreRequest mit input_type="self_improve".
    """
    master = MasterAgent()

    req = CoreRequest(
        trace_id=str(uuid.uuid4()),
        session_id="phase6-self-improve-session",
        user_id="phase6-tester",
        input_type="self_improve",
        message=None,
        tool_name=None,
        tool_payload=None,
        context_hints=[],
    )

    res = master.handle_request(req)

    print("\n--- Phase 6: MasterAgent self_improve Test ---")
    if res.messages:
        try:
            content = res.messages[0].get("content", "")
            parsed = json.loads(content)
        except Exception:
            parsed = {"raw": res.messages[0]}
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        print("Keine Messages im Response.")
    print("--------------------------------------------")


def main() -> None:
    """
    Sammel-Test für Phase 6:
    - Logger
    - SelfImprovementAgent
    - MasterAgent-Integration
    """
    _test_task_feedback_logger()
    _test_self_improvement_agent()
    _test_master_agent_self_improve_integration()


if __name__ == "__main__":
    main()