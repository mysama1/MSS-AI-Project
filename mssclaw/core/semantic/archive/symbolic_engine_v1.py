"""
MSS Symbolic Reasoning Engine
确定性符号推理层 - 不依赖LLM的可解释推理

Core concept:
- Knowledge as a graph (not embeddings)
- Reasoning as graph traversal (not probability)
- Truth as topological invariants (not confidence scores)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum, auto
import json
import os

class NodeType(Enum):
    """MSS knowledge node types"""
    AXIOM = auto()        # L1: Immutable hard core
    THEOREM = auto()      # L2: Derived theory
    CONCEPT = auto()      # L3: Heuristic/metaphor
    PREDICTION = auto()   # Falsifiable prediction
    LEMMA = auto()        # Intermediate result

class RelationType(Enum):
    """MSS relation types between nodes"""
    IMPLIES = auto()          # A -> B (logical implication)
    CONTRADICTS = auto()      # A !~ B (logical contradiction)
    INSTANCE_OF = auto()      # A : B (category membership)
    DERIVES_FROM = auto()     # A <- B (derivation)
    ANALOGOUS = auto()        # A ~ B (analogy/metaphor)
    TESTS = auto()            # A ? B (prediction tests theory)
    REFINES = auto()          # A > B (refinement)

class InferenceResult(Enum):
    """Result of inference operation"""
    PROVEN = auto()           # Deterministically proven
    DISPROVEN = auto()        # Contradiction found
    UNDETERMINED = auto()     # Insufficient information
    CIRCULAR = auto()         # Circular reasoning detected
    OUT_OF_SCOPE = auto()     # Beyond symbolic capability

@dataclass
class ConceptNode:
    """A node in the MSS knowledge graph"""
    id: str
    name: str
    node_type: NodeType
    layer: str  # "L1", "L2", "L3"
    content: str
    confidence: float = 1.0  # For L1, always 1.0
    falsifiable: bool = False
    humility_clause: Optional[str] = None
    boundary_statement: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type.name,
            "layer": self.layer,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "confidence": self.confidence,
            "falsifiable": self.falsifiable,
        }

@dataclass
class RelationEdge:
    """An edge connecting two concept nodes"""
    source: str  # node id
    target: str  # node id
    relation: RelationType
    strength: float = 1.0  # 0.0 to 1.0
    evidence: Optional[str] = None
    bidirectional: bool = False

@dataclass
class InferencePath:
    """A path of reasoning from premise to conclusion"""
    steps: List[Tuple[str, RelationType, str]]  # (from, relation, to)
    result: InferenceResult
    certainty: float  # 0.0 to 1.0
    explanation: str

    def to_text(self) -> str:
        lines = [f"Inference Result: {self.result.name}"]
        lines.append(f"Certainty: {self.certainty:.2%}")
        lines.append(f"Explanation: {self.explanation}")
        if self.steps:
            lines.append("Path:")
            for i, (frm, rel, to) in enumerate(self.steps, 1):
                lines.append(f"  {i}. {frm} --[{rel.name}]--> {to}")
        return "\n".join(lines)

class MSSKnowledgeGraph:
    """
    Symbolic knowledge graph for MSS framework

    Loads from existing knowledge base entries and provides
    deterministic reasoning operations.
    """

    def __init__(self):
        self.nodes: Dict[str, ConceptNode] = {}
        self.edges: List[RelationEdge] = []
        self._index_by_type: Dict[NodeType, Set[str]] = {}
        self._index_by_layer: Dict[str, Set[str]] = {}
        self._adjacency: Dict[str, List[RelationEdge]] = {}

    def add_node(self, node: ConceptNode) -> None:
        """Add a concept node to the graph"""
        self.nodes[node.id] = node

        # Update indexes
        if node.node_type not in self._index_by_type:
            self._index_by_type[node.node_type] = set()
        self._index_by_type[node.node_type].add(node.id)

        if node.layer not in self._index_by_layer:
            self._index_by_layer[node.layer] = set()
        self._index_by_layer[node.layer].add(node.id)

        if node.id not in self._adjacency:
            self._adjacency[node.id] = []

    def add_edge(self, edge: RelationEdge) -> None:
        """Add a relation edge between nodes"""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Unknown node: {edge.source} or {edge.target}")

        self.edges.append(edge)
        self._adjacency[edge.source].append(edge)

        if edge.bidirectional:
            reverse = RelationEdge(
                source=edge.target,
                target=edge.source,
                relation=edge.relation,
                strength=edge.strength,
                evidence=edge.evidence,
                bidirectional=True
            )
            self.edges.append(reverse)
            self._adjacency[edge.target].append(reverse)

    def get_node(self, node_id: str) -> Optional[ConceptNode]:
        """Retrieve a node by ID"""
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str, relation_filter: Optional[RelationType] = None) -> List[ConceptNode]:
        """Get all nodes connected to given node"""
        if node_id not in self._adjacency:
            return []

        results = []
        for edge in self._adjacency[node_id]:
            if relation_filter is None or edge.relation == relation_filter:
                neighbor = self.nodes.get(edge.target)
                if neighbor:
                    results.append(neighbor)
        return results

    def find_path(self, start: str, end: str, max_depth: int = 5) -> Optional[InferencePath]:
        """
        Find reasoning path from start to end node
        Uses BFS for shortest path
        """
        if start not in self.nodes or end not in self.nodes:
            return None

        # BFS
        visited = {start}
        queue = [(start, [])]

        while queue:
            current, path = queue.pop(0)

            if current == end and path:
                return InferencePath(
                    steps=path,
                    result=InferenceResult.PROVEN,
                    certainty=1.0,
                    explanation=f"Path found from {start} to {end}"
                )

            if len(path) >= max_depth:
                continue

            for edge in self._adjacency.get(current, []):
                if edge.target not in visited:
                    visited.add(edge.target)
                    new_path = path + [(current, edge.relation, edge.target)]
                    queue.append((edge.target, new_path))

        return InferencePath(
            steps=[],
            result=InferenceResult.UNDETERMINED,
            certainty=0.0,
            explanation=f"No path found from {start} to {end} within {max_depth} steps"
        )

    def check_contradiction(self, node_a: str, node_b: str) -> InferencePath:
        """Check if two nodes contradict each other"""
        # Direct contradiction edge
        for edge in self._adjacency.get(node_a, []):
            if edge.target == node_b and edge.relation == RelationType.CONTRADICTS:
                return InferencePath(
                    steps=[(node_a, RelationType.CONTRADICTS, node_b)],
                    result=InferenceResult.DISPROVEN,
                    certainty=1.0,
                    explanation=f"Direct contradiction: {node_a} contradicts {node_b}"
                )

        # Check for indirect contradiction through implication chains
        # If A implies C and B contradicts C, then A and B are in tension
        neighbors_a = self.get_neighbors(node_a, RelationType.IMPLIES)
        for implied in neighbors_a:
            for edge in self._adjacency.get(node_b, []):
                if edge.target == implied.id and edge.relation == RelationType.CONTRADICTS:
                    return InferencePath(
                        steps=[
                            (node_a, RelationType.IMPLIES, implied.id),
                            (node_b, RelationType.CONTRADICTS, implied.id)
                        ],
                        result=InferenceResult.DISPROVEN,
                        certainty=0.8,
                        explanation=f"Indirect contradiction via {implied.id}"
                    )

        return InferencePath(
            steps=[],
            result=InferenceResult.UNDETERMINED,
            certainty=0.0,
            explanation="No contradiction detected"
        )

    def get_layer_contents(self, layer: str) -> List[ConceptNode]:
        """Get all nodes in a specific layer"""
        node_ids = self._index_by_layer.get(layer, set())
        return [self.nodes[nid] for nid in node_ids]

    def query(self, node_type: Optional[NodeType] = None,
              layer: Optional[str] = None,
              keyword: Optional[str] = None) -> List[ConceptNode]:
        """Query nodes by multiple criteria"""
        results = list(self.nodes.values())

        if node_type:
            type_ids = self._index_by_type.get(node_type, set())
            results = [n for n in results if n.id in type_ids]

        if layer:
            layer_ids = self._index_by_layer.get(layer, set())
            results = [n for n in results if n.id in layer_ids]

        if keyword:
            keyword_lower = keyword.lower()
            results = [n for n in results if
                      keyword_lower in n.name.lower() or
                      keyword_lower in n.content.lower()]

        return results

    def stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "by_type": {t.name: len(ids) for t, ids in self._index_by_type.items()},
            "by_layer": {l: len(ids) for l, ids in self._index_by_layer.items()},
            "avg_degree": sum(len(self._adjacency.get(nid, [])) for nid in self.nodes) / max(len(self.nodes), 1),
        }

class SymbolicReasoner:
    """
    High-level symbolic reasoning interface

    Provides user-friendly methods for common reasoning tasks
    without requiring LLM involvement.
    """

    def __init__(self, graph: Optional[MSSKnowledgeGraph] = None):
        self.graph = graph or MSSKnowledgeGraph()

    def load_from_knowledge_base(self, kb_dir: str = "knowledge_base") -> int:
        """
        Load knowledge from existing JSONL files
        Returns number of nodes loaded
        """
        count = 0
        kb_path = os.path.join(os.path.dirname(__file__), kb_dir)

        if not os.path.exists(kb_path):
            print(f"Knowledge base directory not found: {kb_path}")
            return 0

        # Load L1 axioms
        l1_file = os.path.join(kb_path, "L1_axioms.jsonl")
        if os.path.exists(l1_file):
            count += self._load_jsonl(l1_file, NodeType.AXIOM, "L1")

        # Load L2 theories
        l2_files = [
            "L2_theory.jsonl",
            "L2_protective_belt.jsonl",
        ]
        for fname in l2_files:
            fpath = os.path.join(kb_path, fname)
            if os.path.exists(fpath):
                count += self._load_jsonl(fpath, NodeType.THEOREM, "L2")

        # Load L3 heuristics
        l3_file = os.path.join(kb_path, "L3_heuristics.jsonl")
        if os.path.exists(l3_file):
            count += self._load_jsonl(l3_file, NodeType.CONCEPT, "L3")

        return count

    def load_relations_from_kb(self, kb_dir: str = "knowledge_base") -> int:
        """
        Load relations from JSONL files that contain dependency information.
        This bridges kb_loader.py output with symbolic_engine.py graph.
        Returns number of edges loaded.
        """
        edge_count = 0
        kb_path = os.path.join(os.path.dirname(__file__), kb_dir)

        if not os.path.exists(kb_path):
            return 0

        # Load all JSONL files to extract dependency relations
        for jsonl_file in os.listdir(kb_path):
            if not jsonl_file.endswith('.jsonl'):
                continue

            filepath = os.path.join(kb_path, jsonl_file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            entry_id = entry.get("id", "")
                            dependencies = entry.get("dependencies", [])

                            # Create IMPLIES edges from dependencies
                            for dep_id in dependencies:
                                if dep_id in self.graph.nodes and entry_id in self.graph.nodes:
                                    edge = RelationEdge(
                                        source=dep_id,
                                        target=entry_id,
                                        relation=RelationType.IMPLIES,
                                        strength=0.8,
                                        evidence=f"Dependency from {dep_id}"
                                    )
                                    try:
                                        self.graph.add_edge(edge)
                                        edge_count += 1
                                    except ValueError:
                                        pass

                            # Check for explicit relations in entry
                            relations = entry.get("relations", [])
                            for rel in relations:
                                target_id = rel.get("target", "")
                                rel_type_str = rel.get("type", "IMPLIES")
                                strength = rel.get("strength", 0.5)

                                if target_id in self.graph.nodes and entry_id in self.graph.nodes:
                                    rel_type = getattr(RelationType, rel_type_str, RelationType.IMPLIES)
                                    edge = RelationEdge(
                                        source=entry_id,
                                        target=target_id,
                                        relation=rel_type,
                                        strength=strength,
                                        evidence=rel.get("evidence", "")
                                    )
                                    try:
                                        self.graph.add_edge(edge)
                                        edge_count += 1
                                    except ValueError:
                                        pass
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"Error loading relations from {jsonl_file}: {e}")

        return edge_count

    def load_from_kb_loader(self, graph: MSSKnowledgeGraph) -> int:
        """
        Load directly from a kb_loader.py generated graph.
        This is the preferred method when using kb_loader.py.
        """
        # Merge the loaded graph into our graph
        node_count = 0
        edge_count = 0

        # Copy nodes
        for node_id, node in graph.nodes.items():
            if node_id not in self.graph.nodes:
                self.graph.add_node(node)
                node_count += 1

        # Copy edges
        for edge in graph.edges:
            try:
                self.graph.add_edge(edge)
                edge_count += 1
            except ValueError:
                pass

        return node_count + edge_count

    def _load_jsonl(self, filepath: str, node_type: NodeType, layer: str) -> int:
        """Load entries from a JSONL file"""
        count = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        node = ConceptNode(
                            id=entry.get("id", f"auto_{count}"),
                            name=entry.get("title", "Untitled"),
                            node_type=node_type,
                            layer=layer,
                            content=entry.get("content", ""),
                            confidence=entry.get("confidence", 1.0 if layer == "L1" else 0.8),
                            falsifiable=entry.get("falsifiable", layer != "L1"),
                            humility_clause=entry.get("humility_clause"),
                            boundary_statement=entry.get("boundary_statement"),
                        )
                        self.graph.add_node(node)
                        count += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error loading {filepath}: {e}")

        return count

    def explain(self, concept_id: str) -> str:
        """Generate explanation for a concept"""
        node = self.graph.get_node(concept_id)
        if not node:
            return f"Concept '{concept_id}' not found"

        lines = [
            f"=== {node.name} ===",
            f"Type: {node.node_type.name} | Layer: {node.layer}",
            f"Content: {node.content[:300]}...",
        ]

        # Find what this implies
        implications = self.graph.get_neighbors(concept_id, RelationType.IMPLIES)
        if implications:
            lines.append("\nImplies:")
            for imp in implications[:5]:
                lines.append(f"  - {imp.name} ({imp.layer})")

        # Find what derives this
        derived_from = []
        for edge in self.graph.edges:
            if edge.target == concept_id and edge.relation == RelationType.DERIVES_FROM:
                source = self.graph.get_node(edge.source)
                if source:
                    derived_from.append(source)

        if derived_from:
            lines.append("\nDerived from:")
            for src in derived_from[:5]:
                lines.append(f"  - {src.name} ({src.layer})")

        return "\n".join(lines)

    def verify_claim(self, claim: str, referenced_nodes: List[str]) -> InferencePath:
        """
        Verify if a claim is supported by referenced nodes

        This is deterministic - no LLM involved
        """
        # Check if all referenced nodes exist
        missing = [nid for nid in referenced_nodes if nid not in self.graph.nodes]
        if missing:
            return InferencePath(
                steps=[],
                result=InferenceResult.UNDETERMINED,
                certainty=0.0,
                explanation=f"Referenced nodes not found: {missing}"
            )

        # Check for contradictions among references
        for i, a in enumerate(referenced_nodes):
            for b in referenced_nodes[i+1:]:
                contradiction = self.graph.check_contradiction(a, b)
                if contradiction.result == InferenceResult.DISPROVEN:
                    return InferencePath(
                        steps=contradiction.steps,
                        result=InferenceResult.DISPROVEN,
                        certainty=contradiction.certainty,
                        explanation=f"Contradiction found between references: {a} and {b}"
                    )

        # Check if references form a connected chain (basic coherence)
        if len(referenced_nodes) > 1:
            # Simple check: can we find paths between consecutive references
            for i in range(len(referenced_nodes) - 1):
                path = self.graph.find_path(referenced_nodes[i], referenced_nodes[i+1], max_depth=3)
                if path.result == InferenceResult.UNDETERMINED:
                    return InferencePath(
                        steps=[],
                        result=InferenceResult.UNDETERMINED,
                        certainty=0.5,
                        explanation=f"No clear connection between {referenced_nodes[i]} and {referenced_nodes[i+1]}"
                    )

        return InferencePath(
            steps=[],
            result=InferenceResult.PROVEN,
            certainty=0.9,
            explanation="Claim is consistent with referenced nodes (no contradictions, basic connectivity)"
        )

    def find_related(self, concept_id: str, max_depth: int = 2) -> List[Tuple[ConceptNode, int]]:
        """Find concepts related to given concept within N steps"""
        if concept_id not in self.graph.nodes:
            return []

        visited = {concept_id: 0}
        queue = [(concept_id, 0)]
        results = []

        while queue:
            current, depth = queue.pop(0)

            if depth > 0:
                node = self.graph.get_node(current)
                if node:
                    results.append((node, depth))

            if depth >= max_depth:
                continue

            for edge in self.graph._adjacency.get(current, []):
                if edge.target not in visited:
                    visited[edge.target] = depth + 1
                    queue.append((edge.target, depth + 1))

        return results

# --- Demo / Test ---

def demo():
    """Demonstrate symbolic engine capabilities"""
    print("=" * 60)
    print("MSS Symbolic Reasoning Engine Demo")
    print("=" * 60)

    # Create graph
    graph = MSSKnowledgeGraph()

    # Add sample nodes (subset of MSS framework)
    nodes = [
        ConceptNode("A1", "Information Ontology", NodeType.AXIOM, "L1",
                   "Information is the fundamental substrate of reality", confidence=1.0),
        ConceptNode("A2", "0/1 Critical", NodeType.AXIOM, "L1",
                   "0/1 mapping is the fundamental phase transition", confidence=1.0),
        ConceptNode("T1", "BCT Coupling", NodeType.THEOREM, "L2",
                   "Bekenstein-Church-Turing coupling between information and computation", confidence=0.9),
        ConceptNode("T2", "Organizational Resilience", NodeType.THEOREM, "L2",
                   "R = T/phi, where T is tuning degree and phi is dissipation", confidence=0.85),
        ConceptNode("H1", "Redshift Metaphor", NodeType.CONCEPT, "L3",
                   "Civilizational redshift as metaphor for meaning dilution", confidence=0.7),
    ]

    for node in nodes:
        graph.add_node(node)

    # Add edges
    edges = [
        RelationEdge("A1", "T1", RelationType.IMPLIES, strength=1.0,
                    evidence="Information ontology implies BCT coupling"),
        RelationEdge("A2", "T1", RelationType.IMPLIES, strength=0.9),
        RelationEdge("T1", "T2", RelationType.DERIVES_FROM, strength=0.8),
        RelationEdge("T2", "H1", RelationType.ANALOGOUS, strength=0.6),
    ]

    for edge in edges:
        graph.add_edge(edge)

    # Demo 1: Graph stats
    print("\n1. Graph Statistics:")
    stats = graph.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Demo 2: Find path
    print("\n2. Path Finding (A1 -> T2):")
    path = graph.find_path("A1", "T2", max_depth=3)
    print(path.to_text())

    # Demo 3: Query
    print("\n3. Query L1 Axioms:")
    l1_nodes = graph.query(layer="L1")
    for node in l1_nodes:
        print(f"   - {node.name}: {node.content[:50]}...")

    # Demo 4: Reasoner
    print("\n4. Symbolic Reasoner:")
    reasoner = SymbolicReasoner(graph)

    # Explain a concept
    print("\n   Explaining T1:")
    print(reasoner.explain("T1"))

    # Verify claim
    print("\n   Verifying claim with [A1, T1]:")
    result = reasoner.verify_claim("BCT coupling holds", ["A1", "T1"])
    print(result.to_text())

    # Find related
    print("\n   Concepts related to A1 (depth 2):")
    related = reasoner.find_related("A1", max_depth=2)
    for node, depth in related:
        print(f"   - {node.name} (depth {depth})")

    print("\n" + "=" * 60)
    print("Demo complete")
    print("=" * 60)

if __name__ == "__main__":
    demo()
