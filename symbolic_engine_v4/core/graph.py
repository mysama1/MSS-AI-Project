"""
MSS Symbolic Engine v4.0 - CSR Graph Implementation
Compressed Sparse Row graph for efficient memory and traversal
"""

from typing import Dict, List, Optional, Tuple, Set, Iterator
from collections import defaultdict
from .types import ConceptNode, ConceptEdge, RelationType

class CSRGraph:
    """
    Compressed Sparse Row graph implementation

    Memory efficient for large graphs:
    - Nodes stored in dense array
    - Edges stored in CSR format (indptr, indices, data)
    - Supports up to millions of nodes
    """

    def __init__(self, max_nodes: int = 100000):
        self.max_nodes = max_nodes

        # Node storage
        self.nodes: Dict[str, int] = {}  # id -> index mapping
        self.node_list: List[ConceptNode] = []  # index -> node

        # CSR format for edges
        self.indptr = [0]  # Row pointers
        self.indices = []  # Column indices
        self.data = []     # Edge data (relation type, weight)

        # Reverse mapping for quick lookups
        self.edge_map: Dict[Tuple[int, int], int] = {}  # (src_idx, dst_idx) -> edge_idx

        # Node metadata
        self.node_metadata: Dict[int, Dict] = defaultdict(dict)

        self._node_count = 0
        self._edge_count = 0

    def add_node(self, node: ConceptNode) -> int:
        """Add a node to the graph, return its index"""
        if node.id in self.nodes:
            return self.nodes[node.id]

        if self._node_count >= self.max_nodes:
            raise MemoryError(f"Maximum node count {self.max_nodes} reached")

        idx = self._node_count
        self.nodes[node.id] = idx
        self.node_list.append(node)
        self._node_count += 1

        # Extend indptr
        self.indptr.append(self.indptr[-1])

        return idx

    def add_edge(self, edge: ConceptEdge) -> bool:
        """Add an edge to the graph"""
        if edge.source not in self.nodes:
            return False
        if edge.target not in self.nodes:
            return False

        src_idx = self.nodes[edge.source]
        dst_idx = self.nodes[edge.target]

        # Check if edge already exists
        if (src_idx, dst_idx) in self.edge_map:
            return False

        # Insert into CSR format (maintain sorted order)
        start = self.indptr[src_idx]
        end = self.indptr[src_idx + 1]

        # Find insertion point
        insert_pos = end
        for i in range(start, end):
            if self.indices[i] > dst_idx:
                insert_pos = i
                break

        # Insert
        self.indices.insert(insert_pos, dst_idx)
        self.data.insert(insert_pos, (edge.relation, edge.weight, edge.metadata))

        # Update indptr for subsequent rows
        for i in range(src_idx + 1, len(self.indptr)):
            self.indptr[i] += 1

        # Update edge map
        self.edge_map[(src_idx, dst_idx)] = len(self.data) - 1
        self._edge_count += 1

        return True

    def get_node(self, node_id: str) -> Optional[ConceptNode]:
        """Get node by id"""
        if node_id not in self.nodes:
            return None
        return self.node_list[self.nodes[node_id]]

    def get_node_by_index(self, idx: int) -> Optional[ConceptNode]:
        """Get node by index"""
        if 0 <= idx < len(self.node_list):
            return self.node_list[idx]
        return None

    def get_neighbors(self, node_id: str) -> List[Tuple[ConceptNode, RelationType, float]]:
        """Get all neighbors of a node"""
        if node_id not in self.nodes:
            return []

        idx = self.nodes[node_id]
        start = self.indptr[idx]
        end = self.indptr[idx + 1]

        neighbors = []
        for i in range(start, end):
            dst_idx = self.indices[i]
            relation, weight, _ = self.data[i]
            node = self.node_list[dst_idx]
            neighbors.append((node, relation, weight))

        return neighbors

    def get_outgoing_edges(self, node_id: str) -> List[ConceptEdge]:
        """Get all outgoing edges from a node"""
        if node_id not in self.nodes:
            return []

        idx = self.nodes[node_id]
        start = self.indptr[idx]
        end = self.indptr[idx + 1]

        edges = []
        for i in range(start, end):
            dst_idx = self.indices[i]
            relation, weight, metadata = self.data[i]
            dst_node = self.node_list[dst_idx]
            edges.append(ConceptEdge(
                source=node_id,
                target=dst_node.id,
                relation=relation,
                weight=weight,
                metadata=metadata
            ))

        return edges

    def has_edge(self, source: str, target: str) -> bool:
        """Check if edge exists"""
        if source not in self.nodes or target not in self.nodes:
            return False

        src_idx = self.nodes[source]
        dst_idx = self.nodes[target]
        return (src_idx, dst_idx) in self.edge_map

    def get_edge(self, source: str, target: str) -> Optional[ConceptEdge]:
        """Get specific edge"""
        if source not in self.nodes or target not in self.nodes:
            return None

        src_idx = self.nodes[source]
        dst_idx = self.nodes[target]

        if (src_idx, dst_idx) not in self.edge_map:
            return None

        edge_idx = self.edge_map[(src_idx, dst_idx)]
        relation, weight, metadata = self.data[edge_idx]

        return ConceptEdge(
            source=source,
            target=target,
            relation=relation,
            weight=weight,
            metadata=metadata
        )

    def get_nodes_by_type(self, node_type) -> List[ConceptNode]:
        """Get all nodes of a specific type"""
        return [n for n in self.node_list if n.node_type == node_type]

    def get_nodes_by_layer(self, layer) -> List[ConceptNode]:
        """Get all nodes in a specific layer"""
        return [n for n in self.node_list if n.layer == layer]

    @property
    def node_count(self) -> int:
        return self._node_count

    @property
    def edge_count(self) -> int:
        return self._edge_count

    def __len__(self):
        return self._node_count

    def __iter__(self) -> Iterator[ConceptNode]:
        return iter(self.node_list)
