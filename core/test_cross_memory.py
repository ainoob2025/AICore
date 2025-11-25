import sys
from pathlib import Path

# Projekt-Root eintragen (damit "core" als Modul gefunden wird)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.memory.semantic_memory import SemanticMemory
from core.rag.rag_service import RagService
from core.graph.graph_engine import GraphEngine
from core.memory.cross_memory_search import CrossMemorySearch


def test_cross_memory_basic_flow() -> None:
    user_id = "cross-memory-test-user"

    # init components
    semantic = SemanticMemory()
    rag = RagService()
    graph = GraphEngine()

    # semantic knowledge
    semantic.add_knowledge(
        user_id=user_id,
        content="AI Core ist Saschas lokales KI Betriebssystem.",
        source="test_cross_memory",
        tags=["project", "aicore"],
        metadata={"kind": "semantic_test"},
    )

    # rag document
    rag.ingest(
        user_id=user_id,
        document_text="Dies ist ein Testdokument ueber AI Core und seinen RAG Layer.",
        metadata={"kind": "rag_test"},
    )

    # graph fact
    graph.add_fact(
        subject_label="Sascha",
        relation="works_on",
        object_label="AI Core",
        source="test_cross_memory",
        metadata={"kind": "graph_test"},
    )

    cross = CrossMemorySearch(
        episodic=None,
        semantic=semantic,
        rag_service=rag,
        graph_engine=graph,
    )

    results = cross.cross_search(
        user_id=user_id,
        query="AI Core",
        scopes=["semantic", "rag", "graph"],
        top_k=10,
    )

    assert isinstance(results, list)
    assert len(results) >= 3

    sources = {r.source for r in results}
    assert "semantic" in sources
    assert "rag" in sources
    assert "graph" in sources


def main() -> None:
    print("================================================================================")
    print("Cross-Memory Test")
    print("================================================================================")

    test_cross_memory_basic_flow()
    print("[OK] Cross-Memory Basic Flow (semantic + rag + graph)")

    print("\n================================================================================")
    print("Cross-Memory Test: ALLE CHECKS OK")
    print("================================================================================")


if __name__ == "__main__":
    main()