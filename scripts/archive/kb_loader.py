"""
MSS Knowledge Base Loader
Loads entries from JSONL files into symbolic graph
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Iterator
from datetime import datetime

from mssclaw.core.semantic.symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType, SymbolicReasoner
)

class KBEntry:
    """Single knowledge base entry"""
    def __init__(self, data: Dict):
        self.id = data.get("id", "")
        self.title = data.get("title", "")
        self.layer = data.get("layer", "L3")
        self.category = data.get("category", "")
        self.score = data.get("score", 0.0)
        self.status = data.get("status", "active")
        self.version = data.get("version", "")
        self.content = data.get("content", "")
        self.content_ref = data.get("content_ref", "")
        self.tags = data.get("tags", [])
        self.boundary_note = data.get("boundary_note", "")
        self.falsifiability = data.get("falsifiability", "")
        self.humility_clause = data.get("humility_clause", "")
        self.compliance = data.get("compliance", {})
        self.created_at = data.get("created_at", "")
        self.dependencies = data.get("dependencies", [])

    def to_node(self) -> ConceptNode:
        """Convert to graph node"""
        layer = self.layer if self.layer in ("L1", "L2", "L3", "L4") else "L3"

        # Map category to node type
        type_map = {
            "axiom": NodeType.AXIOM,
            "theorem": NodeType.THEOREM,
            "theory": NodeType.THEOREM,
            "protective_belt": NodeType.THEOREM,
            "heuristic": NodeType.CONCEPT,
            "metaphor": NodeType.CONCEPT,
            "prediction": NodeType.PREDICTION,
            "lemma": NodeType.LEMMA,
        }
        node_type = type_map.get(self.category.lower(), NodeType.CONCEPT)

        # L1 is always axiom
        if layer == "L1":
            node_type = NodeType.AXIOM

        confidence = 1.0 if layer == "L1" else self.score

        return ConceptNode(
            id=self.id,
            name=self.title,
            node_type=node_type,
            layer=layer,
            content=self.content or f"See: {self.content_ref}",
            confidence=confidence,
            falsifiable=layer != "L1",
            humility_clause=self.humility_clause,
            boundary_statement=self.boundary_note,
        )

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def compliance_score(self) -> float:
        """Average compliance score"""
        if not self.compliance:
            return 0.0
        return sum(self.compliance.values()) / len(self.compliance)

class KBLoader:
    """
    Loads MSS knowledge base from JSONL files

    Supports:
    - Multiple JSONL files
    - Layer-based organization
    - Compliance filtering
    - Version tracking
    """

    def __init__(self, kb_dir: str = "knowledge_base"):
        self.kb_dir = Path(kb_dir)
        self.entries: Dict[str, KBEntry] = {}
        self.loaded_files: List[str] = []
        self.load_errors: List[str] = []

    def load_all(self) -> int:
        """Load all JSONL files in kb_dir"""
        if not self.kb_dir.exists():
            self.load_errors.append(f"Directory not found: {self.kb_dir}")
            return 0

        count = 0
        for jsonl_file in self.kb_dir.glob("*.jsonl"):
            try:
                file_count = self.load_file(jsonl_file)
                count += file_count
                self.loaded_files.append(str(jsonl_file.name))
            except Exception as e:
                self.load_errors.append(f"{jsonl_file.name}: {e}")

        return count

    def load_file(self, filepath: Path) -> int:
        """Load entries from a single JSONL file"""
        count = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = KBEntry(data)
                    if entry.id:
                        self.entries[entry.id] = entry
                        count += 1
                except json.JSONDecodeError as e:
                    self.load_errors.append(f"{filepath.name}:{line_num}: JSON error")
                except Exception as e:
                    self.load_errors.append(f"{filepath.name}:{line_num}: {e}")
        return count

    def to_graph(self, include_inactive: bool = False) -> MSSKnowledgeGraph:
        """Convert loaded entries to knowledge graph"""
        graph = MSSKnowledgeGraph()

        # Add nodes
        for entry in self.entries.values():
            if not include_inactive and not entry.is_active:
                continue
            node = entry.to_node()
            graph.add_node(node)

        # Add edges based on relationships
        self._add_edges(graph)

        return graph

    def _add_edges(self, graph: MSSKnowledgeGraph):
        """Add edges between related entries with enhanced heuristics"""
        # Layer-based edges: L1 -> L2/L3 (IMPLIES, DERIVES_FROM)
        layer_hierarchy = {"L1": 1, "L2": 2, "L3": 3}
        entries_by_layer = {}
        for e in self.entries.values():
            layer = e.layer
            if layer not in entries_by_layer:
                entries_by_layer[layer] = []
            entries_by_layer[layer].append(e)

        # Cross-layer: lower -> higher (IMPLIES)
        for lower_layer, higher_layer in [("L1", "L2"), ("L1", "L3"), ("L2", "L3")]:
            lower_entries = entries_by_layer.get(lower_layer, [])
            higher_entries = entries_by_layer.get(higher_layer, [])

            for lower in lower_entries:
                for higher in higher_entries:
                    # Heuristic 1: ID reference in content/title
                    id_match = lower.id.lower() in higher.content.lower() or \
                              lower.id.lower() in higher.title.lower()

                    # Heuristic 2: Title word overlap (FIXED Chinese segmentation)
                    lower_words = set(self._extract_keywords(lower.title))
                    higher_words = set(self._extract_keywords(higher.title))
                    word_overlap = len(lower_words & higher_words) / max(len(lower_words), 1)

                    # Heuristic 3: Content word overlap (broader context)
                    lower_content = set(self._extract_keywords(lower.content))
                    higher_content = set(self._extract_keywords(higher.content))
                    content_overlap = len(lower_content & higher_content) / max(len(lower_content), 1)

                    # Heuristic 4: Tag overlap
                    tag_overlap = len(set(lower.tags) & set(higher.tags)) / max(len(lower.tags), 1)

                    # Heuristic 5: Dependency field reference
                    dep_match = False
                    if hasattr(higher, 'dependencies') and higher.dependencies:
                        dep_match = lower.id in higher.dependencies

                    # Combined score (lowered threshold for Chinese)
                    score = (0.5 if id_match else 0) + \
                            word_overlap * 0.25 + \
                            content_overlap * 0.15 + \
                            tag_overlap * 0.2 + \
                            (0.4 if dep_match else 0)

                    if score >= 0.15:  # Lowered threshold for Chinese text
                        edge = RelationEdge(
                            source=lower.id,
                            target=higher.id,
                            relation=RelationType.IMPLIES,
                            strength=min(score, 1.0),
                            evidence=f"Derived from {lower.id} (score={score:.2f})"
                        )
                        try:
                            graph.add_edge(edge)
                        except ValueError:
                            pass

        # Same-layer edges: shared tags -> ANALOGOUS
        tag_entries: Dict[str, List[str]] = {}
        for eid, entry in self.entries.items():
            for tag in entry.tags:
                if tag not in tag_entries:
                    tag_entries[tag] = []
                tag_entries[tag].append(eid)

        for tag, eids in tag_entries.items():
            if len(eids) > 1 and tag not in ["L1", "L2", "L3"]:  # Skip layer tags
                for i in range(len(eids)):
                    for j in range(i+1, len(eids)):
                        edge = RelationEdge(
                            source=eids[i],
                            target=eids[j],
                            relation=RelationType.ANALOGOUS,
                            strength=0.5,
                            evidence=f"Shared tag: {tag}",
                            bidirectional=True
                        )
                        try:
                            graph.add_edge(edge)
                        except ValueError:
                            pass

        # Contradiction detection: same layer, opposite keywords
        contradiction_pairs = [
            ("确定性", "随机性"), ("连续", "离散"), ("全局", "局部"),
            ("可逆", "不可逆"), ("稳定", "不稳定"), ("有序", "无序")
        ]
        for layer, entries in entries_by_layer.items():
            for i, e1 in enumerate(entries):
                for e2 in entries[i+1:]:
                    for w1, w2 in contradiction_pairs:
                        if (w1 in e1.title and w2 in e2.title) or \
                           (w2 in e1.title and w1 in e2.title):
                            edge = RelationEdge(
                                source=e1.id,
                                target=e2.id,
                                relation=RelationType.CONTRADICTS,
                                strength=0.7,
                                evidence=f"Potential contradiction: {w1} vs {w2}",
                                bidirectional=True
                            )
                            try:
                                graph.add_edge(edge)
                            except ValueError:
                                pass

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text - FIXED for Chinese segmentation"""
        import re
        # Remove common stop words
        stop_words = {"的", "了", "和", "是", "在", "有", "与", "为", "从", "对",
                      "the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "of", "to", "in", "for", "on", "with", "at", "by", "from",
                      "mss", "v2", "v3", "v10", "v12", "v123", "v20"}

        # Strategy 1: Extract 2-4 char Chinese phrases (bigrams/trigrams/quadgrams)
        # These are the most meaningful units in Chinese
        chinese_phrases = re.findall(r'[\u4e00-\u9fff]{2,4}', text)

        # Strategy 2: Extract English words 3+ chars
        english_words = re.findall(r'[a-zA-Z]{3,}', text.lower())

        # Combine - use phrases only (individual chars too noisy)
        all_words = chinese_phrases + english_words
        return [w for w in all_words if w not in stop_words]

    def _extract_content_keywords(self, text: str) -> List[str]:
        """Extract individual Chinese characters and English words for content matching"""
        import re
        # Extract individual Chinese characters (meaningful ones)
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        # Extract English words 3+ chars
        english_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
        return chinese_chars + english_words

    def get_by_layer(self, layer: str) -> List[KBEntry]:
        """Get all entries in a layer"""
        return [e for e in self.entries.values() if e.layer == layer]

    def get_by_tag(self, tag: str) -> List[KBEntry]:
        """Get entries by tag"""
        return [e for e in self.entries.values() if tag in e.tags]

    def get_stats(self) -> Dict:
        """Get loading statistics"""
        layers = {}
        categories = {}
        statuses = {}

        for entry in self.entries.values():
            layers[entry.layer] = layers.get(entry.layer, 0) + 1
            categories[entry.category] = categories.get(entry.category, 0) + 1
            statuses[entry.status] = statuses.get(entry.status, 0) + 1

        return {
            "total_entries": len(self.entries),
            "files_loaded": len(self.loaded_files),
            "errors": len(self.load_errors),
            "by_layer": layers,
            "by_category": categories,
            "by_status": statuses,
        }

def load_default_kb() -> MSSKnowledgeGraph:
    """Convenience function: load default knowledge base"""
    loader = KBLoader()
    count = loader.load_all()
    print(f"Loaded {count} entries from {len(loader.loaded_files)} files")
    if loader.load_errors:
        print(f"Errors: {len(loader.load_errors)}")
    return loader.to_graph()

# Demo
if __name__ == "__main__":
    print("=" * 60)
    print("MSS Knowledge Base Loader Demo")
    print("=" * 60)

    loader = KBLoader()
    count = loader.load_all()

    print(f"\nLoaded {count} entries")
    print(f"Files: {loader.loaded_files}")

    stats = loader.get_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")

    # Convert to graph
    graph = loader.to_graph()
    print(f"\nGraph: {graph.stats()}")

    # Create reasoner
    reasoner = SymbolicReasoner(graph)

    # List all nodes
    print("\nNodes:")
    for node in graph.nodes.values():
        print(f"  [{node.layer}] {node.id}: {node.name}")

    print("\n" + "=" * 60)
