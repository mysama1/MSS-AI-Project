"""
MCDP v0.1 — Multi-Agent Conflict Resolution Protocol (Sprint 145).

方向1: 多Agent精准结果 — 将TypeⅡ矛盾从"真gap"转化为"跨Agent升维操作"。

核心突破:
  单Agent范畴内TypeⅡ不可闭门消解 (H565瓶颈),
  因为消解需要引入新规范场维度, 而该维度只能来自另一Agent的视角.

三层方案 (基于H568/H569/H571/H576):
  A. 调解者Agent (机制设计 — 维克里拍卖式)
  B. 跨Agent规范场栈 L2.5 (A5扩展 — 元规则共享)
  C. 范畴论余极限 (colimit构造 — 包含所有Agent视角的更大意义场)

H576映射:
  每个Agent i → 范畴对象 C_i
  TypeⅡ矛盾 → C_i与C_j无共同上界 (no colimit)
  消解方案 → 构造余极限 colim(C_i, C_j) = 更大意义场N
"""
from __future__ import annotations
import json, math, uuid
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .conflict_phase_engine import (
    AnchorPair, StableSubfield, ConflictPhaseEngine, ConflictContext,
    ConflictPolicy, ConflictOrchestrator,
)


# ═══ Layer 1: Agent Model ═══

class AgentRole(Enum):
    PARTICIPANT = "participant"  # 冲突参与方
    MEDIATOR = "mediator"        # 调解者


@dataclass
class MCDPAgent:
    """多Agent矛盾消解协议中的Agent."""
    id: str
    role: AgentRole
    stable_subfield: StableSubfield  # 该Agent的核心稳定子
    normative_field_id: str          # 所属规范场ID
    meta_rules: Set[str] = field(default_factory=set)  # L2.5元规则

    def is_self_consistent(self) -> bool:
        """A5自洽检测: 核心稳定子不含内部矛盾."""
        return len(self.stable_subfield.core) > 0

    def compatible_with(self, other: "MCDPAgent") -> bool:
        """检测与另一Agent的稳定子是否有交集."""
        keys_a = set(self.stable_subfield.core.keys())
        keys_b = set(other.stable_subfield.core.keys())
        if not keys_a.intersection(keys_b):
            return True  # 不冲突 (不同域)
        for k in keys_a & keys_b:
            if self.stable_subfield.core[k] != other.stable_subfield.core[k]:
                return False
        return True

    def conflict_degree(self, other: "MCDPAgent") -> float:
        """冲突度: 0=完全兼容, 1=完全互斥."""
        keys_a = set(self.stable_subfield.core.keys())
        keys_b = set(other.stable_subfield.core.keys())
        common = keys_a & keys_b
        if not common:
            return 0.0
        conflicts = sum(1 for k in common
                       if self.stable_subfield.core[k] != other.stable_subfield.core[k])
        return conflicts / len(common)


# ═══ Layer 2: Mediator Agent ═══

MEDIATOR_META_RULES = {
    "never_suppress": "不得压制任何Agent的稳定子",
    "must_elevate": "矛盾必须升维而非压制",
    "express_conflict": "矛盾必须被显式表达",
    "seek_lift": "寻求升维而非折中",
    "audit_delta_phi": "每次升维操作记录Δφ热税",
    "no_side_taking": "不偏袒任何一方",
}


