"""
MSS Topology Metrics Engine v1.0
拓扑度量引擎 - 基于图论的标准算法实现

MSS定位说明(L3试探法标注):
本模块使用标准图论算法(连通分量、桥边检测、聚类系数)作为知识图谱的
结构健康度指标。文中"拓扑""同调""同伦"等术语为L3隐喻表述，实际
实现为确定性图论计算，不涉及连续数学或代数拓扑的形式化证明。

工程目标:
1. 识别知识图谱中的逻辑脆弱点(桥边)
2. 量化知识密集度(聚类系数)
3. 检测知识孤岛(连通分量)
4. 为热税计算提供结构权重因子

与现有系统集成:
- 输入: symbolic_engine.MSSKnowledgeGraph
- 输出: 拓扑健康度评分 + 结构脆弱点报告
- 调用方: symbolic_engine_v2.GraphAlgorithms(增强)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict, deque
import heapq

from symbolic_engine import (
    MSSKnowledgeGraph, ConceptNode, RelationEdge,
    NodeType, RelationType
)


@dataclass
class TopologyMetrics:
    """图谱拓扑度量结果"""
    node_count: int
    edge_count: int
    connected_components: int
    bridge_count: int
    avg_clustering_coefficient: float
    avg_path_length: float
    diameter: int
    
    # MSS专用指标
    layer_crossing_edges: int  # 跨层边数量
    l1_l2_bridge_edges: int    # L1-L2桥边(关键脆弱点)
    l2_l3_bridge_edges: int    # L2-L3桥边
    isolated_nodes: int        # 孤立节点数
    
    # 健康度评分(0-100)
    topology_health_score: float
    
    # 详细报告
    bridges: List[Tuple[str, str]] = field(default_factory=list)
    component_sizes: List[int] = field(default_factory=list)
    node_clustering: Dict[str, float] = field(default_factory=dict)


@dataclass
class VulnerabilityReport:
    """逻辑脆弱点报告"""
    bridge_edges: List[Tuple[str, str, str]]  # (source, target, reason)
    sparse_regions: List[str]  # 聚类系数低于阈值的节点
    isolated_clusters: List[List[str]]  # 孤立连通分量
    layer_gaps: List[Tuple[str, str]]  # 层间连接缺失
    
    # 修复建议
    recommendations: List[str] = field(default_factory=list)


class TopologyMetricsEngine:
    """
    拓扑度量引擎
    
    基于标准图论算法，为知识图谱提供结构健康度分析。
    所有算法均为确定性计算，不依赖LLM。
    """
    
    def __init__(self, graph: MSSKnowledgeGraph):
        self.graph = graph
        self._bridge_cache: Optional[List[Tuple[str, str]]] = None
        self._component_cache: Optional[List[Set[str]]] = None
    
    # =========================================================
    # 1. 连通分量分析 (Connected Components)
    # 对应L3隐喻: "知识孤岛检测"
    # =========================================================
    
    def find_connected_components(self) -> List[Set[str]]:
        """
        查找所有连通分量
        
        使用BFS遍历，将图谱划分为互不连通的意义域。
        不同连通域之间的概念无法通过现有关系直接推导。
        """
        if self._component_cache is not None:
            return self._component_cache
        
        visited = set()
        components = []
        
        for node_id in self.graph.nodes:
            if node_id in visited:
                continue
            
            # BFS遍历该连通分量
            component = set()
            queue = deque([node_id])
            visited.add(node_id)
            
            while queue:
                current = queue.popleft()
                component.add(current)
                
                # 遍历邻居(无向)
                neighbors = self._get_neighbors(current)
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            
            components.append(component)
        
        self._component_cache = components
        return components
    
    def _get_neighbors(self, node_id: str) -> Set[str]:
        """获取节点的所有邻居(无向)"""
        neighbors = set()
        if node_id in self.graph.nodes:
            # 出边邻居
            for edge in self.graph._adjacency.get(node_id, []):
                neighbors.add(edge.target)
            # 入边邻居(查找所有指向该节点的边)
            for other_id, edges in self.graph._adjacency.items():
                for edge in edges:
                    if edge.target == node_id:
                        neighbors.add(other_id)
        return neighbors
    
    def get_largest_component_size(self) -> int:
        """最大连通分量的大小"""
        components = self.find_connected_components()
        if not components:
            return 0
        return max(len(c) for c in components)
    
    def get_component_for_node(self, node_id: str) -> Optional[Set[str]]:
        """获取节点所属的连通分量"""
        components = self.find_connected_components()
        for comp in components:
            if node_id in comp:
                return comp
        return None
    
    # =========================================================
    # 2. 桥边检测 (Bridge Detection)
    # 对应L3隐喻: "逻辑脆弱点识别"
    # =========================================================
    
    def find_bridges(self) -> List[Tuple[str, str]]:
        """
        查找所有桥边(割边)
        
        桥边 = 删除后会使连通分量数量增加的边
        在知识图谱中，桥边代表两个知识域之间的唯一连接，
        是逻辑传导的关键脆弱点。
        
        算法: Tarjan桥边算法 O(V+E)
        """
        if self._bridge_cache is not None:
            return self._bridge_cache
        
        bridges = []
        visited = set()
        discovery = {}  # 发现时间
        low = {}        # 最低可达祖先
        parent = {}     # DFS树中的父节点
        time = [0]      # 使用list实现nonlocal
        
        def dfs(node: str):
            visited.add(node)
            discovery[node] = low[node] = time[0]
            time[0] += 1
            
            for neighbor in self._get_neighbors(node):
                if neighbor not in visited:
                    parent[neighbor] = node
                    dfs(neighbor)
                    
                    # 更新low值
                    low[node] = min(low[node], low[neighbor])
                    
                    # 桥边判定: 子树无法回连到祖先
                    if low[neighbor] > discovery[node]:
                        # 规范化边表示(较小ID在前)
                        edge = tuple(sorted([node, neighbor]))
                        if edge not in bridges:
                            bridges.append(edge)
                
                elif neighbor != parent.get(node):
                    # 回边
                    low[node] = min(low[node], discovery[neighbor])
        
        # 对每个未访问节点启动DFS
        for node_id in self.graph.nodes:
            if node_id not in visited:
                dfs(node_id)
        
        self._bridge_cache = bridges
        return bridges
    
    def is_bridge(self, source: str, target: str) -> bool:
        """判断特定边是否为桥边"""
        bridges = self.find_bridges()
        edge = tuple(sorted([source, target]))
        return edge in bridges
    
    def get_bridge_between_components(self) -> List[Tuple[str, str, int, int]]:
        """
        获取连接不同连通分量的桥边及其分量大小
        
        返回: [(source, target, comp1_size, comp2_size), ...]
        """
        bridges = self.find_bridges()
        result = []
        components = self.find_connected_components()
        comp_map = {}  # node_id -> component_index
        
        for idx, comp in enumerate(components):
            for node in comp:
                comp_map[node] = idx
        
        for source, target in bridges:
            idx1 = comp_map.get(source, -1)
            idx2 = comp_map.get(target, -1)
            if idx1 >= 0 and idx2 >= 0:
                size1 = len(components[idx1])
                size2 = len(components[idx2])
                result.append((source, target, size1, size2))
        
        return result
    
    # =========================================================
    # 3. 聚类系数 (Clustering Coefficient)
    # 对应L3隐喻: "知识密集度量化"
    # =========================================================
    
    def local_clustering_coefficient(self, node_id: str) -> float:
        """
        计算节点的局部聚类系数
        
        定义: 邻居之间实际存在的边数 / 可能存在的最大边数
        意义: 该节点所在区域的"知识密集度"
        - 高聚类 = 该领域知识密集，推理热税低
        - 低聚类 = 该领域知识稀疏，推理热税高
        """
        neighbors = list(self._get_neighbors(node_id))
        k = len(neighbors)
        
        if k < 2:
            return 0.0
        
        # 计算邻居之间的实际边数
        neighbor_edges = 0
        for i in range(k):
            for j in range(i + 1, k):
                if neighbors[j] in self._get_neighbors(neighbors[i]):
                    neighbor_edges += 1
        
        # 最大可能边数 = k*(k-1)/2
        max_edges = k * (k - 1) / 2
        return neighbor_edges / max_edges if max_edges > 0 else 0.0
    
    def global_clustering_coefficient(self) -> float:
        """全局平均聚类系数"""
        if not self.graph.nodes:
            return 0.0
        
        coefficients = []
        for node_id in self.graph.nodes:
            coeff = self.local_clustering_coefficient(node_id)
            coefficients.append(coeff)
        
        return sum(coefficients) / len(coefficients) if coefficients else 0.0
    
    def get_sparse_nodes(self, threshold: float = 0.3) -> List[Tuple[str, float]]:
        """
        获取聚类系数低于阈值的稀疏节点
        
        这些节点所在的知识区域需要补充数据以降低热税。
        """
        sparse = []
        for node_id in self.graph.nodes:
            coeff = self.local_clustering_coefficient(node_id)
            if coeff < threshold:
                sparse.append((node_id, coeff))
        
        # 按稀疏度排序(升序)
        sparse.sort(key=lambda x: x[1])
        return sparse
    
    # =========================================================
    # 4. 层间连接分析 (Layer Crossings)
    # MSS特有: 分析L1/L2/L3之间的连接模式
    # =========================================================
    
    def analyze_layer_connections(self) -> Dict[str, Any]:
        """
        分析层间连接模式
        
        返回层间连接统计，识别层间传导瓶颈。
        """
        layer_crossings = {
            "L1->L2": 0, "L2->L1": 0,
            "L2->L3": 0, "L3->L2": 0,
            "L1->L3": 0, "L3->L1": 0,
            "same_layer": 0
        }
        
        l1_l2_bridges = []
        l2_l3_bridges = []
        
        for node_id, node in self.graph.nodes.items():
            source_layer = getattr(node, 'layer', 'UNKNOWN')
            
            for edge in self.graph._adjacency.get(node_id, []):
                target = self.graph.nodes.get(edge.target)
                if target:
                    target_layer = getattr(target, 'layer', 'UNKNOWN')
                    
                    if source_layer == target_layer:
                        layer_crossings["same_layer"] += 1
                    else:
                        key = f"{source_layer}->{target_layer}"
                        if key in layer_crossings:
                            layer_crossings[key] += 1
                        
                        # 记录层间桥边
                        if source_layer == "L1" and target_layer == "L2":
                            l1_l2_bridges.append((node_id, edge.target))
                        elif source_layer == "L2" and target_layer == "L3":
                            l2_l3_bridges.append((node_id, edge.target))
        
        return {
            "crossing_counts": layer_crossings,
            "l1_l2_bridges": l1_l2_bridges,
            "l2_l3_bridges": l2_l3_bridges,
            "total_crossings": sum(v for k, v in layer_crossings.items() 
                                   if k != "same_layer")
        }
    
    def find_layer_gaps(self) -> List[Tuple[str, str]]:
        """
        发现层间连接缺失
        
        如果某层有大量节点但极少跨层连接，标记为"层间断裂"。
        """
        gaps = []
        
        # 统计每层节点数
        layer_counts = defaultdict(int)
        for node in self.graph.nodes.values():
            layer = getattr(node, 'layer', 'UNKNOWN')
            layer_counts[layer] += 1
        
        # 分析层间连接
        layer_conn = self.analyze_layer_connections()
        crossings = layer_conn["crossing_counts"]
        
        # 检查L1->L2连接
        if layer_counts.get("L1", 0) > 0 and layer_counts.get("L2", 0) > 0:
            l1_l2_total = crossings.get("L1->L2", 0) + crossings.get("L2->L1", 0)
            if l1_l2_total < max(layer_counts["L1"], layer_counts["L2"]) * 0.1:
                gaps.append(("L1", "L2"))
        
        # 检查L2->L3连接
        if layer_counts.get("L2", 0) > 0 and layer_counts.get("L3", 0) > 0:
            l2_l3_total = crossings.get("L2->L3", 0) + crossings.get("L3->L2", 0)
            if l2_l3_total < max(layer_counts["L2"], layer_counts["L3"]) * 0.1:
                gaps.append(("L2", "L3"))
        
        return gaps
    
    # =========================================================
    # 5. 综合拓扑度量 (Comprehensive Metrics)
    # =========================================================
    
    def compute_all_metrics(self) -> TopologyMetrics:
        """计算全部拓扑度量"""
        components = self.find_connected_components()
        bridges = self.find_bridges()
        avg_clustering = self.global_clustering_coefficient()
        
        # 计算平均路径长度和直径(在最大连通分量上)
        avg_path, diameter = self._compute_path_metrics()
        
        # 层间连接分析
        layer_analysis = self.analyze_layer_connections()
        
        # 孤立节点
        isolated = sum(1 for c in components if len(c) == 1)
        
        # 计算健康度评分
        # 基于: 连通性(40%) + 桥边比例(30%) + 聚类系数(30%)
        node_count = len(self.graph.nodes)
        edge_count = len(self.graph.edges)
        
        # 连通性评分(更多连通分量 = 更低分)
        if node_count > 0:
            connectivity_score = (self.get_largest_component_size() / node_count) * 100
        else:
            connectivity_score = 0
        
        # 桥边比例评分(桥边越多 = 越脆弱 = 越低分)
        if edge_count > 0:
            bridge_ratio = len(bridges) / edge_count
            bridge_score = max(0, 100 - bridge_ratio * 200)
        else:
            bridge_score = 100
        
        # 聚类评分
        clustering_score = avg_clustering * 100
        
        # 综合健康度
        health_score = (
            connectivity_score * 0.4 +
            bridge_score * 0.3 +
            clustering_score * 0.3
        )
        health_score = max(0, min(100, health_score))
        
        return TopologyMetrics(
            node_count=node_count,
            edge_count=edge_count,
            connected_components=len(components),
            bridge_count=len(bridges),
            avg_clustering_coefficient=avg_clustering,
            avg_path_length=avg_path,
            diameter=diameter,
            layer_crossing_edges=layer_analysis["total_crossings"],
            l1_l2_bridge_edges=len(layer_analysis["l1_l2_bridges"]),
            l2_l3_bridge_edges=len(layer_analysis["l2_l3_bridges"]),
            isolated_nodes=isolated,
            topology_health_score=health_score,
            bridges=bridges,
            component_sizes=[len(c) for c in components],
            node_clustering={
                nid: self.local_clustering_coefficient(nid)
                for nid in self.graph.nodes
            }
        )
    
    def _compute_path_metrics(self) -> Tuple[float, int]:
        """
        计算平均路径长度和直径
        
        在最大连通分量上计算所有节点对的最短路径。
        对于大型图谱，使用采样近似。
        """
        components = self.find_connected_components()
        if not components:
            return 0.0, 0
        
        # 在最大连通分量上计算
        largest = max(components, key=len)
        if len(largest) <= 1:
            return 0.0, 0
        
        nodes = list(largest)
        
        # 对于大分量使用采样
        sample_size = min(len(nodes), 100)
        if len(nodes) > 100:
            import random
            random.seed(42)
            sampled = random.sample(nodes, sample_size)
        else:
            sampled = nodes
        
        total_length = 0
        path_count = 0
        max_length = 0
        
        for i, source in enumerate(sampled):
            # BFS计算从source到所有其他节点的距离
            distances = self._bfs_distances(source, largest)
            
            for target, dist in distances.items():
                if target != source and dist > 0:
                    total_length += dist
                    path_count += 1
                    max_length = max(max_length, dist)
        
        avg_path = total_length / path_count if path_count > 0 else 0.0
        
        # 如果采样了，对直径进行估计修正
        if len(nodes) > 100:
            max_length = int(max_length * 1.2)  # 保守估计
        
        return avg_path, max_length
    
    def _bfs_distances(self, source: str, node_set: Set[str]) -> Dict[str, int]:
        """BFS计算从source到node_set中所有节点的距离"""
        distances = {source: 0}
        queue = deque([source])
        
        while queue:
            current = queue.popleft()
            for neighbor in self._get_neighbors(current):
                if neighbor in node_set and neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
        
        return distances
    
    # =========================================================
    # 6. 脆弱点报告生成
    # =========================================================
    
    def generate_vulnerability_report(self) -> VulnerabilityReport:
        """
        生成逻辑脆弱点报告
        
        综合所有拓扑分析结果，输出可执行的修复建议。
        """
        bridges = self.find_bridges()
        components = self.find_connected_components()
        sparse = self.get_sparse_nodes(threshold=0.3)
        layer_gaps = self.find_layer_gaps()
        
        # 桥边详情
        bridge_details = []
        for source, target in bridges:
            reason = "唯一连接路径"
            # 检查是否为层间桥边
            source_node = self.graph.nodes.get(source)
            target_node = self.graph.nodes.get(target)
            if source_node and target_node:
                s_layer = getattr(source_node, 'layer', '?')
                t_layer = getattr(target_node, 'layer', '?')
                if s_layer != t_layer:
                    reason = f"层间唯一通道({s_layer}->{t_layer})"
            bridge_details.append((source, target, reason))
        
        # 孤立簇(大小>1但无外部连接)
        isolated_clusters = [
            list(comp) for comp in components
            if len(comp) > 1 and len(comp) < len(self.graph.nodes) * 0.1
        ]
        
        # 生成修复建议
        recommendations = []
        
        if len(components) > 1:
            recommendations.append(
                f"发现{len(components)}个知识孤岛，建议添加{len(components)-1}条跨岛连接"
            )
        
        if bridges:
            recommendations.append(
                f"发现{len(bridges)}个逻辑脆弱点(桥边)，建议为关键桥边添加冗余路径"
            )
        
        if sparse:
            top_sparse = sparse[:5]
            recommendations.append(
                f"发现{len(sparse)}个稀疏知识区域，"
                f"优先补充: {', '.join(n for n, _ in top_sparse)}"
            )
        
        if layer_gaps:
            for src_layer, tgt_layer in layer_gaps:
                recommendations.append(
                    f"{src_layer}与{tgt_layer}之间层间传导不足，建议增加映射关系"
                )
        
        return VulnerabilityReport(
            bridge_edges=bridge_details,
            sparse_regions=[n for n, _ in sparse],
            isolated_clusters=isolated_clusters,
            layer_gaps=layer_gaps,
            recommendations=recommendations
        )
    
    # =========================================================
    # 7. 热税权重计算 (与现有热税系统集成)
    # =========================================================
    
    def compute_heat_tax_weight(self, node_id: str) -> float:
        """
        计算节点的热税权重因子
        
        基于拓扑位置的热税调整系数:
        - 桥边节点: 权重↑ (通过桥边的推理风险更高)
        - 稀疏节点: 权重↑ (知识不足导致推理不确定)
        - 孤立节点: 权重↑↑ (几乎无法推理)
        
        返回: 权重因子(>=1.0，1.0表示无额外热税)
        """
        if node_id not in self.graph.nodes:
            return 2.0  # 未知节点高熵税
        
        weight = 1.0
        
        # 桥边惩罚
        bridges = self.find_bridges()
        for source, target in bridges:
            if node_id in (source, target):
                weight += 0.5  # 桥边端点+50%热税
                break
        
        # 稀疏度惩罚
        clustering = self.local_clustering_coefficient(node_id)
        if clustering < 0.3:
            weight += (0.3 - clustering) * 2  # 最多+0.6
        
        # 孤立惩罚
        component = self.get_component_for_node(node_id)
        if component and len(component) == 1:
            weight += 1.0  # 孤立节点+100%热税
        
        return round(weight, 2)
    
    def get_path_heat_tax(self, path: List[str]) -> float:
        """
        计算路径的总热税
        
        路径热税 = 各节点热税权重之和
        """
        total = 0.0
        for node_id in path:
            total += self.compute_heat_tax_weight(node_id)
        return round(total, 2)


# =============================================================
# 增强版路径搜索 (集成拓扑度量)
# =============================================================

class TopologyAwarePathfinder:
    """
    拓扑感知路径搜索器
    
    在symbolic_engine_v2.GraphAlgorithms基础上增强:
    - 考虑节点热税权重
    - 优先避开桥边和稀疏区域
    - 支持层间传导优化
    
    L3隐喻说明:
    "同伦路径"在此实现为"热税等价的低权路径"，
    即多条到达相同目标的路径中，选择热税最低的。
    这不涉及数学上的同伦等价类计算。
    """
    
    def __init__(self, graph: MSSKnowledgeGraph, metrics_engine: TopologyMetricsEngine):
        self.graph = graph
        self.metrics = metrics_engine
    
    def find_lowest_heat_tax_path(
        self,
        start: str,
        end: str,
        max_depth: int = 10,
        avoid_bridges: bool = False
    ) -> Optional[Tuple[List[str], float]]:
        """
        查找热税最低的路径
        
        改进的Dijkstra算法，边权重 = 目标节点热税权重
        
        Args:
            start: 起始节点ID
            end: 目标节点ID
            max_depth: 最大搜索深度
            avoid_bridges: 是否避开桥边
        
        Returns:
            (路径节点列表, 总热税) 或 None
        """
        if start not in self.graph.nodes or end not in self.graph.nodes:
            return None
        
        # 获取桥边集合
        bridges = set()
        if avoid_bridges:
            for s, t in self.metrics.find_bridges():
                bridges.add(tuple(sorted([s, t])))
        
        # Dijkstra优先队列: (累计热税, 深度, 当前节点, 路径)
        queue = [(self.metrics.compute_heat_tax_weight(start), 0, start, [start])]
        visited = set()
        
        while queue:
            current_tax, depth, current, path = heapq.heappop(queue)
            
            if current == end:
                return path, current_tax
            
            if current in visited or depth >= max_depth:
                continue
            
            visited.add(current)
            
            # 遍历邻居
            for edge in self.graph._adjacency.get(current, []):
                neighbor = edge.target
                if neighbor in visited:
                    continue
                
                # 检查桥边
                if avoid_bridges:
                    edge_key = tuple(sorted([current, neighbor]))
                    if edge_key in bridges:
                        continue
                
                # 计算新热税
                neighbor_tax = self.metrics.compute_heat_tax_weight(neighbor)
                new_tax = current_tax + neighbor_tax
                
                new_path = path + [neighbor]
                heapq.heappush(queue, (new_tax, depth + 1, neighbor, new_path))
        
        return None
    
    def find_multiple_paths(
        self,
        start: str,
        end: str,
        max_paths: int = 3,
        max_depth: int = 10
    ) -> List[Tuple[List[str], float]]:
        """
        查找多条热税不同的路径
        
        用于比较不同推理路径的热税成本。
        """
        paths = []
        
        # 第一次搜索: 允许桥边
        result = self.find_lowest_heat_tax_path(start, end, max_depth, avoid_bridges=False)
        if result:
            paths.append(result)
        
        # 第二次搜索: 避开桥边
        if max_paths >= 2:
            result = self.find_lowest_heat_tax_path(start, end, max_depth, avoid_bridges=True)
            if result and result not in paths:
                paths.append(result)
        
        # 第三次搜索: 层优先(L1->L2->L3)
        if max_paths >= 3:
            result = self._find_layer_priority_path(start, end, max_depth)
            if result and result not in paths:
                paths.append(result)
        
        return paths
    
    def _find_layer_priority_path(
        self,
        start: str,
        end: str,
        max_depth: int = 10
    ) -> Optional[Tuple[List[str], float]]:
        """
        层优先路径: 优先L1->L2->L3方向
        
        层序: L1(0) < L2(1) < L3(2) < UNKNOWN(3)
        """
        layer_order = {"L1": 0, "L2": 1, "L3": 2, "UNKNOWN": 3}
        
        def get_layer_rank(node_id: str) -> int:
            node = self.graph.nodes.get(node_id)
            if node:
                return layer_order.get(getattr(node, 'layer', 'UNKNOWN'), 3)
            return 3
        
        # 修改Dijkstra: 惩罚层回退
        queue = [(0, 0, start, [start])]
        visited = set()
        
        while queue:
            current_cost, depth, current, path = heapq.heappop(queue)
            
            if current == end:
                tax = self.metrics.get_path_heat_tax(path)
                return path, tax
            
            if current in visited or depth >= max_depth:
                continue
            
            visited.add(current)
            
            current_rank = get_layer_rank(current)
            
            for edge in self.graph._adjacency.get(current, []):
                neighbor = edge.target
                if neighbor in visited:
                    continue
                
                neighbor_rank = get_layer_rank(neighbor)
                
                # 层回退惩罚
                layer_penalty = 0
                if neighbor_rank < current_rank:
                    layer_penalty = (current_rank - neighbor_rank) * 2
                
                neighbor_tax = self.metrics.compute_heat_tax_weight(neighbor)
                new_cost = current_cost + neighbor_tax + layer_penalty
                
                new_path = path + [neighbor]
                heapq.heappush(queue, (new_cost, depth + 1, neighbor, new_path))
        
        return None


# =============================================================
# 与现有系统的集成接口
# =============================================================

def enhance_graph_algorithms(graph_algorithms) -> TopologyMetricsEngine:
    """
    增强现有GraphAlgorithms实例
    
    为symbolic_engine_v2.GraphAlgorithms添加拓扑度量能力。
    
    Usage:
        from symbolic_engine_v2 import GraphAlgorithms
        from topology_metrics import enhance_graph_algorithms
        
        ga = GraphAlgorithms(knowledge_graph)
        topo = enhance_graph_algorithms(ga)
        metrics = topo.compute_all_metrics()
    """
    return TopologyMetricsEngine(graph_algorithms.graph)


# 兼容性别名(保持与提案术语的映射)
SimplicialComplexMetrics = TopologyMetricsEngine  # L3隐喻兼容
"""单纯复形度量 = 拓扑度量引擎(别名)"""
