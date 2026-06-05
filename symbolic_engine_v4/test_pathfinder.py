"""
Test A* Path Finder
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from symbolic_engine_v4.core import CSRGraph, ConceptNode, ConceptEdge, RelationType, LayerTier
from symbolic_engine_v4.parser import JSONLParser

def test_pathfinder():
    print("=" * 60)
    print("Testing A* Path Finder")
    print("=" * 60)
    print()

    # Load knowledge base
    graph = CSRGraph()
    parser = JSONLParser()

    kb_dir = r"C:\MSS-AI-Project\knowledge_base"
    nodes, edges = parser.parse_directory(kb_dir)

    for node in nodes:
        graph.add_node(node)

    for edge in edges:
        graph.add_edge(edge)

    print(f"Loaded {graph.node_count} nodes, {graph.edge_count} edges")
    print()

    # Test path finding (skip if no edges)
    if graph.edge_count == 0:
        print("⚠️ No edges in graph, skipping path tests")
        return

    # Import path finder
    from symbolic_engine_v4.reasoner.path_finder import AStarPathFinder

    finder = AStarPathFinder(graph)

    # Find some test paths
    test_pairs = [
        ("H001", "H010"),
        ("H020", "H030"),
    ]

    for start, end in test_pairs:
        if start in graph.nodes and end in graph.nodes:
            result = finder.find_path(start, end, max_depth=5)
            if result:
                print(f"Path {start} → {end}:")
                print(f"  Length: {result['path_length']}")
                print(f"  Cost: {result['total_cost']}")
                print(f"  Confidence: {result['confidence']}")
                print(f"  Nodes: {' → '.join(n['id'] for n in result['nodes'])}")
            else:
                print(f"No path found: {start} → {end}")
            print()

    print("=" * 60)
    print("Path finder test complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_pathfinder()
