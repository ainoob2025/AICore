import sys
from pathlib import Path

# Projekt-Root eintragen (damit "core" als Modul gefunden wird)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.graph.graph_engine import GraphEngine


def test_graph_basic_flow() -> None:
    engine = GraphEngine()

    # Basis-Fakt hinzufügen
    result = engine.add_fact(
        subject_label="Sascha",
        relation="works_on",
        object_label="AI Core",
        source="test_graph_engine",
        metadata={"importance": "high"},
    )
    assert "subject_id" in result
    assert "object_id" in result
    assert "edge_id" in result

    # Related Query
    related = engine.query_related(label="Sascha", relation="works_on", max_depth=1, top_k=10)
    assert isinstance(related, list)
    assert len(related) >= 1

    entry = related[0]
    assert entry["relation"] == "works_on"
    assert entry["node"]["label"] == "AI Core"


def main() -> None:
    print("================================================================================")
    print("GraphEngine Test")
    print("================================================================================")

    test_graph_basic_flow()
    print("[OK] Graph Basic Flow (add_fact + query_related)")

    print("\n================================================================================")
    print("GraphEngine Test: ALLE CHECKS OK")
    print("================================================================================")


if __name__ == "__main__":
    main()