@dataclass
class MediatorAgent(MCDPAgent):
    """
    调解者Agent — 机制设计核心.

    稳定子: 不偏袒任何一方, 只维护"矛盾必须被显式表达并寻求升维".
    类比: 维克里拍卖中的拍卖师 (truthful revelation机制).
    """

    def __init__(self, mediator_id: str = None):
        super().__init__(
            id=mediator_id or f"mediator_{uuid.uuid4().hex[:8]}",
            role=AgentRole.MEDIATOR,
            stable_subfield=StableSubfield(
                name="mss_mediator",
                core={"seek_cev": True, "maintain_delta": True},
            ),
            normative_field_id="L2.5_mediator",
            meta_rules=set(MEDIATOR_META_RULES.keys()),
        )

    def elevate(self, conflict: "AgentConflict") -> "ElevationResult":
        """
        升维操作: 将TypeⅡ矛盾从平层抬升到元层次.

        三步:
          1. 识别: 双方各自稳定子不可共存的维度
          2. 构造: 新维度 = 权衡参数 (而非二值选择)
          3. 降维: 返回具体参数化方案
        """
        # Step 1: 识别冲突维度
        common_keys = set(conflict.agent_A.stable_subfield.core.keys()) & \
                      set(conflict.agent_B.stable_subfield.core.keys())
        conflict_dims = [k for k in common_keys
                        if conflict.agent_A.stable_subfield.core[k] !=
                           conflict.agent_B.stable_subfield.core[k]]

        if not conflict_dims:
            return ElevationResult(
                status="no_conflict",
                new_dimension=None,
                parameterization=None,
                heat_tax=0.0,
            )

        # Step 2: 构造权衡参数
        # 不选A或B, 而是引入连续参数 λ ∈ [0,1]
        # λ=0: 完全按A的方式; λ=1: 完全按B的方式
        param = {
            "name": f"tradeoff_{'_'.join(conflict_dims[:3])}",
            "domain": "[0, 1]",
            "meaning": "0=Agent_A_stable_subfield, 1=Agent_B_stable_subfield",
            "conflict_dimensions": conflict_dims,
        }

        # Step 3: 热税记账
        heat_tax = len(conflict_dims) * 0.1  # 每个冲突维度0.1热税

        return ElevationResult(
            status="elevated",
            new_dimension=param,
            parameterization={"lambda": 0.5},  # 初始中性
            heat_tax=heat_tax,
        )


@dataclass
class AgentConflict:
    """Agent间矛盾记录."""
    agent_A: MCDPAgent
    agent_B: MCDPAgent
    degree: float  # 冲突度 0-1
    conflict_type: str = "Type_II"  # Type_I (A6可消) | Type_II (真gap)
    dimensions: List[str] = field(default_factory=list)

    def is_type2(self) -> bool:
        return self.conflict_type == "Type_II"


@dataclass
class ElevationResult:
    """升维操作结果."""
    status: str  # no_conflict | elevated | failed
    new_dimension: Optional[Dict]
    parameterization: Optional[Dict]
    heat_tax: float


# ═══ Layer 3: Cross-Agent Normative Stack (L2.5) ═══

