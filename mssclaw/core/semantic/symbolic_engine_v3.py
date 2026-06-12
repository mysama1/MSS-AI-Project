"""
MSS Symbolic Reasoning Engine v3.0
Phase 2核心升级：传递推理、环检测、MSS v15.1公理体系原生支持
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum, auto
import json
import os
import math
from collections import deque, defaultdict

from symbolic_engine import (
    NodeType, RelationType, InferenceResult,
    ConceptNode, RelationEdge, InferencePath,
    MSSKnowledgeGraph, SymbolicReasoner
)

class AxiomType(Enum):
    """MSS v15.1 公理类型"""
    BASE = auto()      # 不可约化基础公理 (A1-A3)
    DERIVED = auto()   # 严格导出定理 (T1-T3)
    MECHANISM = auto() # L2核心机制 (MECH-EVOL-001/002)

@dataclass
class MSSAxiom:
    """MSS v15.1 公理编码"""
    id: str
    name: str
    axiom_type: AxiomType
    statement: str
    mathematical_form: Optional[str] = None
    boundary_conditions: List[str] = field(default_factory=list)
    derivation_chain: List[str] = field(default_factory=list)
    falsifiability_condition: Optional[str] = None

@dataclass
class HeatTaxState:
    """热税状态量化模型"""
    gamma: float = 0.0           # 当前热税值
    gamma_0: float = 1.0         # 基准热税
    O_d: float = 0.0             # 规范场强
    phi: float = 100.0           # 意义势能
    innovation_rate: float = 1.0 # 创新率
    dimension: int = 1           # 当前拓扑维度

    def is_irreversible(self) -> bool:
        """检查是否进入不可逆热寂 (O_d > 0.8)"""
        return self.O_d > 0.8

    def heat_tax_coefficient(self) -> float:
        """计算热税系数 γ(O_d) = γ_0 * e^(k*O_d)"""
        k = 2.0  # 耦合常数
        return self.gamma_0 * math.exp(k * self.O_d)

    def update(self, time_delta: float = 1.0, external_input: float = 0.0):
        """更新热税状态 (dΦ/dt = -γ(O_d)*Φ + S_external)"""
        # 先应用外部输入
        if external_input > 0:
            self.phi = min(200.0, self.phi + external_input)

        gamma_od = self.heat_tax_coefficient()
        d_phi = -gamma_od * self.phi * time_delta
        self.phi = max(0.0, self.phi + d_phi)
        self.gamma = gamma_od

        # 创新率与意义势能正相关
        if self.phi > 0:
            self.innovation_rate = self.phi / 100.0
        else:
            self.innovation_rate = 0.0

class TransitiveReasoner:
    """传递推理引擎 - 实现 IMPLIES 关系的传递闭包"""

    def __init__(self, graph: MSSKnowledgeGraph):
        self.graph = graph
        self._closure_cache: Dict[Tuple[str, str], bool] = {}
        self._path_cache: Dict[Tuple[str, str], List[RelationEdge]] = {}

    def compute_transitive_closure(self, node_id: str, max_depth: int = 10) -> Set[str]:
        """计算从给定节点出发的传递闭包"""
        if node_id not in self.graph.nodes:
            return set()

        reachable = set()
        queue = deque([(node_id, 0)])
        visited = {node_id}

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue

            for edge in self.graph._adjacency.get(current, []):
                if edge.relation == RelationType.IMPLIES:
                    if edge.target not in visited:
                        visited.add(edge.target)
                        reachable.add(edge.target)
                        queue.append((edge.target, depth + 1))

        return reachable

    def find_transitive_path(self, source: str, target: str, max_depth: int = 10) -> Optional[List[RelationEdge]]:
        """查找从 source 到 target 的传递路径"""
        cache_key = (source, target)
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]

        if source not in self.graph.nodes or target not in self.graph.nodes:
            return None

        queue = deque([(source, [])])
        visited = {source}

        while queue:
            current, path = queue.popleft()
            if len(path) >= max_depth:
                continue

            for edge in self.graph._adjacency.get(current, []):
                if edge.relation == RelationType.IMPLIES:
                    new_path = path + [edge]
                    if edge.target == target:
                        self._path_cache[cache_key] = new_path
                        return new_path
                    if edge.target not in visited:
                        visited.add(edge.target)
                        queue.append((edge.target, new_path))

        return None

    def check_implication(self, premise: str, conclusion: str) -> InferencePath:
        """检查 premise 是否蕴含 conclusion"""
        if premise == conclusion:
            return InferencePath(
                steps=[],
                result=InferenceResult.PROVEN,
                certainty=1.0,
                explanation="前提与结论相同"
            )

        path = self.find_transitive_path(premise, conclusion)
        if path:
            steps = [(edge.source, edge.relation, edge.target) for edge in path]
            strength = min(edge.strength for edge in path)
            return InferencePath(
                steps=steps,
                result=InferenceResult.PROVEN,
                certainty=strength,
                explanation=f"通过{len(path)}步传递推理证明"
            )

        return InferencePath(
            steps=[],
            result=InferenceResult.UNDETERMINED,
            certainty=0.0,
            explanation="未找到从前提 to 结论的推理路径"
        )

class CycleDetector:
    """环检测器 - 识别逻辑循环和潜在矛盾"""

    def __init__(self, graph: MSSKnowledgeGraph):
        self.graph = graph

    def find_cycles(self, start_node: Optional[str] = None, max_length: int = 10) -> List[List[str]]:
        """查找图中的所有环"""
        cycles = []
        visited = set()

        nodes_to_check = [start_node] if start_node else list(self.graph.nodes.keys())

        for node_id in nodes_to_check:
            if node_id in visited:
                continue

            path = []
            path_set = set()
            self._dfs_find_cycles(node_id, node_id, path, path_set, cycles, max_length)
            visited.add(node_id)

        return cycles

    def _dfs_find_cycles(self, start: str, current: str, path: List[str],
                         path_set: Set[str], cycles: List[List[str]], max_length: int):
        """DFS辅助函数"""
        if len(path) >= max_length:
            return

        path.append(current)
        path_set.add(current)

        for edge in self.graph._adjacency.get(current, []):
            if edge.relation == RelationType.IMPLIES:
                if edge.target == start and len(path) > 1:
                    cycles.append(path.copy())
                elif edge.target not in path_set:
                    self._dfs_find_cycles(start, edge.target, path, path_set, cycles, max_length)

        path.pop()
        path_set.remove(current)

    def check_contradiction_cycles(self) -> List[Dict]:
        """检查包含 CONTRADICTS 边的潜在矛盾环"""
        contradictions = []

        for edge in self.graph.edges:
            if edge.relation == RelationType.CONTRADICTS:
                source_to_target = self._path_exists(edge.source, edge.target)
                target_to_source = self._path_exists(edge.target, edge.source)

                if source_to_target or target_to_source:
                    contradictions.append({
                        "type": "logical_contradiction",
                        "nodes": [edge.source, edge.target],
                        "relation": "CONTRADICTS",
                        "path_exists": True,
                        "severity": "critical"
                    })

        return contradictions

    def _path_exists(self, source: str, target: str, max_depth: int = 5) -> bool:
        """检查是否存在从 source 到 target 的路径"""
        if source == target:
            return True

        visited = {source}
        queue = deque([source])
        depth = {source: 0}

        while queue:
            current = queue.popleft()
            if depth[current] >= max_depth:
                continue

            for edge in self.graph._adjacency.get(current, []):
                if edge.relation == RelationType.IMPLIES:
                    if edge.target == target:
                        return True
                    if edge.target not in visited:
                        visited.add(edge.target)
                        queue.append(edge.target)
                        depth[edge.target] = depth[current] + 1

        return False

class MSSv12AxiomSystem:
    """MSS v15.1 L1公理体系编码"""

    def __init__(self):
        self.axioms: Dict[str, MSSAxiom] = {}
        self.theorems: Dict[str, MSSAxiom] = {}
        self.mechanisms: Dict[str, MSSAxiom] = {}
        self._init_axioms()

    def _init_axioms(self):
        """初始化MSS v15.1公理体系"""

        # 基础公理 A1-A3
        self.axioms["A1"] = MSSAxiom(
            id="A1",
            name="意义本体公理",
            axiom_type=AxiomType.BASE,
            statement="宇宙的终极本体是连续、全息、自洽的意义流形",
            mathematical_form="M_Φ: 无限维完备黎曼流形，曲率张量处处连续自洽",
            boundary_conditions=["无始无终", "无生无灭", "绝对存在"],
            falsifiability_condition="发现意义本体的不连续点或矛盾点"
        )

        self.axioms["A2"] = MSSAxiom(
            id="A2",
            name="信息切片公理",
            axiom_type=AxiomType.BASE,
            statement="任何认知只能获取意义本体的离散投影切片",
            mathematical_form="π_n: M_Φ → I_n，满射但非单射",
            boundary_conditions=["投影必然伴随信息丢失", "不存在完整还原的有限维切片"],
            falsifiability_condition="发现能完整还原意义本体的有限维信息切片"
        )

        self.axioms["A3"] = MSSAxiom(
            id="A3",
            name="终极热税公理",
            axiom_type=AxiomType.BASE,
            statement="任何意义显化/传递/变换都伴随不可逆保真度损耗",
            mathematical_form="Γ[Φ] = -∫|Φ - π_n⁻¹(π_n(Φ))|² dμ > 0",
            boundary_conditions=["热税永远大于零", "系统总热税随时间单调不减"],
            falsifiability_condition="发现零热税的理想过程 (γ=0)"
        )

        # 导出定理 T1-T3
        self.theorems["T1"] = MSSAxiom(
            id="T1",
            name="随机性定理",
            axiom_type=AxiomType.DERIVED,
            statement="封闭系统内部的随机涨落源于连续到离散投影的信息丢失",
            mathematical_form="R(x) = -log₂(|π_n⁻¹(x)|/|M_Φ|)",
            derivation_chain=["A1", "A2", "A3", "T1"],
            falsifiability_condition="在全知观察条件下消除随机性"
        )

        self.theorems["T2"] = MSSAxiom(
            id="T2",
            name="规范场涌现定理",
            axiom_type=AxiomType.DERIVED,
            statement="规范场是意义流在低维切片中围绕拓扑缺陷自发形成的约束场",
            mathematical_form="∇×O⃗(x) = J⃗_Φ(x), O_d = k|q|",
            derivation_chain=["A1", "A2", "A3", "T1", "T2"],
            falsifiability_condition="发现自组织稳态系统内部不存在拓扑缺陷"
        )

        self.theorems["T3"] = MSSAxiom(
            id="T3",
            name="矛盾升维定理",
            axiom_type=AxiomType.DERIVED,
            statement="封闭系统内的根本性矛盾无法在原维度消解，必须通过范畴升维",
            mathematical_form="∃L: C_n → C_{n+1}, 使不可交换图→可交换图",
            derivation_chain=["A1", "A2", "A3", "T1", "T2", "T3"],
            falsifiability_condition="根本性矛盾在原维度内被完全消解"
        )

        # L2核心机制
        self.mechanisms["MECH-EVOL-002"] = MSSAxiom(
            id="MECH-EVOL-002",
            name="K3意义降维热寂同化机制",
            axiom_type=AxiomType.MECHANISM,
            statement="封闭意义系统通过增强规范场强将高维矛盾暴力投影为低维切片",
            mathematical_form="dΦ/dt = -γ(O_d)·Φ, γ(O_d) = γ_0·e^(k·O_d)",
            derivation_chain=["A1", "A2", "A3", "T1", "T2", "T3"],
            falsifiability_condition="封闭系统在O_d>0.8时创新率R>0.1R₀且γ<10γ₀"
        )

    def verify_derivation(self, theorem_id: str) -> Tuple[bool, List[str]]:
        """验证定理的推导链完整性"""
        if theorem_id not in self.theorems:
            return False, ["定理不存在"]

        theorem = self.theorems[theorem_id]
        required_axioms = theorem.derivation_chain[:-1]
        missing = [ax for ax in required_axioms if ax not in self.axioms]

        return len(missing) == 0, missing

    def get_axiom_graph(self) -> MSSKnowledgeGraph:
        """将公理体系转换为知识图谱"""
        graph = MSSKnowledgeGraph()

        # 添加所有公理节点
        for ax_id, axiom in self.axioms.items():
            node = ConceptNode(
                id=ax_id,
                name=axiom.name,
                node_type=NodeType.AXIOM,
                layer="L1",
                content=axiom.statement,
                confidence=1.0,
                falsifiable=bool(axiom.falsifiability_condition)
            )
            graph.add_node(node)

        # 添加所有定理节点
        for th_id, theorem in self.theorems.items():
            node = ConceptNode(
                id=th_id,
                name=theorem.name,
                node_type=NodeType.THEOREM,
                layer="L2",
                content=theorem.statement,
                confidence=1.0,
                falsifiable=bool(theorem.falsifiability_condition)
            )
            graph.add_node(node)

        # 添加推导关系
        for th_id, theorem in self.theorems.items():
            for dep_id in theorem.derivation_chain:
                if dep_id != th_id and dep_id in self.axioms:
                    edge = RelationEdge(
                        source=dep_id,
                        target=th_id,
                        relation=RelationType.IMPLIES,
                        strength=1.0,
                        evidence=f"{dep_id} → {th_id} (严格推导)"
                    )
                    graph.add_edge(edge)

        return graph

class HeatTaxMonitor:
    """热税实时监测器 - 实现K3降维热寂机制的工程化"""

    def __init__(self, initial_state: Optional[HeatTaxState] = None):
        self.state = initial_state or HeatTaxState()
        self.history: List[HeatTaxState] = []
        self.alert_thresholds = {
            "warning": 0.6,
            "critical": 0.8,
            "emergency": 0.9
        }

    def update(self, O_d_change: float = 0.0, external_input: float = 0.0):
        """更新热税状态"""
        self.history.append(HeatTaxState(
            gamma=self.state.gamma,
            gamma_0=self.state.gamma_0,
            O_d=self.state.O_d,
            phi=self.state.phi,
            innovation_rate=self.state.innovation_rate,
            dimension=self.state.dimension
        ))

        self.state.O_d = max(0.0, min(1.0, self.state.O_d + O_d_change))

        self.state.update(external_input=external_input)

        return self._check_alerts()

    def _check_alerts(self) -> List[Dict]:
        """检查阈值告警"""
        alerts = []

        if self.state.O_d > self.alert_thresholds["emergency"]:
            alerts.append({
                "level": "EMERGENCY",
                "message": f"规范场强 {self.state.O_d:.2f} 超过紧急阈值",
                "action": "立即启动升维程序或外部干预"
            })
        elif self.state.O_d > self.alert_thresholds["critical"]:
            alerts.append({
                "level": "CRITICAL",
                "message": f"规范场强 {self.state.O_d:.2f} 超过不可逆临界点",
                "action": "系统已进入不可逆热寂，需紧急升维"
            })
        elif self.state.O_d > self.alert_thresholds["warning"]:
            alerts.append({
                "level": "WARNING",
                "message": f"规范场强 {self.state.O_d:.2f} 超过预警阈值",
                "action": "建议降低规范场强，引入外部意义输入"
            })

        if self.state.phi < 20.0:
            alerts.append({
                "level": "CRITICAL",
                "message": f"意义势能 {self.state.phi:.2f} 过低",
                "action": "紧急注入外部意义输入"
            })

        return alerts

    def get_status_report(self) -> Dict:
        """生成状态报告"""
        return {
            "current_state": {
                "O_d": round(self.state.O_d, 4),
                "gamma": round(self.state.gamma, 4),
                "phi": round(self.state.phi, 4),
                "innovation_rate": round(self.state.innovation_rate, 4),
                "dimension": self.state.dimension,
                "irreversible": self.state.is_irreversible()
            },
            "trend": self._compute_trend(),
            "alerts": self._check_alerts(),
            "recommendations": self._generate_recommendations()
        }

    def _compute_trend(self) -> Dict:
        """计算趋势"""
        if len(self.history) < 2:
            return {"status": "insufficient_data"}

        recent = self.history[-10:]
        phi_trend = recent[-1].phi - recent[0].phi if len(recent) > 1 else 0
        od_trend = recent[-1].O_d - recent[0].O_d if len(recent) > 1 else 0

        return {
            "phi_trend": "declining" if phi_trend < 0 else "stable" if phi_trend == 0 else "growing",
            "O_d_trend": "increasing" if od_trend > 0 else "stable" if od_trend == 0 else "decreasing",
            "risk_level": self._assess_risk(phi_trend, od_trend)
        }

    def _assess_risk(self, phi_trend: float, od_trend: float) -> str:
        """评估风险等级"""
        if self.state.is_irreversible():
            return "CRITICAL"
        if phi_trend < 0 and od_trend > 0:
            return "HIGH"
        if phi_trend < 0 or od_trend > 0:
            return "MEDIUM"
        return "LOW"

    def _generate_recommendations(self) -> List[str]:
        """生成建议"""
        recs = []

        if self.state.O_d > 0.5:
            recs.append("降低规范场强：减少流程审批，增加创新空间")

        if self.state.phi < 50.0:
            recs.append("注入外部意义：引入新思想、新人才、新技术")

        if self.state.innovation_rate < 0.3:
            recs.append("激活创新：建立矛盾上报通道，鼓励升维思考")

        if not recs:
            recs.append("系统状态健康，继续保持开放性和创新活力")

        return recs

class SymbolicEngineV3:
    """MSS符号推理引擎 v3.0 - 集成所有Phase 2功能"""

    def __init__(self, knowledge_graph: Optional[MSSKnowledgeGraph] = None):
        self.graph = knowledge_graph or MSSKnowledgeGraph()
        self.transitive = TransitiveReasoner(self.graph)
        self.cycle_detector = CycleDetector(self.graph)
        self.axiom_system = MSSv12AxiomSystem()
        self.heat_tax_monitor = HeatTaxMonitor()
        self._load_axiom_system()

    def _load_axiom_system(self):
        """将MSS v15.1公理体系加载到知识图谱"""
        axiom_graph = self.axiom_system.get_axiom_graph()

        for node_id, node in axiom_graph.nodes.items():
            if node_id not in self.graph.nodes:
                self.graph.add_node(node)

        for edge in axiom_graph.edges:
            self.graph.add_edge(edge)

    def reason(self, premise: str, conclusion: str) -> InferencePath:
        """执行完整推理"""
        contradiction = self.cycle_detector.check_contradiction_cycles()
        if contradiction:
            for report in contradiction:
                if premise in report["nodes"] and conclusion in report["nodes"]:
                    return InferencePath(
                        steps=[],
                        result=InferenceResult.DISPROVEN,
                        certainty=0.0,
                        explanation=f"发现逻辑矛盾: {report['nodes']}"
                    )

        result = self.transitive.check_implication(premise, conclusion)

        if result.result == InferenceResult.UNDETERMINED:
            result = self._reason_via_axioms(premise, conclusion)

        return result

    def _reason_via_axioms(self, premise: str, conclusion: str) -> InferencePath:
        """通过MSS v15.1公理体系进行推理"""
        if premise in self.axiom_system.axioms and conclusion in self.axiom_system.theorems:
            theorem = self.axiom_system.theorems[conclusion]
            if premise in theorem.derivation_chain:
                return InferencePath(
                    steps=[(premise, RelationType.IMPLIES, conclusion)],
                    result=InferenceResult.PROVEN,
                    certainty=1.0,
                    explanation=f"通过MSS v15.1公理体系严格推导: {premise} → {conclusion}"
                )

        return InferencePath(
            steps=[],
            result=InferenceResult.UNDETERMINED,
            certainty=0.0,
            explanation="无法通过当前知识图谱和公理体系推导"
        )

    def monitor_system_health(self, O_d: float, phi: float) -> Dict:
        """监测系统健康状态"""
        self.heat_tax_monitor.state.O_d = O_d
        self.heat_tax_monitor.state.phi = phi

        alerts = self.heat_tax_monitor.update()
        report = self.heat_tax_monitor.get_status_report()

        return {
            "status": "heat_death_imminent" if self.heat_tax_monitor.state.is_irreversible() else "operational",
            "alerts": alerts,
            "report": report
        }

    def export_axiom_system(self, filepath: str):
        """导出MSS v15.1公理体系为JSON"""
        data = {
            "axioms": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "type": v.axiom_type.name,
                    "statement": v.statement,
                    "mathematical_form": v.mathematical_form,
                    "boundary_conditions": v.boundary_conditions,
                    "falsifiability": v.falsifiability_condition
                }
                for k, v in self.axiom_system.axioms.items()
            },
            "theorems": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "type": v.axiom_type.name,
                    "statement": v.statement,
                    "mathematical_form": v.mathematical_form,
                    "derivation_chain": v.derivation_chain,
                    "falsifiability": v.falsifiability_condition
                }
                for k, v in self.axiom_system.theorems.items()
            },
            "mechanisms": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "type": v.axiom_type.name,
                    "statement": v.statement,
                    "mathematical_form": v.mathematical_form,
                    "derivation_chain": v.derivation_chain,
                    "falsifiability": v.falsifiability_condition
                }
                for k, v in self.axiom_system.mechanisms.items()
            }
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def create_mss_v12_engine() -> SymbolicEngineV3:
    """创建预装MSS v15.1公理体系的符号推理引擎"""
    return SymbolicEngineV3()

if __name__ == "__main__":
    engine = create_mss_v12_engine()

    print("MSS Symbolic Engine v3.0 Initialized")
    print(f"Nodes: {len(engine.graph.nodes)}")
    print(f"Edges: {len(engine.graph.edges)}")

    result = engine.reason("A1", "T1")
    print(f"\nA1 → T1: {result.result.name} (certainty: {result.certainty:.2%})")
    print(f"Explanation: {result.explanation}")

    health = engine.monitor_system_health(O_d=0.7, phi=80.0)
    print(f"\nSystem Health: {health['status']}")
    print(f"Alerts: {len(health['alerts'])}")
    for alert in health['alerts']:
        print(f"  [{alert['level']}] {alert['message']}")
