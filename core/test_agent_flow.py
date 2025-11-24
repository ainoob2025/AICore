import json
import requests
import uuid

BASE_URL = "http://localhost:10010"


def print_section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


def test_agent_flow():
    user_id = "sascha"

    # --------------------------------------------------------------------------
    # 1) AGENT CREATE (Planner + AgentFactory)
    # --------------------------------------------------------------------------
    print_section("1) AGENT CREATE (Planner + AgentFactory)")

    payload = {
        "user_id": user_id,
        "task": "Testlauf AgentRunner (Flow)",
        "template": "research_agent"
    }

    r = requests.post(f"{BASE_URL}/agent/create", json=payload)
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    agent_id = data["agent"]["agent_id"]

    # --------------------------------------------------------------------------
    # 2) AGENT STEP (Step hinzufügen)
    # --------------------------------------------------------------------------
    print_section("2) AGENT STEP (Step hinzufügen)")

    payload = {
        "agent_id": agent_id,
        "step_type": "info",
        "description": "Flow-Test: Schritt 1",
        "data": {"a": 1, "b": True}
    }

    r = requests.post(f"{BASE_URL}/agent/step", json=payload)
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # --------------------------------------------------------------------------
    # 3) AGENT RUN (Step ausführen)
    # --------------------------------------------------------------------------
    print_section("3) AGENT RUN (Step ausführen)")

    payload = {"agent_id": agent_id}

    r = requests.post(f"{BASE_URL}/agent/run", json=payload)
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    print_section("Flow-Test abgeschlossen!")


if __name__ == "__main__":
    test_agent_flow()
