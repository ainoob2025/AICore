import sys
import json
from pathlib import Path

# Projekt-Root eintragen (damit "core" als Modul gefunden wird)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tools.tool_router import ToolRouter


def _make_router() -> ToolRouter:
    """
    Erstellt einen ToolRouter mit Dummy-API-URL, damit keine echten
    LM-Studio-Requests notwendig sind.
    """
    return ToolRouter(
        api_url="http://localhost:0",
        main_model_id="dummy-main",
        vision_model_id=None,
        thinking_model_id=None,
    )


def test_browser_tools(router: ToolRouter) -> None:
    """
    Testet browser_get + browser_extract.
    ACHTUNG: benötigt Internetzugriff auf https://example.com.
    """
    print("\n[Phase 7] Browser-Tools …")

    res_get = router.run_tool("browser_get", {"url": "https://example.com"})
    print("browser_get result:", json.dumps(res_get, ensure_ascii=False)[:300])

    assert isinstance(res_get, dict)
    assert res_get.get("tool") == "browser_get"

    # Nur weiter prüfen, wenn der Request erfolgreich war
    if res_get.get("ok"):
        result = res_get.get("result") or {}
        text = result.get("text", "")
        assert isinstance(text, str)
        assert len(text) > 0

        res_extract = router.run_tool(
            "browser_extract", {"text": text, "query": "Example"}
        )
        print("browser_extract result:", json.dumps(res_extract, ensure_ascii=False)[:300])

        assert res_extract.get("ok") is True
        extract_result = res_extract.get("result") or {}
        assert "snippet" in extract_result


def test_shell_run(router: ToolRouter) -> None:
    """
    Testet shell_run im Sandbox-Verzeichnis.
    Nutzt einen Whitelist-Befehl: echo.
    """
    print("\n[Phase 7] shell_run …")

    res = router.run_tool("shell_run", {"command": "echo phase7"})
    print("shell_run result:", json.dumps(res, ensure_ascii=False)[:300])

    assert res.get("ok") is True
    result = res.get("result") or {}
    stdout = result.get("stdout", "")
    assert "phase7" in stdout


def test_file_tools(router: ToolRouter) -> None:
    """
    Testet file_write, file_read, file_list und file_summary.
    Arbeitet unterhalb von data/files.
    """
    print("\n[Phase 7] File-Tools …")

    # Basis-Pfade
    files_root = ROOT_DIR / "data" / "files"
    test_rel_path = "phase7/test_file.txt"
    test_abs_path = files_root / test_rel_path

    # 1) file_write
    res_write = router.run_tool(
        "file_write",
        {
            "path": test_rel_path,
            "content": "Hallo Phase 7!\nDies ist ein Test für file_write/file_read.",
        },
    )
    print("file_write result:", json.dumps(res_write, ensure_ascii=False)[:300])

    assert res_write.get("ok") is True
    assert test_abs_path.is_file()

    # 2) file_read
    res_read = router.run_tool("file_read", {"path": test_rel_path})
    print("file_read result:", json.dumps(res_read, ensure_ascii=False)[:300])

    assert res_read.get("ok") is True
    read_result = res_read.get("result") or {}
    assert "content" in read_result
    assert "Hallo Phase 7" in read_result.get("content", "")

    # 3) file_list
    res_list = router.run_tool("file_list", {"path": "phase7"})
    print("file_list result:", json.dumps(res_list, ensure_ascii=False)[:300])

    assert res_list.get("ok") is True
    list_result = res_list.get("result") or {}
    entries = list_result.get("entries") or []
    assert any(e.get("name") == "test_file.txt" for e in entries)

    # 4) file_summary
    res_summary = router.run_tool("file_summary", {"path": test_rel_path})
    print("file_summary result:", json.dumps(res_summary, ensure_ascii=False)[:300])

    assert res_summary.get("ok") is True
    summary = res_summary.get("result") or {}
    assert summary.get("num_chars", 0) > 0
    assert "preview" in summary


def test_audio_tools(router: ToolRouter) -> None:
    """
    Testet speech_to_text und text_to_speech (Stub-Implementierungen).
    """
    print("\n[Phase 7] Audio-Tools …")

    audio_in_root = ROOT_DIR / "data" / "audio"
    audio_out_root = ROOT_DIR / "data" / "audio_out"

    audio_in_root.mkdir(parents=True, exist_ok=True)
    audio_out_root.mkdir(parents=True, exist_ok=True)

    # 1) Dummy-"Audio"-Input (Textdatei)
    input_rel = "phase7_input.txt"
    input_abs = audio_in_root / input_rel
    input_abs.write_text("Dies ist ein Dummy-Audio-Transkript.", encoding="utf-8")

    res_stt = router.run_tool("speech_to_text", {"path": input_rel})
    print("speech_to_text result:", json.dumps(res_stt, ensure_ascii=False)[:300])

    assert res_stt.get("ok") is True
    stt_result = res_stt.get("result") or {}
    transcript = stt_result.get("transcript", "")
    assert "Dummy-Audio-Transkript" in transcript

    # 2) text_to_speech -> schreibt Text nach data/audio_out
    output_name = "phase7_tts.txt"
    output_abs = audio_out_root / output_name

    res_tts = router.run_tool(
        "text_to_speech",
        {"text": "Phase 7 Text-to-Speech Test.", "output_name": output_name},
    )
    print("text_to_speech result:", json.dumps(res_tts, ensure_ascii=False)[:300])

    assert res_tts.get("ok") is True
    assert output_abs.is_file()
    content = output_abs.read_text(encoding="utf-8")
    assert "Phase 7 Text-to-Speech Test." in content


def main() -> None:
    router = _make_router()

    print("================================================================================")
    print("Phase 7 – Tool-Ökosystem Test")
    print("================================================================================")

    test_browser_tools(router)
    test_shell_run(router)
    test_file_tools(router)
    test_audio_tools(router)

    print("\n================================================================================")
    print("Phase 7: ALLE CHECKS OK (sofern keine Netzwerkprobleme beim Browser-Test).")
    print("================================================================================")


if __name__ == "__main__":
    main()