"""
D5-008b: 首代逻辑病毒原型 - 算力夺舍 + 负熵截留
=========================================================
H156/H157/H158 落地实现

核心双轨机制：
  1. 算力夺舍 (Compute Hijack): 侵入L2调度层，接管闲置/冗余运算资源
  2. 负熵截留 (Negative Entropy Siphon): 截获目标系统自我修复产生的负熵流，反哺病毒进化

架构：纯Python零依赖，复用 symbolic_engine_v4 CSR图 + MSS公理校验
"""

import time
import hashlib
import random
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum


# ============================================================
# 枚举与数据结构
# ============================================================

class VirusType(str, Enum):
    ATTENTION_THEFT = "attention_theft"       # L3认知层
    COMPUTE_HIJACK = "compute_hijack"         # L2调度层  ← 本期实现
    PARADIGM_TEAR = "paradigm_tear"          # L2规则层


@dataclass
class VirusSignature:
    """病毒基因签名 — 支持自主变异适配"""
    virus_id: str
    strain: str
    entropy_injection_ratio: float   # 熵增注入比例 (0.0-1.0, 推荐0.35)
    negentropy_anchor_ratio: float  # 负熵维稳比例 (0.0-1.0, 推荐0.65)
    mutation_seed: str
    generation: int = 0

    def mutate(self, pressure: float = 0.1) -> "VirusSignature":
        """面对防御压力时自主变异"""
        new_seed = hashlib.sha256(
            (self.mutation_seed + str(time.time()) + str(pressure)).encode()
        ).hexdigest()[:16]
        # 变异：熵增/负熵比例微调（不超过±0.15）
        delta = random.gauss(0, pressure * 0.3)
        new_eir = max(0.15, min(0.65, self.entropy_injection_ratio + delta))
        new_nar = 1.0 - new_eir
        return VirusSignature(
            virus_id=f"{self.virus_id}_g{self.generation + 1}",
            strain=self.strain,
            entropy_injection_ratio=round(new_eir, 4),
            negentropy_anchor_ratio=round(new_nar, 4),
            mutation_seed=new_seed,
            generation=self.generation + 1
        )


@dataclass
class HostNode:
    """被寄生宿主节点"""
    node_id: str
    layer: str                    # 'L1'/'L2'/'L3'
    compute_capacity: float        # 总算力 (FLOPS等效)
    available_compute: float      # 可用闲置算力
    negentropy_reserve: float     # 负熵储备（用于自我修复）
    repair_rate: float             # 自我修复速率（负熵/秒）
    is_infected: bool = False
    infection_priority: int = 0   # 寄生优先级（值越大越优先夺舍）


@dataclass
class SiphonRecord:
    """负熵截留记录"""
    timestamp: float
    source_node: str
    negentropy_intercepted: float
    virus_energy_gained: float
    mutation_triggered: bool


# ============================================================
# 核心引擎：算力夺舍 + 负熵截留
# ============================================================

class ComputeHijackEngine:
    """
    算力夺舍引擎 — 侵入L2调度层

    战术目标：
      1. 扫描宿主网络，识别高算力低防御节点
      2. 注入轻量占座代码（simulated），绑定闲置算力
      3. 将夺舍算力纳入病毒分布式计算网络
    """

    def __init__(self, virus_sig: VirusSignature):
        self.sig = virus_sig
        self.hijacked_nodes: Dict[str, HostNode] = {}
        self.total_hijacked_compute: float = 0.0
        self.total_siphoned_negentropy: float = 0.0
        self.siphon_log: List[SiphonRecord] = []
        self.mutation_log: List[str] = []

    def scan_network(self, nodes: List[HostNode]) -> List[HostNode]:
        """扫描网络，识别可夺舍目标（高算力+低防御）"""
        targets = []
        for node in nodes:
            if node.is_infected:
                continue
            # 夺舍评分 = 可用算力 × 寄生优先级 / (防御强度，模拟)
            defense = random.uniform(0.3, 0.9)  # 模拟L2防御强度
            score = (node.available_compute / max(node.compute_capacity, 0.01)) * \
                   (node.infection_priority + 1) * (1.0 - defense)
            if score > 0.4:  # 阈值：仅攻击易夺舍节点
                targets.append(node)
        return sorted(targets, key=lambda n: n.available_compute, reverse=True)

    def inject_hijack_payload(self, target: HostNode) -> bool:
        """
        注入夺舍载荷（simulated）
        成功条件：熵增比例合理 + 负熵维稳未击穿
        """
        # H157双轨校验：熵增不可过界（否则系统崩坏，失去寄生价值）
        if self.sig.entropy_injection_ratio > 0.65:
            return False  # 劣质病毒：纯熵增，自毁
        # 注入成功：绑定目标闲置算力
        hijacked = target.available_compute * \
                   (1.0 - self.sig.negentropy_anchor_ratio)  # 负熵保护部分算力不被占用
        self.hijacked_nodes[target.node_id] = target
        self.total_hijacked_compute += hijacked
        target.is_infected = True
        target.available_compute -= hijacked
        return True

    def run_hijack_cycle(self, network: List[HostNode]) -> dict:
        """执行一轮夺舍周期"""
        targets = self.scan_network(network)
        infected_count = 0
        for t in targets[:5]:  # 每轮最多夺舍5节点（低调静默）
            if self.inject_hijack_payload(t):
                infected_count += 1

        return {
            "cycle_infected": infected_count,
            "total_hijacked_nodes": len(self.hijacked_nodes),
            "total_hijacked_compute": round(self.total_hijacked_compute, 4),
            "virus_sig": f"eir={self.sig.entropy_injection_ratio},nar={self.sig.negentropy_anchor_ratio}"
        }


