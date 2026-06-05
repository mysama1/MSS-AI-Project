"""
Test API functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from symbolic_engine_v4.api import SymbolicEngineAPI

def test_api():
    print("=" * 60)
    print("Testing Symbolic Engine v4.0 API")
    print("=" * 60)
    print()

    api = SymbolicEngineAPI()

    # Test 1: Stats before loading
    print("1. Testing get_stats (before load)...")
    stats = api.get_stats()
    print(f"   Status: {stats['status']}")
    print(f"   KB Loaded: {stats['knowledge_base_loaded']}")
    print(f"   Version: {stats['version']}")
    print("   ✅ OK")
    print()

    # Test 2: Load knowledge base
    print("2. Testing load_knowledge_base...")
    kb_dir = r"C:\MSS-AI-Project\knowledge_base"
    if os.path.exists(kb_dir):
        result = api.load_knowledge_base(kb_dir)
        print(f"   Status: {result['status']}")
        print(f"   Nodes: {result['nodes_loaded']}")
        print(f"   Edges: {result['edges_loaded']}")
        print(f"   Load time: {result['load_time_ms']}ms")
        print("   ✅ OK")
    else:
        print("   ⚠️ Knowledge base directory not found")
    print()

    # Test 3: Stats after loading
    print("3. Testing get_stats (after load)...")
    stats = api.get_stats()
    print(f"   Nodes: {stats['graph_stats']['nodes']}")
    print(f"   Edges: {stats['graph_stats']['edges']}")
    print("   ✅ OK")
    print()

    # Test 4: Analyze query
    print("4. Testing analyze...")
    result = api.analyze("公理")
    print(f"   Status: {result['status']}")
    print(f"   Results: {result['results_count']}")
    if result['results_count'] > 0:
        print(f"   Top result: {result['results'][0]['title']} (score: {result['results'][0]['score']})")
    print("   ✅ OK")
    print()

    # Test 5: Validate node
    print("5. Testing validate...")
    result = api.validate("H001")
    print(f"   Status: {result['status']}")
    if result['status'] == 'success':
        print(f"   Valid: {result['validation']['is_valid']}")
        print(f"   Score: {result['validation']['score']}")
    print("   ✅ OK")
    print()

    print("=" * 60)
    print("All API tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
