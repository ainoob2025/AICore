import sys
from pathlib import Path

# Projekt-Root eintragen (damit "core" als Modul gefunden wird)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.rag.rag_service import RagService


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


def test_rag_basic_flow() -> None:
    """
    Kleiner Unit-Test für den RagService:
    - Neues Dokument für einen Test-User anlegen
    - Eine Query absetzen
    - Prüfen, dass mindestens ein Treffer zurückkommt und
      dass unser Test-Dokument darunter ist.
    """
    service = RagService()

    user_id = "test-user-rag"
    text = "Dies ist ein Testdokument über KI und RAG im AI Core."
    metadata = {"source": "test_rag", "kind": "test"}

    doc = service.ingest(user_id=user_id, document_text=text, metadata=metadata)

    results = service.query(
        user_id=user_id,
        query_text="Was weißt du über RAG im AI Core?",
        top_k=5,
        filters={"source": "test_rag"},
    )

    assert isinstance(results, list), "Erwartet: results ist eine Liste"
    assert len(results) >= 1, "Es sollte mindestens einen Treffer geben"

    ids = [r.get("id") for r in results]
    assert doc["id"] in ids, "Das gerade ingestierte Dokument sollte unter den Treffern sein"

    print("[OK] RAG Basic Flow (ingest + query)")


def main() -> None:
    print_section("RAG-Service Test")
    try:
        test_rag_basic_flow()
    except AssertionError as e:
        print(f"[FAIL] {e}")
        raise
    print("\nRAG-Test: ALLE CHECKS OK")


if __name__ == "__main__":
    main()