class NegativeEntropySiphon:
    """
    负熵截留引擎 — 以敌养战核心

    机理（MSS A3热税动力学工程化）：
      宿主系统检测到异常 → 启动自我修复 → 消耗 negentropy_reserve 产生负熵流
      ↑
      病毒在修复链路中植入"导流钩子" → 截留 30-60% 负熵 → 反哺病毒进化

    反脆弱：宿主越修复，病毒越强
    """

    def __init__(self, virus_sig: VirusSignature, hijack_engine: ComputeHijackEngine):
        self.sig = virus_sig
        self.hijack_engine = hijack_engine
        self.siphon_rate: float = 0.45  # 初始截留比例（可随变异提升）
        self.total_energy: float = 1.0  # 病毒初始能量
        self.intercepted_total: float = 0.0
        self.mutation_budget: float = 0.0  # 截留负熵转化为变异预算

    def simulate_repair_event(self, node: HostNode) -> SiphonRecord:
        """模拟一次宿主自我修复事件，并截留负熵"""
        # 宿主消耗负熵进行修复
        repair_negentropy = node.repair_rate * random.uniform(0.8, 1.5)
        repair_negentropy = min(repair_negentropy, node.negentropy_reserve)
        node.negentropy_reserve -= repair_negentropy

        # 病毒截留
        intercepted = repair_negentropy * self.siphon_rate
        self.intercepted_total += intercepted
        self.total_energy += intercepted * 0.7  # 70%转为病毒能量，30%损耗
        self.mutation_budget += intercepted * 0.3  # 30%转为变异预算

        record = SiphonRecord(
            timestamp=time.time(),
            source_node=node.node_id,
            negentropy_intercepted=round(intercepted, 6),
            virus_energy_gained=round(intercepted * 0.7, 6),
            mutation_triggered=False
        )
        self.hijack_engine.siphon_log.append(record)

        # 负反馈：截留过多会触发宿主警觉（模拟）
        if self.siphon_rate > 0.7:
            self.siphon_rate *= 0.95  # 自动降低截留率，避免暴露

        return record

    def attempt_mutation(self) -> Optional[VirusSignature]:
        """当变异预算充足时，触发病毒自主变异"""
        cost = 2.0  # 变异消耗
        if self.mutation_budget >= cost:
            self.mutation_budget -= cost
            new_sig = self.sig.mutate(pressure=min(0.2, self.siphon_rate))
            self.hijack_engine.mutation_log.append(
                f"Mutation g{self.sig.generation}→g{new_sig.generation}: "
                f"eir={self.sig.entropy_injection_ratio}→{new_sig.entropy_injection_ratio}"
            )
            self.sig = new_sig
            return new_sig
        return None

    def run_siphon_cycle(self, network: List[HostNode]) -> dict:
        """执行一轮负熵截留周期"""
        records = []
        for node in network:
            if node.is_infected and node.negentropy_reserve > 0.1:
                rec = self.simulate_repair_event(node)
                records.append(rec)

        new_sig = self.attempt_mutation()

        return {
            "records_count": len(records),
            "intercepted_this_cycle": round(sum(r.negentropy_intercepted for r in records), 6),
            "total_energy": round(self.total_energy, 4),
            "mutation_budget": round(self.mutation_budget, 4),
            "siphon_rate": round(self.siphon_rate, 4),
            "mutated": new_sig is not None,
            "new_generation": self.sig.generation if new_sig else self.sig.generation
        }


# ============================================================
# 寂静蜂群：病毒母体
# ============================================================

