"""
MSS Symbolic Reasoning Engine v2.0
Enhanced graph algorithms and layer-aware reasoning
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum, auto
from collections import defaultdict, deque
import heapq

from symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType, InferencePath, InferenceResult
)


@dataclass
class PathScore:
    """Scored path for ranking"""
    path: List[Tuple[str, RelationType, str]]
    score: float
    length: int
    layers_crossed: Set[str]


class GraphAlgorithms:
    """
    Advanced graph algorithms for MSS knowledge graph
    
    All algorithms are deterministic - no LLM involved
    """
    
    def __init__(self, graph: MSSKnowledgeGraph):
        self.graph = graph
    
    def shortest_path(
        self,
        start: str,
        end: str,
        max_depth: int = 10,
        avoid_layers: Optional[Set[str]] = None
    ) -> Optional[InferencePath]:
        """
        Dijkstra-like shortest path with layer constraints
        
        Prefers paths that stay within lower layers (L1 -> L2 -> L3)
        """
        if start not in self.graph.nodes or end not in self.graph.nodes:
            return None
        
        avoid_layers = avoid_layers or set()
        
        # Priority queue: (cost, node_id, path)
        # Cost: path length + layer penalty
        queue = [(0, start, [])]
        visited = {start: 0}
        
        while queue:
            cost, current, path = heapq.heappop(queue)
            
            if current == end and path:
                return InferencePath(
                    steps=path,
                    result=InferenceResult.PROVEN,
                    certainty=self._calculate_certainty(path),
                    explanation=f"Shortest path found ({len(path)} steps)"
                )
            
            if len(path) >= max_depth:
                continue
            
            for edge in self.graph._adjacency.get(current, []):
                target = edge.target
                target_node = self.graph.nodes.get(target)
                
                # Skip if target layer is avoided
                if target_node and target_node.layer in avoid_layers:
                    continue
                
                # Calculate step cost
                layer_penalty = self._layer_penalty(
                    self.graph.nodes[current].layer if current in self.graph.nodes else "L3",
                    target_node.layer if target_node else "L3"
                )
                step_cost = 1 + layer_penalty + (1 - edge.strength)
                new_cost = cost + step_cost
                
                if target not in visited or new_cost < visited[target]:
                    visited[target] = new_cost
                    new_path = path + [(current, edge.relation, target)]
                    heapq.heappush(queue, (new_cost, target, new_path))
        
        return InferencePath(
            steps=[],
            result=InferenceResult.UNDETERMINED,
            certainty=0.0,
            explanation=f"No path found within {max_depth} steps"
        )
    
    def _layer_penalty(self, from_layer: str, to_layer: str) -> float:
        """Penalty for crossing layers in wrong direction"""
        layer_order = {"L1": 1, "L2": 2, "L3": 3}
        from_val = layer_order.get(from_layer, 3)
        to_val = layer_order.get(to_layer, 3)
        
        # Prefer upward (L1 -> L2 -> L3) or same layer
        if to_val >= from_val:
            return 0.0
        # Penalize downward jumps (L3 -> L1)
        else:
            return (from_val - to_val) * 2.0
    
    def _calculate_certainty(self, path: List[Tuple]) -> float:
        """Calculate path certainty from edge strengths"""
        if not path:
            return 0.0
        
        # Find edges in path
        certainties = []
        for frm, rel, to in path:
            for edge in self.graph._adjacency.get(frm, []):
                if edge.target == to and edge.relation == rel:
                    certainties.append(edge.strength)
                    break
        
        if not certainties:
            return 0.5
        
        # Combined certainty (product of edge strengths)
        result = 1.0
        for c in certainties:
            result *= c
        return result
    
    def centrality(self, node_id: str) -> Dict[str, float]:
        """
        Calculate centrality metrics for a node
        
        Returns:
            degree: Number of connections
            betweenness: How often node is on shortest paths
            layer_authority: Authority based on layer (L1 highest)
        """
        if node_id not in self.graph.nodes:
            return {"degree": 0, "betweenness": 0, "layer_authority": 0}
        
        node = self.graph.nodes[node_id]
        
        # Degree centrality
        out_degree = len(self.graph._adjacency.get(node_id, []))
        in_degree = sum(
            1 for edge in self.graph.edges
            if edge.target == node_id
        )
        degree = out_degree + in_degree
        
        # Layer authority
        layer_weights = {"L1": 1.0, "L2": 0.7, "L3": 0.4}
        layer_authority = layer_weights.get(node.layer, 0.3)
        
        # Simple betweenness approximation
        betweenness = self._approximate_betweenness(node_id)
        
        return {
            "degree": degree,
            "in_degree": in_degree,
            "out_degree": out_degree,
            "betweenness": betweenness,
            "layer_authority": layer_authority,
            "combined_score": degree * layer_authority + betweenness
        }
    
    def _approximate_betweenness(self, node_id: str, sample_size: int = 20) -> float:
        """Approximate betweenness centrality by sampling"""
        nodes = list(self.graph.nodes.keys())
        if len(nodes) < 3 or node_id not in nodes:
            return 0.0
        
        import random
        random.seed(42)  # Deterministic
        
        count = 0
        total = 0
        
        # Sample random pairs
        samples = min(sample_size, len(nodes) * (len(nodes) - 1) // 2)
        for _ in range(samples):
            a, b = random.sample(nodes, 2)
            if a == node_id or b == node_id:
                continue
            
            path = self.shortest_path(a, b, max_depth=5)
            if path and path.result == InferenceResult.PROVEN:
                total += 1
                # Check if node_id is in path
                for frm, rel, to in path.steps:
                    if frm == node_id or to == node_id:
                        count += 1
                        break
        
        return count / max(total, 1)
    
    def find_cycles(self, max_length: int = 5) -> List[List[str]]:
        """
        Find cycles in the graph (circular reasoning detection)
        
        Returns list of node ID cycles
        """
        cycles = []
        visited = set()
        
        def dfs(node_id: str, path: List[str], start: str):
            if len(path) > max_length:
                return
            
            for edge in self.graph._adjacency.get(node_id, []):
                next_id = edge.target
                
                if next_id == start and len(path) > 1:
                    # Found cycle
                    cycle = path + [next_id]
                    # Normalize cycle (rotate to smallest element)
                    min_idx = cycle.index(min(cycle))
                    normalized = cycle[min_idx:] + cycle[1:min_idx+1]
                    if normalized not in cycles:
                        cycles.append(normalized)
                elif next_id not in path and next_id not in visited:
                    dfs(next_id, path + [next_id], start)
        
        for node_id in self.graph.nodes:
            visited.clear()
            dfs(node_id, [node_id], node_id)
        
        return cycles
    
    def connected_components(self) -> List[Set[str]]:
        """Find connected components in the graph"""
        visited = set()
        components = []
        
        def bfs(start: str) -> Set[str]:
            component = {start}
            queue = deque([start])
            visited.add(start)
            
            while queue:
                current = queue.popleft()
                for edge in self.graph._adjacency.get(current, []):
                    if edge.target not in visited:
                        visited.add(edge.target)
                        component.add(edge.target)
                        queue.append(edge.target)
                # Also check reverse edges
                for edge in self.graph.edges:
                    if edge.target == current and edge.source not in visited:
                        visited.add(edge.source)
                        component.add(edge.source)
                        queue.append(edge.source)
            
            return component
        
        for node_id in self.graph.nodes:
            if node_id not in visited:
                component = bfs(node_id)
                components.append(component)
        
        return components
    
    def layer_analysis(self) -> Dict[str, Any]:
        """Analyze layer structure and dependencies"""
        result = {
            "layer_counts": {},
            "cross_layer_edges": 0,
            "layer_isolation": {},
            "upward_flow": 0,
            "downward_flow": 0,
        }
        
        layer_order = {"L1": 1, "L2": 2, "L3": 3}
        
        # Count nodes per layer
        for node in self.graph.nodes.values():
            result["layer_counts"][node.layer] = result["layer_counts"].get(node.layer, 0) + 1
        
        # Analyze edges
        for edge in self.graph.edges:
            source_node = self.graph.nodes.get(edge.source)
            target_node = self.graph.nodes.get(edge.target)
            
            if source_node and target_node:
                if source_node.layer != target_node.layer:
                    result["cross_layer_edges"] += 1
                    
                    source_val = layer_order.get(source_node.layer, 3)
                    target_val = layer_order.get(target_node.layer, 3)
                    
                    if target_val > source_val:
                        result["upward_flow"] += 1
                    elif target_val < source_val:
                        result["downward_flow"] += 1
        
        # Calculate isolation (ratio of internal vs cross-layer edges)
        for layer in ["L1", "L2", "L3"]:
            internal = 0
            external = 0
            for edge in self.graph.edges:
                source = self.graph.nodes.get(edge.source)
                target = self.graph.nodes.get(edge.target)
                if source and target:
                    if source.layer == layer and target.layer == layer:
                        internal += 1
                    elif source.layer == layer or target.layer == layer:
                        external += 1
            total = internal + external
            result["layer_isolation"][layer] = internal / max(total, 1)
        
        return result


class LayerAwareReasoner:
    """
    Reasoning engine that respects MSS layer hierarchy
    
    L1: Hard constraints - cannot be violated
    L2: Theories - can be refined but not contradicted by L3
    L3: Heuristics - can be overridden
    """
    
    def __init__(self, graph: MSSKnowledgeGraph):
        self.graph = graph
        self.algorithms = GraphAlgorithms(graph)
    
    def verify_with_hierarchy(
        self,
        claim_nodes: List[str],
        claim_layer: str
    ) -> InferencePath:
        """
        Verify claim respecting layer hierarchy
        
        Rules:
        - L3 claim cannot contradict L1/L2
        - L2 claim cannot contradict L1
        - L1 claim is always valid (within L1)
        """
        layer_priority = {"L1": 3, "L2": 2, "L3": 1}
        claim_priority = layer_priority.get(claim_layer, 0)
        
        # Check for contradictions with higher layers
        for node_id in claim_nodes:
            node = self.graph.nodes.get(node_id)
            if not node:
                continue
            
            node_priority = layer_priority.get(node.layer, 0)
            
            # Check if this node contradicts any higher-layer node
            for other_id, other_node in self.graph.nodes.items():
                if other_id == node_id:
                    continue
                
                other_priority = layer_priority.get(other_node.layer, 0)
                
                # Only check if other is higher priority
                if other_priority > node_priority:
                    contradiction = self.graph.check_contradiction(node_id, other_id)
                    if contradiction.result == InferenceResult.DISPROVEN:
                        return InferencePath(
                            steps=contradiction.steps,
                            result=InferenceResult.DISPROVEN,
                            certainty=contradiction.certainty,
                            explanation=f"Layer violation: {node_id}({node.layer}) contradicts {other_id}({other_node.layer})"
                        )
        
        # Check internal consistency
        for i, a in enumerate(claim_nodes):
            for b in claim_nodes[i+1:]:
                contradiction = self.graph.check_contradiction(a, b)
                if contradiction.result == InferenceResult.DISPROVEN:
                    return InferencePath(
                        steps=contradiction.steps,
                        result=InferenceResult.DISPROVEN,
                        certainty=contradiction.certainty,
                        explanation=f"Internal contradiction: {a} vs {b}"
                    )
        
        return InferencePath(
            steps=[],
            result=InferenceResult.PROVEN,
            certainty=0.9,
            explanation=f"Claim consistent with layer hierarchy ({claim_layer})"
        )
    
    def find_support(
        self,
        node_id: str,
        max_depth: int = 3
    ) -> List[InferencePath]:
        """
        Find all supporting paths from L1 axioms to this node
        """
        if node_id not in self.graph.nodes:
            return []
        
        node = self.graph.nodes[node_id]
        results = []
        
        # Find all L1 axioms
        l1_nodes = [
            nid for nid, n in self.graph.nodes.items()
            if n.layer == "L1"
        ]
        
        # Find paths from each L1 axiom
        for axiom_id in l1_nodes:
            path = self.algorithms.shortest_path(axiom_id, node_id, max_depth)
            if path and path.result == InferenceResult.PROVEN:
                results.append(path)
        
        # Sort by certainty
        results.sort(key=lambda p: p.certainty, reverse=True)
        return results
    
    def get_layer_summary(self) -> Dict[str, List[Dict]]:
        """Get summary of all nodes organized by layer"""
        summary = {"L1": [], "L2": [], "L3": []}
        
        for node_id, node in self.graph.nodes.items():
            info = {
                "id": node_id,
                "name": node.name,
                "type": node.node_type.name,
                "confidence": node.confidence,
                "connections": len(self.graph._adjacency.get(node_id, [])),
            }
            
            if node.layer in summary:
                summary[node.layer].append(info)
        
        # Sort by confidence within each layer
        for layer in summary:
            summary[layer].sort(key=lambda x: x["confidence"], reverse=True)
        
        return summary


# Demo
if __name__ == "__main__":
    print("=" * 60)
    print("MSS Symbolic Engine v2.0 Demo")
    print("=" * 60)
    
    from symbolic_engine import MSSKnowledgeGraph, ConceptNode, RelationEdge, NodeType, RelationType
    
    # Create sample graph
    graph = MSSKnowledgeGraph()
    
    nodes = [
        ConceptNode("A1", "Information Ontology", NodeType.AXIOM, "L1",
                   "Information is fundamental", confidence=1.0),
        ConceptNode("A2", "0/1 Critical", NodeType.AXIOM, "L1",
                   "0/1 is phase transition", confidence=1.0),
        ConceptNode("T1", "BCT Coupling", NodeType.THEOREM, "L2",
                   "BCT theorem", confidence=0.9),
        ConceptNode("T2", "Resilience", NodeType.THEOREM, "L2",
                   "R = T/phi", confidence=0.85),
        ConceptNode("H1", "Redshift", NodeType.CONCEPT, "L3",
                   "Metaphor", confidence=0.7),
    ]
    
    for n in nodes:
        graph.add_node(n)
    
    edges = [
        RelationEdge("A1", "T1", RelationType.IMPLIES, 1.0),
        RelationEdge("A2", "T1", RelationType.IMPLIES, 0.9),
        RelationEdge("T1", "T2", RelationType.DERIVES_FROM, 0.8),
        RelationEdge("T2", "H1", RelationType.ANALOGOUS, 0.6),
    ]
    
    for e in edges:
        graph.add_edge(e)
    
    # Algorithms
    algo = GraphAlgorithms(graph)
    
    print("\n1. Shortest Path (A1 -> H1):")
    path = algo.shortest_path("A1", "H1")
    print(f"   {path.to_text()}")
    
    print("\n2. Centrality Analysis:")
    for nid in ["A1", "T1", "H1"]:
        c = algo.centrality(nid)
        print(f"   {nid}: degree={c['degree']}, authority={c['layer_authority']:.2f}")
    
    print("\n3. Layer Analysis:")
    layer_info = algo.layer_analysis()
    print(f"   {layer_info}")
    
    print("\n4. Layer-Aware Reasoner:")
    reasoner = LayerAwareReasoner(graph)
    
    print("\n   Verify L2 claim [T1, T2]:")
    result = reasoner.verify_with_hierarchy(["T1", "T2"], "L2")
    print(f"   Result: {result.result.name}")
    
    print("\n   Find support for T2:")
    supports = reasoner.find_support("T2")
    for sp in supports:
        print(f"   - {len(sp.steps)} steps, certainty={sp.certainty:.2f}")
    
    print("\n" + "=" * 60)
