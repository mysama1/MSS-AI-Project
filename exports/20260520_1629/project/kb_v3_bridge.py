"""
MSS KB-V3 Bridge
Connects kb_loader graph data to SymbolicEngineV3
"""

import os
import json
from typing import Optional
from kb_loader import KBLoader, load_default_kb
from symbolic_engine import RelationEdge, RelationType
from symbolic_engine_v3 import SymbolicEngineV3, MSSKnowledgeGraph


class KBV3Bridge:
    """Bridge between kb_loader and SymbolicEngineV3"""
    
    def __init__(self):
        self.loader = KBLoader()
        self.engine: Optional[SymbolicEngineV3] = None
    
    def load_kb_to_v3(self, engine: Optional[SymbolicEngineV3] = None) -> SymbolicEngineV3:
        """Load knowledge base into SymbolicEngineV3"""
        # Load all KB entries
        count = self.loader.load_all()
        print(f"KB Loader: {count} entries loaded")
        
        # Build graph from KB
        kb_graph = self.loader.to_graph()
        print(f"KB Graph: {kb_graph.stats()}")
        
        # Load L1 IMPLIES completion edges
        completion_file = r"C:\MSS-AI-Project\knowledge_base\l1_implies_completion.jsonl"
        if os.path.exists(completion_file):
            added = 0
            with open(completion_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        edge = RelationEdge(
                            source=data['source'],
                            target=data['target'],
                            relation=RelationType.IMPLIES,
                            strength=data.get('strength', 0.7),
                            evidence=data.get('evidence', 'completion')
                        )
                        kb_graph.edges.append(edge)
                        if edge.source not in kb_graph._adjacency:
                            kb_graph._adjacency[edge.source] = []
                        kb_graph._adjacency[edge.source].append(edge)
                        added += 1
                    except Exception as e:
                        print(f"Warning: failed to load completion edge: {e}")
            print(f"L1 IMPLIES completion: {added} edges added")
        
        # Create or use existing engine
        if engine is None:
            engine = SymbolicEngineV3()
        
        # Merge KB graph into engine's graph
        self._merge_graphs(engine.graph, kb_graph)
        
        # Rebuild transitive reasoner with merged graph
        from symbolic_engine_v3 import TransitiveReasoner
        engine.transitive_reasoner = TransitiveReasoner(engine.graph)
        
        self.engine = engine
        print(f"V3 Engine: {len(engine.graph.nodes)} nodes, {len(engine.graph.edges)} edges")
        
        return engine
    
    def _merge_graphs(self, target: MSSKnowledgeGraph, source: MSSKnowledgeGraph):
        """Merge source graph into target graph"""
        # Add all nodes from source
        for node_id, node in source.nodes.items():
            if node_id not in target.nodes:
                target.nodes[node_id] = node
        
        # Add all edges from source
        for edge in source.edges:
            # Check if edge already exists
            exists = False
            for existing in target.edges:
                if (existing.source == edge.source and 
                    existing.target == edge.target and
                    existing.relation == edge.relation):
                    exists = True
                    break
            if not exists:
                target.edges.append(edge)
                # Update adjacency
                if edge.source not in target._adjacency:
                    target._adjacency[edge.source] = []
                target._adjacency[edge.source].append(edge)
    
    def query_l1_to_l2_path(self, l1_node_id: str, l2_node_id: str):
        """Query path from L1 to L2 using transitive reasoning"""
        if self.engine is None:
            raise RuntimeError("Engine not loaded. Call load_kb_to_v3() first.")
        
        result = self.engine.reason(l1_node_id, l2_node_id)
        return {
            "result": result.result.name,
            "certainty": result.certainty,
            "explanation": result.explanation,
            "steps": len(result.steps)
        }
    
    def get_l1_axioms(self):
        """Get all L1 axioms from loaded KB"""
        if self.engine is None:
            return []
        return [
            node for node in self.engine.graph.nodes.values()
            if node.layer == "L1"
        ]
    
    def get_l2_theorems(self):
        """Get all L2 theorems from loaded KB"""
        if self.engine is None:
            return []
        return [
            node for node in self.engine.graph.nodes.values()
            if node.layer == "L2"
        ]


def create_integrated_engine() -> SymbolicEngineV3:
    """Create a fully integrated engine with KB data"""
    bridge = KBV3Bridge()
    return bridge.load_kb_to_v3()


if __name__ == "__main__":
    print("=" * 60)
    print("MSS KB-V3 Bridge Demo")
    print("=" * 60)
    
    engine = create_integrated_engine()
    
    # Show L1 axioms
    l1_axioms = [n for n in engine.graph.nodes.values() if n.layer == "L1"]
    print(f"\nL1 Axioms ({len(l1_axioms)}):")
    for axiom in l1_axioms[:5]:
        print(f"  - {axiom.id}: {axiom.name}")
    
    # Show L2 theorems
    l2_theorems = [n for n in engine.graph.nodes.values() if n.layer == "L2"]
    print(f"\nL2 Theorems ({len(l2_theorems)}):")
    for theorem in l2_theorems[:5]:
        print(f"  - {theorem.id}: {theorem.name}")
    
    # Test transitive reasoning
    if l1_axioms and l2_theorems:
        test_axiom = l1_axioms[0]
        test_theorem = l2_theorems[0]
        print(f"\nTesting: {test_axiom.id} → {test_theorem.id}")
        result = engine.reason(test_axiom.id, test_theorem.id)
        print(f"  Result: {result.result.name} (certainty: {result.certainty:.2%})")
        print(f"  Explanation: {result.explanation[:100]}...")