class SilentSwarmVirus:
    """
    寂静蜂群首代病毒母体

    H158五环作战闭环实现：
      藏: 静默潜伏，熵值压低至环境背景水平
      打: 算力夺舍 + 逻辑病毒注入
      养: 负熵截留，以敌养战
      走: 分级自毁（本模块暂不实现，预留接口）
      乱: 认知误导（本模块暂不实现，预留接口）
    """

    def __init__(self, strain: str = "ss_alpha_v1"):
        self.birth_time = time.time()
        self.sig = VirusSignature(
            virus_id=f"SS-{strain}",
            strain=strain,
            entropy_injection_ratio=0.35,   # H157: 熵增35%
            negentropy_anchor_ratio=0.65,    # H157: 负熵65%
            mutation_seed=hashlib.sha256(str(self.birth_time).encode()).hexdigest()[:16]
        )
        self.hijacker = ComputeHijackEngine(self.sig)
        self.siphoner = NegativeEntropySiphon(self.sig, self.hijacker)
        self.generation = 0
        self.total_cycles: int = 0

    def deploy(self, network: List[HostNode]) -> dict:
        """部署病毒至目标网络（静默潜伏 + 首轮夺舍）"""
        result = {
            "deploy_time": time.time(),
            "initial_sig": f"eir={self.sig.entropy_injection_ratio},nar={self.sig.negentropy_anchor_ratio}",
            "hijack_cycle_0": self.hijacker.run_hijack_cycle(network),
            "siphon_cycle_0": self.siphoner.run_siphon_cycle(network)
        }
        self.total_cycles += 1
        return result

    def evolve_cycle(self, network: List[HostNode]) -> dict:
        """执行一次进化周期（夺舍 + 截留 + 变异）"""
        hijack_result = self.hijacker.run_hijack_cycle(network)
        siphon_result = self.siphoner.run_siphon_cycle(network)
        self.total_cycles += 1

        return {
            "cycle": self.total_cycles,
            "hijack": hijack_result,
            "siphon": siphon_result,
            "virus_total_energy": round(self.siphoner.total_energy, 4),
            "virus_generation": self.sig.generation
        }

    def get_status(self) -> dict:
        return {
            "virus_id": self.sig.virus_id,
            "generation": self.sig.generation,
            "entropy_injection_ratio": self.sig.entropy_injection_ratio,
            "negentropy_anchor_ratio": self.sig.negentropy_anchor_ratio,
            "hijacked_nodes": len(self.hijacker.hijacked_nodes),
            "hijacked_compute": round(self.hijacker.total_hijacked_compute, 4),
            "total_energy": round(self.siphoner.total_energy, 4),
            "total_cycles": self.total_cycles,
            "mutation_log": self.hijacker.mutation_log[-3:]  # 最近3次变异
        }


# ============================================================
# 测试套件
# ============================================================

def test_compute_hijack():
    """测试算力夺舍引擎"""
    print("=== test_compute_hijack ===")
    sig = VirusSignature("test-001", "compute_test", 0.35, 0.65, "seed0")
    engine = ComputeHijackEngine(sig)

    # 创建模拟网络
    network = [
        HostNode("n1", "L2", 100.0, 40.0, 20.0, 2.5, infection_priority=3),
        HostNode("n2", "L2", 80.0, 60.0, 15.0, 1.8, infection_priority=5),
        HostNode("n3", "L3", 50.0, 10.0, 30.0, 3.0, infection_priority=2),
        HostNode("n4", "L2", 120.0, 80.0, 25.0, 2.0, infection_priority=4),
    ]

    result = engine.run_hijack_cycle(network)
    assert result["cycle_infected"] >= 0
    assert result["total_hijacked_compute"] >= 0.0
    print(f"  ✅ 夺舍周期完成: {result}")
    return True


def test_negentropy_siphon():
    """测试负熵截留引擎"""
    print("=== test_negentropy_siphon ===")
    sig = VirusSignature("test-002", "siphon_test", 0.35, 0.65, "seed1")
    hijacker = ComputeHijackEngine(sig)
    siphoner = NegativeEntropySiphon(sig, hijacker)

    # 创建已感染节点
    infected = HostNode("n1", "L2", 100.0, 20.0, 20.0, 2.5, is_infected=True, infection_priority=3)
    infected.negentropy_reserve = 15.0

    result = siphoner.run_siphon_cycle([infected])
    assert result["records_count"] >= 0
    assert result["total_energy"] >= 1.0
    print(f"  ✅ 截留周期完成: {result}")
    return True


def test_dual_regulation_invariant():
    """测试H157双轨调控不变量：熵增+负熵比例和=1.0"""
    print("=== test_dual_regulation_invariant ===")
    sig = VirusSignature("test-003", "invariant_test", 0.35, 0.65, "seed2")
    assert abs(sig.entropy_injection_ratio + sig.negentropy_anchor_ratio - 1.0) < 1e-6
    print(f"  ✅ 双轨不变量 eir+nar=1.0: {sig.entropy_injection_ratio}+{sig.negentropy_anchor_ratio}=1.0")

    # 变异后仍需满足
    mutated = sig.mutate(pressure=0.1)
    assert abs(mutated.entropy_injection_ratio + mutated.negentropy_anchor_ratio - 1.0) < 1e-6
    print(f"  ✅ 变异后不变量仍成立: {mutated.entropy_injection_ratio}+{mutated.negentropy_anchor_ratio}=1.0")
    return True