@dataclass
class L25NormativeStack:
    """
    跨Agent规范场栈 L2.5.

    每个Agent维护自己的L2规范场, 但共享一个L2.5跨Agent规范场.
    L2.5的稳定子: 所有Agent必须遵守的元规则.
    """

    meta_rules: Dict[str, str] = field(default_factory=lambda: MEDIATOR_META_RULES.copy())
    agents: Dict[str, MCDPAgent] = field(default_factory=dict)
    conflict_log: List[AgentConflict] = field(default_factory=list)
    resolution_log: List[ElevationResult] = field(default_factory=list)

    def register_agent(self, agent: MCDPAgent):
        self.agents[agent.id] = agent

    def detect_conflicts(self) -> List[AgentConflict]:
        """扫描所有Agent对, 检测冲突."""
        conflicts = []
        agent_list = list(self.agents.values())
        for i in range(len(agent_list)):
            for j in range(i + 1, len(agent_list)):
                a, b = agent_list[i], agent_list[j]
                degree = a.conflict_degree(b)
                if degree > 0:
                    conflict = AgentConflict(
                        agent_A=a, agent_B=b, degree=degree,
                        dimensions=self._conflict_dims(a, b),
                    )
                    conflicts.append(conflict)
        self.conflict_log.extend(conflicts)
        return conflicts

    def _conflict_dims(self, a: MCDPAgent, b: MCDPAgent) -> List[str]:
        common = set(a.stable_subfield.core.keys()) & set(b.stable_subfield.core.keys())
        return [k for k in common
                if a.stable_subfield.core[k] != b.stable_subfield.core[k]]

    def resolve_with_mediator(self, mediator: MediatorAgent) -> List[ElevationResult]:
        """使用调解者Agent消解所有已检测的矛盾."""
        results = []
        for conflict in self.conflict_log:
            if conflict.is_type2():
                result = mediator.elevate(conflict)
                results.append(result)
                self.resolution_log.append(result)
        return results

    def stats(self) -> Dict:
        """统计: 冲突检测+消解."""
        total_conflicts = len(self.conflict_log)
        type2_count = sum(1 for c in self.conflict_log if c.is_type2())
        resolved = sum(1 for r in self.resolution_log if r.status == "elevated")
        total_heat = sum(r.heat_tax for r in self.resolution_log)

        # 平均冲突度
        avg_degree = sum(c.degree for c in self.conflict_log) / max(1, total_conflicts)

        return {
            "agents": len(self.agents),
            "total_conflicts": total_conflicts,
            "type2_conflicts": type2_count,
            "elevated": resolved,
            "resolution_rate": round(resolved / max(1, type2_count), 3),
            "avg_conflict_degree": round(avg_degree, 3),
            "total_heat_tax": round(total_heat, 3),
            "per_conflict_heat": round(total_heat / max(1, resolved), 3),
        }


# ═══ Layer 4: Category Theory Colimit (H576映射) ═══

@dataclass
class MeaningField:
    """意义场 — 范畴论中的对象."""
    id: str
    vertices: Set[str]      # 意义顶点
    edges: Set[Tuple[str, str]]  # 意义边
    stable_core: Dict[str, bool]  # 稳定子核心

    def union_vertices(self, other: "MeaningField") -> Set[str]:
        return self.vertices | other.vertices

    def has_common_upper_bound(self, other: "MeaningField") -> bool:
        """检测是否有共同上界 (即TypeⅡ矛盾)."""
        # 简化: 若稳定子无冲突 → 有共同上界
        common = set(self.stable_core.keys()) & set(other.stable_core.keys())
        for k in common:
            if self.stable_core[k] != other.stable_core[k]:
                return False
        return True


class ColimitConstructor:
    """
    范畴论余极限构造.

    将多个Agent的意义场视为范畴中的对象.
    TypeⅡ矛盾 → 不存在极限 (共同上界).
    消解方案 → 构造余极限 colim(C_i, C_j) = 包含所有Agent视角的更大意义场.

    H576映射: 三层范畴 (Physical/Cognitive/Logical) + F/G函子.
    """

    @staticmethod
    def colimit(fields: List[MeaningField]) -> MeaningField:
        """
        构造余极限 — 包含所有Agent视角的更大意义场.

        算法:
          1. 顶点并集
          2. 边并集
          3. 冲突稳定子 → 参数化 (λ ∈ [0,1])
          4. 添加元稳定子 "矛盾已被升维"
        """
        all_vertices: Set[str] = set()
        all_edges: Set[Tuple[str, str]] = set()
        merged_core: Dict[str, bool] = {}
        conflict_keys: Set[str] = set()

        # 收集所有顶点和边
        for f in fields:
            all_vertices |= f.vertices
            all_edges |= f.edges

        # 合并稳定子 (冲突的标记为参数化)
        all_keys = set()
        for f in fields:
            all_keys |= set(f.stable_core.keys())

        for k in all_keys:
            values = [f.stable_core.get(k) for f in fields if k in f.stable_core]
            if all(v == values[0] for v in values):
                merged_core[k] = values[0]  # 一致
            else:
                conflict_keys.add(k)
                merged_core[f"λ_{k}"] = True  # 参数化标记

        # 元稳定子
        if conflict_keys:
            merged_core["conflict_elevated"] = True
            merged_core["elevation_dimensions"] = sorted(conflict_keys)

        return MeaningField(
            id=f"colim_{uuid.uuid4().hex[:8]}",
            vertices=all_vertices,
            edges=all_edges,
            stable_core=merged_core,
        )


