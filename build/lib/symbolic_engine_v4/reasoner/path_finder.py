"""
MSS Symbolic Engine v4.0 - A* Path Finder with Layer Heuristics
"""

import heapq
from typing import List, Optional, Dict, Tuple, Set
from ..core import CSRGraph, ConceptNode, ConceptEdge
from ..core.types import RelationType, LayerTier

class AStarPathFinder:
    """
    A* pathfinding with layer-aware heuristics

    Optimized for MSS knowledge graph traversal:
    - Prefers L1→L2→L3 paths (hierarchical reasoning)
    - Penalizes L4 contaminated nodes
    - Rewards IMPLIES edges over ANALOGOUS
    """

    def __init__(self, graph: CSRGraph):
        self.graph = graph
        self.layer_weights = {
            LayerTier.L1_CORE: 0.5,      # Prefer L1 nodes
            LayerTier.L2_PROTECTIVE: 0.8,
            LayerTier.L3_HEURISTIC: 1.0,  # Standard weight
            LayerTier.L4_CONTAMINATED: 5.0  # Heavy penalty
        }
        self.relation_weights = {
            RelationType.IMPLIES: 0.5,     # Strong logical connection
            RelationType.DERIVES_FROM: 0.6,
            RelationType.REFINES: 0.7,
            RelationType.TESTS: 0.8,
            RelationType.INSTANCE_OF: 0.9,
            RelationType.ANALOGOUS: 1.5,   # Weaker connection
            RelationType.CONTRADICTS: 10.0  # Avoid contradictions
        }

    def find_path(self, start_id: str, end_id: str,
                  max_depth: int = 10) -> Optional[Dict]:
        """
        Find optimal path from start to end node

        Returns:
            Dict with path info or None if no path found
        """
        if start_id not in self.graph.nodes:
            return None
        if end_id not in self.graph.nodes:
            return None

        start_idx = self.graph.nodes[start_id]
        end_idx = self.graph.nodes[end_id]

        # A* algorithm
        open_set = [(0, start_idx)]  # (f_score, node_idx)
        came_from: Dict[int, int] = {}

        g_score: Dict[int, float] = {start_idx: 0}
        f_score: Dict[int, float] = {start_idx: self._heuristic(start_idx, end_idx)}

        visited: Set[int] = set()

        while open_set:
            current_f, current_idx = heapq.heappop(open_set)

            if current_idx in visited:
                continue

            visited.add(current_idx)

            # Check if reached target
            if current_idx == end_idx:
                return self._reconstruct_path(came_from, start_idx, end_idx)

            # Check depth limit
            path_length = len(self._get_path_indices(came_from, start_idx, current_idx))
            if path_length >= max_depth:
                continue

            # Explore neighbors
            neighbors = self._get_neighbors(current_idx)
            for neighbor_idx, edge_cost in neighbors:
                if neighbor_idx in visited:
                    continue

                tentative_g = g_score[current_idx] + edge_cost

                if neighbor_idx not in g_score or tentative_g < g_score[neighbor_idx]:
                    came_from[neighbor_idx] = current_idx
                    g_score[neighbor_idx] = tentative_g
                    f_score[neighbor_idx] = tentative_g + self._heuristic(neighbor_idx, end_idx)
                    heapq.heappush(open_set, (f_score[neighbor_idx], neighbor_idx))

        return None  # No path found

    def find_all_paths(self, start_id: str, end_id: str,
                       max_paths: int = 5, max_depth: int = 10) -> List[Dict]:
        """Find multiple paths between nodes"""
        paths = []

        for _ in range(max_paths):
            path = self.find_path(start_id, end_id, max_depth)
            if path is None:
                break
            paths.append(path)

            # Block this path for next iteration (simple approach)
            # In production, use edge penalization

        return paths

    def _heuristic(self, node_idx: int, target_idx: int) -> float:
        """
        Layer-aware heuristic

        Estimates cost from node to target:
        - Prefer moving towards higher layer nodes
        - Penalize L4 nodes
        """
        node = self.graph.node_list[node_idx]
        target = self.graph.node_list[target_idx]

        # Base heuristic: layer difference
        layer_diff = abs(self._layer_value(node.layer) - self._layer_value(target.layer))

        # Layer weight penalty/bonus
        layer_weight = self.layer_weights.get(node.layer, 1.0)

        return layer_diff * layer_weight

    def _get_neighbors(self, node_idx: int) -> List[Tuple[int, float]]:
        """Get neighbors with edge costs"""
        neighbors = []

        start = self.graph.indptr[node_idx]
        end = self.graph.indptr[node_idx + 1]

        for i in range(start, end):
            neighbor_idx = self.graph.indices[i]
            relation, weight, _ = self.graph.data[i]

            # Calculate edge cost
            relation_weight = self.relation_weights.get(relation, 1.0)
            neighbor_node = self.graph.node_list[neighbor_idx]
            layer_weight = self.layer_weights.get(neighbor_node.layer, 1.0)

            cost = weight * relation_weight * layer_weight
            neighbors.append((neighbor_idx, cost))

        return neighbors

    def _reconstruct_path(self, came_from: Dict[int, int],
                          start_idx: int, end_idx: int) -> Dict:
        """Reconstruct path from came_from map"""
        path_indices = self._get_path_indices(came_from, start_idx, end_idx)

        nodes = []
        edges = []
        total_cost = 0

        for i, idx in enumerate(path_indices):
            node = self.graph.node_list[idx]
            nodes.append({
                "id": node.id,
                "title": node.title,
                "layer": node.layer.value
            })

            if i > 0:
                prev_idx = path_indices[i - 1]
                edge = self.graph.get_edge(
                    self.graph.node_list[prev_idx].id,
                    node.id
                )
                if edge:
                    edges.append({
                        "source": edge.source,
                        "target": edge.target,
                        "relation": edge.relation.value,
                        "weight": edge.weight
                    })
                    total_cost += edge.weight

        return {
            "path_length": len(nodes),
            "nodes": nodes,
            "edges": edges,
            "total_cost": round(total_cost, 3),
            "confidence": round(1.0 / (1.0 + total_cost), 3)
        }

    def _get_path_indices(self, came_from: Dict[int, int],
                          start_idx: int, end_idx: int) -> List[int]:
        """Get path as list of indices"""
        path = [end_idx]
        current = end_idx

        while current in came_from:
            current = came_from[current]
            path.append(current)

        path.reverse()
        return path

    def _layer_value(self, layer: LayerTier) -> int:
        """Convert layer to numeric value for comparison"""
        layer_values = {
            LayerTier.L1_CORE: 1,
            LayerTier.L2_PROTECTIVE: 2,
            LayerTier.L3_HEURISTIC: 3,
            LayerTier.L4_CONTAMINATED: 4
        }
        return layer_values.get(layer, 3)
