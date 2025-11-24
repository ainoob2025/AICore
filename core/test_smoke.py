import json
import sys
import requests

BASE_URL = "http://localhost:10010"


def test_chat():
    resp = requests.post(
        f"{BASE_URL}/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"user_id": "sascha", "message": "Smoke Test Chat"}),
    )
    resp.raise_for_status()
    data = resp.json()
    assert "reply" in data and isinstance(data["reply"], str)
    print("[OK] Chat")


def test_tool_echo():
    resp = requests.post(
        f"{BASE_URL}/tool",
        headers={"Content-Type": "application/json"},
        data=json.dumps(
            {
                "user_id": "sascha",
                "tool": "echo",
                "payload": {"text": "smoke"},
            }
        ),
    )
    resp.raise_for_status()
    data = resp.json()
    assert data.get("result", {}).get("ok") is True
    print("[OK] Tool (echo)")


def test_thinker():
    resp = requests.post(
        f"{BASE_URL}/thinker_assist",
        headers={"Content-Type": "application/json"},
        data=json.dumps(
            {
                "user_id": "sascha",
                "question": "Kleiner Smoke Test: 2 + 3 * 4?",
            }
        ),
    )
    resp.raise_for_status()
    data = resp.json()
    assert "reply" in data
    print("[OK] Thinker Assist")


def test_memory():
    resp1 = requests.get(f"{BASE_URL}/episodes/sascha?limit=5")
    resp2 = requests.get(f"{BASE_URL}/semantic/sascha?limit=5")
    resp1.raise_for_status()
    resp2.raise_for_status()
    data1 = resp1.json()
    data2 = resp2.json()
    assert "events" in data1
    assert "knowledge" in data2
    print("[OK] Memory (episodic + semantic)")


def main():
    tests = [test_chat, test_tool_echo, test_thinker, test_memory]
    failed = False

    for t in tests:
        try:
            t()
        except Exception as e:
            failed = True
            print(f"[FAIL] {t.__name__}: {e}")

    if failed:
        sys.exit(1)
    else:
        print("Smoke Test: ALLE CHECKS OK")


if __name__ == "__main__":
    main()
