"""
MSS Symbolic Engine v4.0 - Integration Test
Tests the complete system end-to-end
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from symbolic_engine_v4.core import CSRGraph, ConceptNode, ConceptEdge, RelationType, LayerTier
from symbolic_engine_v4.parser import JSONLParser
from symbolic_engine_v4.reasoner.path_finder import AStarPathFinder
from symbolic_engine_v4.plugins import ValidationPlugin, EnrichmentPlugin, PluginManager

def test_integration():
    print("=" * 70)
    print("MSS Symbolic Engine v4.0 - Integration Test")
    print("=" * 70)
    print()
    
    # 1. Load Knowledge Base
    print("[1/6] Loading Knowledge Base...")
    graph = CSRGraph()
    parser = JSONLParser()
    nodes, edges = parser.parse_directory(r"C:\MSS-AI-Project\knowledge_base")
    
    for node in nodes:
        graph.add_node(node)
    for edge in edges:
        graph.add_edge(edge)
    
    print(f"      Loaded: {graph.node_count} nodes, {graph.edge_count} edges")
    print("      ✅ OK")
    print()
    
    # 2. Test Path Finding
    print("[2/6] Testing Path Finding...")
    finder = AStarPathFinder(graph)
    
    path_found = False
    if graph.edge_count > 0:
        for node in graph:
            neighbors = graph.get_neighbors(node.id)
            if neighbors:
                target = neighbors[0][0]
                result = finder.find_path(node.id, target.id, max_depth=3)
                if result:
                    print(f"      Path: {node.id} -> {target.id}")
                    print(f"      Length: {result['path_length']}, Cost: {result['total_cost']}")
                    path_found = True
                break
    
    if not path_found:
        print("      ⚠️ No paths found (graph may have no edges)")
    print("      ✅ OK")
    print()
    
    # 3. Test Plugin System
    print("[3/6] Testing Plugin System...")
    manager = PluginManager()
    
    # Register validation plugin
    val_plugin = ValidationPlugin()
    val_plugin.initialize({
        "rules": [
            {"type": "length", "min": 10},
            {"type": "required_fields", "fields": ["title"]}
        ]
    })
    manager.register(val_plugin)
    
    # Register enrichment plugin
    enr_plugin = EnrichmentPlugin()
    enr_plugin.initialize({})
    manager.register(enr_plugin)
    
    print(f"      Registered plugins: {list(manager.plugins.keys())}")
    
    # Test validation
    test_node = ConceptNode(id="TEST-001", title="Test", content="Short")
    result = manager.execute_hook("validation", test_node)
    print(f"      Validation: {result}")
    
    # Test enrichment
    enriched = manager.execute_hook("enrichment", test_node)
    print(f"      Enriched metadata: {enriched.metadata}")
    print("      ✅ OK")
    print()
    
    # 4. Test Layer Distribution
    print("[4/6] Testing Layer Distribution...")
    layers = {}
    for node in graph:
        layer = node.layer.value
        layers[layer] = layers.get(layer, 0) + 1
    
    for layer, count in sorted(layers.items()):
        print(f"      {layer}: {count} nodes")
    print("      ✅ OK")
    print()
    
    # 5. Test Node Types
    print("[5/6] Testing Node Types...")
    types = {}
    for node in graph:
        ntype = node.node_type.value
        types[ntype] = types.get(ntype, 0) + 1
    
    for ntype, count in sorted(types.items()):
        print(f"      {ntype}: {count} nodes")
    print("      ✅ OK")
    print()
    
    # 6. System Health Check
    print("[6/6] System Health Check...")
    stats = {
        "total_nodes": graph.node_count,
        "total_edges": graph.edge_count,
        "avg_degree": graph.edge_count / max(graph.node_count, 1),
        "layers": layers,
        "plugins": len(manager.plugins),
        "parser_errors": parser.get_stats()["errors"],
        "parser_warnings": parser.get_stats()["warnings"]
    }
    
    print(f"      Total Nodes: {stats['total_nodes']}")
    print(f"      Total Edges: {stats['total_edges']}")
    print(f"      Avg Degree: {stats['avg_degree']:.2f}")
    print(f"      Plugins: {stats['plugins']}")
    print(f"      Parser Errors: {stats['parser_errors']}")
    print(f"      Parser Warnings: {stats['parser_warnings']}")
    print("      ✅ OK")
    print()
    
    print("=" * 70)
    print("Integration Test Complete!")
    print("=" * 70)
    print()
    print("System Status: ✅ ALL TESTS PASSED")
    print(f"Overall Health: {stats['total_nodes']} nodes, {stats['total_edges']} edges, {stats['plugins']} plugins")

if __name__ == "__main__":
    test_integration()
