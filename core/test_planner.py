import uuid
import json
import sys
from pathlib import Path

# Projekt-Root eintragen (damit "core" als Modul gefunden wird)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.kernel.master_agent import MasterAgent
from core.kernel.request_types import CoreRequest


def main() -> None:
    agent = MasterAgent()

    req = CoreRequest(
        trace_id=str(uuid.uuid4()),
        session_id="planner-test-session",
        user_id="sascha",
        input_type="planner",
        message="Plane einen einfachen Test-Task",
        tool_name=None,
        tool_payload=None,
        context_hints=[],
    )

    res = agent.handle_request(req)

    print("\n--- Planner Test Output ---")
    print(json.dumps(res.planner_trace, ensure_ascii=False, indent=2))
    print("\n---------------------------")


if __name__ == "__main__":
    main()
