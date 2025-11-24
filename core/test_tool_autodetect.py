import sys
from pathlib import Path

# Projekt-Root eintragen (damit "core" als Modul gefunden wird)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tools.tool_router import ToolRouter


def _make_router() -> ToolRouter:
    """
    Erstellt einen ToolRouter mit Dummy-API-URL, damit keine echten
    LM-Studio-Requests ausgeführt werden müssen.

    api_url zeigt absichtlich auf einen toten Port, damit LLM-Calls scheitern
    und der Heuristik-Fallback getestet wird.
    """
    return ToolRouter(
        api_url="http://localhost:0",
        main_model_id="dummy-main",
        vision_model_id=None,
        thinking_model_id=None,
    )


def test_run_tool_echo_and_uppercase(router: ToolRouter) -> None:
    echo_payload = {"foo": "bar", "nested": {"x": 1}}
    echo_result = router.run_tool("echo", echo_payload)
    assert echo_result["ok"] is True
    assert echo_result["tool"] == "echo"
    assert echo_result["result"] == echo_payload

    up_result = router.run_tool("uppercase", {"text": "abc"})
    assert up_result["ok"] is True
    assert up_result["tool"] == "uppercase"
    assert up_result["result"] == "ABC"


def test_tool_select_heuristic_fallback(router: ToolRouter) -> None:
    candidates = router.select_tools(
        step_description="Konvertiere einen Text in Großbuchstaben und gib ihn zurück.",
        context={"test": True},
    )

    # Es sollte mindestens ein Tool vorgeschlagen werden
    assert isinstance(candidates, list)
    assert len(candidates) >= 1

    # Uppercase sollte als möglicher Kandidat dabei sein
    names = [c["name"] for c in candidates]
    assert "uppercase" in names


def main() -> None:
    router = _make_router()

    print("================================================================================")
    print("Tool-Autodetect Test")
    print("================================================================================")

    # 1) Echo & Uppercase
    print("\n[1] run_tool: echo & uppercase …")
    test_run_tool_echo_and_uppercase(router)
    print("[OK] Echo & Uppercase")

    # 2) Tool-Selection (Heuristik-Fallback, da LLM-Call fehlschlägt)
    print("\n[2] select_tools: Heuristik-Fallback …")
    test_tool_select_heuristic_fallback(router)
    print("[OK] Tool-Selection (Heuristik-Fallback)")

    print("\n================================================================================")
    print("Tool-Autodetect: ALLE CHECKS OK")
    print("================================================================================")


if __name__ == "__main__":
    main()