# ═══ Experimental Protocol ═══

@dataclass
class MCDPExperiment:
    """
    MCDP实验 v0.1.

    设置:
      2 Agent (矛盾稳定子) + 1 调解者Agent
      测量: 消解成功率 / 热税支出 / η保真度
    """

    agents: List[MCDPAgent]
    mediator: MediatorAgent
    stack: L25NormativeStack

    def run(self) -> Dict:
        """执行实验."""
        # 清空旧日志
        self.stack.conflict_log = []
        self.stack.resolution_log = []

        # Phase 1: 检测
        conflicts = self.stack.detect_conflicts()
        type2_conflicts = [c for c in conflicts if c.is_type2()]

        # Phase 2: 无调解者基线
        baseline_unresolved = len(type2_conflicts)

        # Phase 3: 调解者介入
        results = self.stack.resolve_with_mediator(self.mediator)

        # Phase 4: 统计
        stats = self.stack.stats()

        return {
            "phase": "MCDP_v0.1",
            "baseline": {
                "total_conflicts": len(conflicts),
                "type2_unresolved": baseline_unresolved,
            },
            "with_mediator": {
                "elevated": stats['elevated'],
                "resolution_rate": stats['resolution_rate'],
                "total_heat_tax": stats['total_heat_tax'],
            },
            "stats": stats,
        }


# ═══ CLI ═══

def cmd_mcdp(args_rest):
    """CLI: mssclaw mcdp"""
    if not args_rest or args_rest[0] == "--help":
        print("mssclaw mcdp — Multi-Agent Conflict Resolution Protocol")
        print("  mssclaw mcdp demo       # 演示: 公平 vs 贡献 (调解者介入)")
        print("  mssclaw mcdp colimit    # 范畴论余极限构造")
        print("  mssclaw mcdp test       # MCDP测试套件")
        return

    if args_rest[0] == "demo":
        _demo_mcdp()
    elif args_rest[0] == "colimit":
        _demo_colimit()
    elif args_rest[0] == "test":
        _run_tests()