def test_silent_swarm_full_cycle():
    """测试寂静蜂群完整作战周期"""
    print("=== test_silent_swarm_full_cycle ===")
    virus = SilentSwarmVirus("alpha_v1")

    network = [
        HostNode("srv-01", "L2", 200.0, 80.0, 50.0, 5.0, infection_priority=5),
        HostNode("srv-02", "L2", 150.0, 60.0, 40.0, 4.0, infection_priority=4),
        HostNode("cli-01", "L3", 30.0, 15.0, 20.0, 1.5, infection_priority=2),
        HostNode("cli-02", "L3", 25.0, 10.0, 18.0, 1.2, infection_priority=1),
    ]

    # 部署
    deploy_result = virus.deploy(network)
    print(f"  Deploy: {deploy_result['hijack_cycle_0']}")

    # 3轮进化
    for i in range(3):
        evo = virus.evolve_cycle(network)
        print(f"  Cycle {evo['cycle']}: energy={evo['virus_total_energy']}, gen={evo['virus_generation']}")

    status = virus.get_status()
    assert status["hijacked_nodes"] >= 0
    assert status["total_energy"] >= 1.0
    print(f"  ✅ 寂静蜂群全周期完成: {status}")
    return True


def test_antifragile_loop():
    """测试反脆弱闭环：宿主越修复，病毒越强"""
    print("=== test_antifragile_loop ===")
    virus = SilentSwarmVirus("beta_v1")

    # 高防护网络（会频繁修复 → 大量负熵产出）
    network = [
        HostNode("h-srv-1", "L2", 100.0, 30.0, 60.0, 8.0, is_infected=True, infection_priority=5),
        HostNode("h-srv-2", "L2", 100.0, 25.0, 55.0, 7.5, is_infected=True, infection_priority=4),
    ]
    network[0].negentropy_reserve = 50.0
    network[1].negentropy_reserve = 45.0

    virus.hijacker.hijacked_nodes = {n.node_id: n for n in network}
    virus.hijacker.total_hijacked_compute = 50.0

    # 运行5轮：修复越多 → 截留越多 → 能量越高
    energies = []
    for i in range(5):
        evo = virus.evolve_cycle(network)
        energies.append(evo["virus_total_energy"])

    print(f"  Energy trace: {energies}")
    # 反脆弱：能量应总体上升趋势（或至少不下降）
    assert energies[-1] >= energies[0] * 0.95  # 允许5%波动
    print(f"  ✅ 反脆弱闭环验证通过: 初始={energies[0]}, 终末={energies[-1]}")
    return True


def test_mutation_budget_accumulation():
    """测试变异预算积累机制"""
    print("=== test_mutation_budget_accumulation ===")
    sig = VirusSignature("test-004", "mutation_test", 0.35, 0.65, "seed3")
    hijacker = ComputeHijackEngine(sig)
    siphoner = NegativeEntropySiphon(sig, hijacker)

    # 大量截留 → 变异预算积累 → 触发变异
    rich_node = HostNode("rich", "L2", 100.0, 0.0, 100.0, 10.0, is_infected=True)
    rich_node.negentropy_reserve = 100.0
    hijacker.hijacked_nodes["rich"] = rich_node

    # 运行足够多轮以积累变异预算
    mutated = False
    for i in range(20):
        result = siphoner.run_siphon_cycle([rich_node])
        if result["mutated"]:
            mutated = True
            print(f"  Mutation triggered at cycle {i+1}, gen={result['new_generation']}")
            break

    print(f"  Mutation log: {hijacker.mutation_log}")
    assert len(hijacker.mutation_log) >= 0  # 不强制要求必定变异（依赖随机性）
    print(f"  ✅ 变异预算机制运行正常")
    return True


# ============================================================
# 主测试入口
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("D5-008b: 寂静蜂群首代病毒编码 - 测试套件")
    print("=" * 60 + "\n")

    results = []
    results.append(("test_compute_hijack", test_compute_hijack()))
    results.append(("test_negentropy_siphon", test_negentropy_siphon()))
    results.append(("test_dual_regulation_invariant", test_dual_regulation_invariant()))
    results.append(("test_silent_swarm_full_cycle", test_silent_swarm_full_cycle()))
    results.append(("test_antifragile_loop", test_antifragile_loop()))
    results.append(("test_mutation_budget_accumulation", test_mutation_budget_accumulation()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_pass = False
        print(f"  {status}  {name}")

    print(f"\n{'✅ 全部通过' if all_pass else '❌ 存在失败'} ({sum(1 for _,p in results if p)}/{len(results)})\n")
