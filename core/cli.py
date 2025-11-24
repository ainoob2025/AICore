import uuid
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# KORREKTER Importpfad nach Harmonisierung
from core.kernel.master_agent import MasterAgent
from core.kernel.request_types import CoreRequest


def main():
    if len(sys.argv) < 2:
        print("Bitte eine Frage angeben.")
        sys.exit(1)

    user_text = sys.argv[1]

    agent = MasterAgent()

    req = CoreRequest(
        trace_id=str(uuid.uuid4()),
        session_id="cli-session",
        user_id="cli-user",
        input_type="chat",
        message=user_text,
        tool_name=None,
        tool_payload=None,
        context_hints=[]
    )

    res = agent.handle_request(req)

    if res.messages:
        print("\nAntwort:")
        print(res.messages[0]["content"])
    else:
        print("\nKeine Antwort erhalten.")


if __name__ == "__main__":
    main()