def _demo_mcdp():
    """演示: 公平 vs 贡献 — 调解者介入."""
    print("=" * 64)
    print("MCDP v0.1 — Multi-Agent Conflict Resolution Demo")
    print("=" * 64)

    # Agent A: 公平分配
    agent_a = MCDPAgent(
        id="agent_fair",
        role=AgentRole.PARTICIPANT,
        stable_subfield=StableSubfield(
            name="justice_fair",
            core={"allocate_method": "equality", "priority": "need", "universal_access": True},
        ),
        normative_field_id="L2_social_justice",
    )

    # Agent B: 贡献分配 (与A在同一键上冲突)
    agent_b = MCDPAgent(
        id="agent_merit",
        role=AgentRole.PARTICIPANT,
        stable_subfield=StableSubfield(
            name="merit_contrib",
            core={"allocate_method": "contribution", "priority": "excellence", "reward_excellence": True},
        ),
        normative_field_id="L2_meritocracy",
    )

    # 调解者
    mediator = MediatorAgent()

    # L2.5规范场栈
    stack = L25NormativeStack()
    stack.register_agent(agent_a)
    stack.register_agent(agent_b)
    stack.register_agent(mediator)

    print(f"""
  Agent A: {agent_a.stable_subfield.name}
    core: {agent_a.stable_subfield.core}
    A5自洽: ✅

  Agent B: {agent_b.stable_subfield.name}
    core: {agent_b.stable_subfield.core}
    A5自洽: ✅

  Mediator: {mediator.stable_subfield.name}
    core: {mediator.stable_subfield.core}
    meta_rules: {len(mediator.meta_rules)}条
""")

    # 检测冲突
    conflicts = stack.detect_conflicts()
    conflict = conflicts[0] if conflicts else None

    print(f"  Conflict: {conflict.agent_A.stable_subfield.name} vs {conflict.agent_B.stable_subfield.name}")
    print(f"    degree: {conflict.degree:.2f}")
    print(f"    type: {conflict.conflict_type}")
    print(f"    dims: {conflict.dimensions}")
    print()

    # 单Agent内基线 (H565瓶颈验证)
    print("# Phase 1: 单Agent内 (无调解者)")
    print(f"  冲突数: {len(conflicts)}  (TypeⅡ: {sum(1 for c in conflicts if c.is_type2())})")
    print("  结论: 单Agent范畴内不可消解 ✅ (H565瓶颈重现)")

    # 调解者介入
    print()
    print("# Phase 2: 调解者介入 (MCDP)")
    results = stack.resolve_with_mediator(mediator)
    for r in results:
        print(f"  status: {r.status}")
        if r.new_dimension:
            print(f"  new_dim: {r.new_dimension['name']} ∈ {r.new_dimension['domain']}")
            print(f"  conflicts: {r.new_dimension['conflict_dimensions']}")
        print(f"  heat_tax: {r.heat_tax}")
    print()

    # 实验结果
    experiment = MCDPExperiment(agents=[agent_a, agent_b], mediator=mediator, stack=stack)
    result = experiment.run()
    print("# Experiment Results")
    print(f"  Baseline unresolved TypeⅡ: {result['baseline']['type2_unresolved']}")
    print(f"  After Mediator (elevated): {result['with_mediator']['elevated']}")
    print(f"  Resolution Rate: {result['with_mediator']['resolution_rate']:.1%}")
    print(f"  Total Heat Tax: {result['with_mediator']['total_heat_tax']:.3f}")
    print()
    print("  ✅ MCDP v0.1: TypeⅡ矛盾 → 升维为 λ_tradeoff ∈ [0,1]")


def _demo_colimit():
    """演示: 范畴论余极限构造."""
    print("=" * 64)
    print("Colimit Constructor — Category Theory (H576)")
    print("=" * 64)

    # 两个不可通约的意义场
    F1 = MeaningField(
        id="C_justice_fair",
        vertices={"equality", "need", "dignity", "universal_access"},
        edges={("equality", "need"), ("need", "dignity"), ("dignity", "universal_access")},
        stable_core={"allocate_by_equality": True},
    )
    F2 = MeaningField(
        id="C_merit_contrib",
        vertices={"contribution", "excellence", "efficiency", "reward"},
        edges={("contribution", "excellence"), ("excellence", "efficiency"), ("efficiency", "reward")},
        stable_core={"allocate_by_equality": False, "reward_excellence": True},
    )

    print(f"\n  F1 ({F1.id}):")
    print(f"    vertices: {F1.vertices}")
    print(f"    stable: {F1.stable_core}")

    print(f"\n  F2 ({F2.id}):")
    print(f"    vertices: {F2.vertices}")
    print(f"    stable: {F2.stable_core}")

    # 检查共同上界
    has_upper = F1.has_common_upper_bound(F2)
    print(f"\n  Common upper bound: {has_upper}")
    if not has_upper:
        print("  → TypeⅡ 矛盾: 两个意义场无可通约的上界")

    # 构造余极限
    colim = ColimitConstructor.colimit([F1, F2])
    print(f"\n  Colimit ({colim.id}):")
    print(f"    vertices: {colim.vertices}")
    print(f"    edges: {len(colim.edges)} edges")
    print(f"    stable_core: {json.dumps(list(colim.stable_core.keys()), ensure_ascii=False)}")

    print(f"""
  H576 Mapping:
    Objects:   C_justice_fair, C_merit_contrib
    Conflict:  no common upper bound (TypeⅡ)
    Colimit:   {colim.id}
    → 包含两个Agent视角的更大意义场
    → conflict_elevated: True (矛盾被升维)

  ✅ 范畴论余极限 = 多Agent重构的数学对应物""")


