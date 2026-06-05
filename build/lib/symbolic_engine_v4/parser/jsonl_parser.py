"""
MSS Symbolic Engine v4.0 - JSONL Knowledge Base Parser
"""

import json
import os
from typing import List, Optional, Dict, Any
from ..core.types import ConceptNode, ConceptEdge, RelationType, NodeType, LayerTier

class JSONLParser:
    """Parse JSONL knowledge base files into graph components"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse_file(self, filepath: str) -> tuple[List[ConceptNode], List[ConceptEdge]]:
        """
        Parse a single JSONL file into nodes and edges

        Returns:
            Tuple of (nodes, edges)
        """
        nodes = []
        edges = []

        if not os.path.exists(filepath):
            self.errors.append(f"File not found: {filepath}")
            return nodes, edges

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        node = self._parse_node(data)
                        if node:
                            nodes.append(node)

                            # Extract edges from content if present
                            content_edges = self._extract_edges_from_content(node, data)
                            edges.extend(content_edges)
                    except json.JSONDecodeError as e:
                        self.warnings.append(f"Line {line_num}: JSON parse error - {e}")
                    except Exception as e:
                        self.warnings.append(f"Line {line_num}: Parse error - {e}")

        except Exception as e:
            self.errors.append(f"File read error: {e}")

        return nodes, edges

    def parse_directory(self, directory: str, exclude_prefix: str = "ima_") -> tuple[List[ConceptNode], List[ConceptEdge]]:
        """
        Parse all JSONL files in a directory

        Args:
            directory: Path to directory containing JSONL files
            exclude_prefix: Skip files starting with this prefix

        Returns:
            Tuple of (nodes, edges)
        """
        all_nodes = []
        all_edges = []

        if not os.path.exists(directory):
            self.errors.append(f"Directory not found: {directory}")
            return all_nodes, all_edges

        files = sorted([f for f in os.listdir(directory)
                       if f.endswith('.jsonl') and not f.startswith(exclude_prefix)])

        for fname in files:
            filepath = os.path.join(directory, fname)
            nodes, edges = self.parse_file(filepath)
            all_nodes.extend(nodes)
            all_edges.extend(edges)

        return all_nodes, all_edges

    def _parse_node(self, data: Dict[str, Any]) -> Optional[ConceptNode]:
        """Parse a single JSON object into a ConceptNode"""
        if not isinstance(data, dict):
            return None

        # Required fields
        node_id = data.get('id', data.get('entry_id', ''))
        if not node_id:
            return None

        title = data.get('title', 'Untitled')
        content = data.get('content', data.get('text', ''))

        # Optional fields
        node_type = self._parse_node_type(data.get('node_type', 'concept'))
        layer = self._parse_layer(data.get('layer', 'L3'))
        category = data.get('category')
        tags = data.get('tags', [])

        # Metadata
        metadata = {k: v for k, v in data.items()
                     if k not in ['id', 'title', 'content', 'text', 'node_type',
                                  'layer', 'category', 'tags']}

        return ConceptNode(
            id=node_id,
            title=title,
            content=content,
            node_type=node_type,
            layer=layer,
            category=category,
            tags=tags if isinstance(tags, list) else [],
            metadata=metadata
        )

    def _extract_edges_from_content(self, node: ConceptNode, data: Dict[str, Any]) -> List[ConceptEdge]:
        """Extract implicit edges from node content or explicit edge definitions"""
        edges = []

        # Check for explicit edges
        if 'edges' in data and isinstance(data['edges'], list):
            for edge_data in data['edges']:
                if isinstance(edge_data, dict):
                    target = edge_data.get('target', edge_data.get('to', ''))
                    relation = self._parse_relation(edge_data.get('relation', 'analogous'))
                    weight = edge_data.get('weight', 1.0)

                    if target:
                        edges.append(ConceptEdge(
                            source=node.id,
                            target=target,
                            relation=relation,
                            weight=weight
                        ))

        # Check for dependencies
        if 'dependencies' in data and isinstance(data['dependencies'], list):
            for dep in data['dependencies']:
                if isinstance(dep, str):
                    edges.append(ConceptEdge(
                        source=node.id,
                        target=dep,
                        relation=RelationType.DERIVES_FROM,
                        weight=1.0
                    ))

        return edges

    def _parse_node_type(self, value: str) -> NodeType:
        """Parse node type string to enum"""
        type_map = {
            'axiom': NodeType.AXIOM,
            'theorem': NodeType.THEOREM,
            'definition': NodeType.DEFINITION,
            'lemma': NodeType.LEMMA,
            'concept': NodeType.CONCEPT,
            'heuristic': NodeType.HEURISTIC,
        }
        return type_map.get(value.lower(), NodeType.CONCEPT)

    def _parse_layer(self, value: str) -> LayerTier:
        """Parse layer string to enum"""
        layer_map = {
            'L1': LayerTier.L1_CORE,
            'L2': LayerTier.L2_PROTECTIVE,
            'L3': LayerTier.L3_HEURISTIC,
            'L4': LayerTier.L4_CONTAMINATED,
            'l1': LayerTier.L1_CORE,
            'l2': LayerTier.L2_PROTECTIVE,
            'l3': LayerTier.L3_HEURISTIC,
            'l4': LayerTier.L4_CONTAMINATED,
        }
        return layer_map.get(value, LayerTier.L3_HEURISTIC)

    def _parse_relation(self, value: str) -> RelationType:
        """Parse relation string to enum"""
        relation_map = {
            'implies': RelationType.IMPLIES,
            'contradicts': RelationType.CONTRADICTS,
            'instance_of': RelationType.INSTANCE_OF,
            'derives_from': RelationType.DERIVES_FROM,
            'analogous': RelationType.ANALOGOUS,
            'tests': RelationType.TESTS,
            'refines': RelationType.REFINES,
        }
        return relation_map.get(value.lower(), RelationType.ANALOGOUS)

    def get_stats(self) -> Dict[str, Any]:
        """Get parsing statistics"""
        return {
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'error_details': self.errors,
            'warning_details': self.warnings
        }