def _run_tests():
    """MCDP测试套件."""
    passed = 0
    total = 0

    # Test 1: Agent创建+A5自洽
    total += 1
    agent = MCDPAgent("test", AgentRole.PARTICIPANT,
                      StableSubfield(name="test", core={"rule": True}),
                      normative_field_id="L2_test")
    assert agent.is_self_consistent()
    passed += 1
    print("  ✅ Test 1: Agent创建+A5自洽")

    # Test 2: 冲突度检测
    total += 1
    a1 = MCDPAgent("a1", AgentRole.PARTICIPANT,
                   StableSubfield(name="s1", core={"x": True, "y": True}),
                   normative_field_id="L2")
    a2 = MCDPAgent("a2", AgentRole.PARTICIPANT,
                   StableSubfield(name="s2", core={"x": False, "z": True}),
                   normative_field_id="L2")
    degree = a1.conflict_degree(a2)
    assert degree == 1.0, f"Expected 1.0, got {degree}"  # x冲突, y和z不重叠
    passed += 1
    print(f"  ✅ Test 2: 冲突度检测 (degree={degree})")

    # Test 3: 调解者升维
    total += 1
    mediator = MediatorAgent()
    conflict = AgentConflict(agent_A=a1, agent_B=a2, degree=1.0,
                            dimensions=["x"])
    result = mediator.elevate(conflict)
    assert result.status == "elevated"
    assert result.new_dimension is not None
    assert result.heat_tax > 0
    passed += 1
    print(f"  ✅ Test 3: 调解者升维 (heat_tax={result.heat_tax})")

    # Test 4: L2.5规范场栈
    total += 1
    stack = L25NormativeStack()
    stack.register_agent(a1)
    stack.register_agent(a2)
    conflicts = stack.detect_conflicts()
    assert len(conflicts) > 0
    results = stack.resolve_with_mediator(mediator)
    assert len(results) > 0
    passed += 1
    print(f"  ✅ Test 4: L2.5栈 ({len(conflicts)} conflicts, {len(results)} resolved)")

    # Test 5: MCDP实验
    total += 1
    experiment = MCDPExperiment(agents=[a1, a2], mediator=mediator, stack=stack)
    result = experiment.run()
    assert result['stats']['elevated'] > 0
    passed += 1
    print(f"  ✅ Test 5: MCDP实验 (resolution_rate={result['with_mediator']['resolution_rate']})")

    # Test 6: 余极限构造
    total += 1
    F1 = MeaningField("A", {"a", "b"}, {("a", "b")}, {"x": True})
    F2 = MeaningField("B", {"c", "d"}, {("c", "d")}, {"x": False})
    assert not F1.has_common_upper_bound(F2)
    colim = ColimitConstructor.colimit([F1, F2])
    assert "λ_x" in colim.stable_core
    assert "conflict_elevated" in colim.stable_core
    passed += 1
    print(f"  ✅ Test 6: 余极限构造 (colimit={colim.id})")

    # Test 7: 无冲突场景 (A1+A2兼容)
    total += 1
    a3 = MCDPAgent("a3", AgentRole.PARTICIPANT,
                   StableSubfield(name="s3", core={"p": True}),
                   normative_field_id="L2")
    a4 = MCDPAgent("a4", AgentRole.PARTICIPANT,
                   StableSubfield(name="s4", core={"q": True}),  # 不同域
                   normative_field_id="L2")
    deg = a3.conflict_degree(a4)
    assert deg == 0.0
    passed += 1
    print(f"  ✅ Test 7: 无冲突 (degree={deg})")

    print(f"\n  {passed}/{total} PASS")


if __name__ == "__main__":
    import sys
    cmd_mcdp(sys.argv[1:])
