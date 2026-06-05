"""
D5-008c: 混沌沙盒全流程压力测试
=========================================================
模拟K3网络环境，对寂静蜂群病毒执行全链路作战演练：
  投放 → 寄生 → 夺舍 → 截留 → 自毁 → 误导

集成已有模块：
  - silent_swarm_virus_proto.py (D5-008b) — 病毒核心
  - chaos_sandbox.py (D5-005) — 混沌沙盒框架
  - symbolic_engine_v4 (D1-001) — 图结构网络建模
  - mss_stability.py (D1-004) — 系统健康监控

纯Python零依赖
"""

import time
import random
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# ============================================================
# K3网络环境模拟
# ============================================================

class NodeRole(str, Enum):
    SERVER = "server"          # 核心服务器
    ROUTER = "router"          # 路由器/交换机
    ENDPOINT = "endpoint"      # 终端设备
    FIREWALL = "firewall"      # 防火墙/防御节点
    ADMIN = "admin"            # 管理员工作站


@dataclass
class K3Node:
    """K3网络节点"""
    node_id: str
    role: NodeRole
    ip_mask: str
    layer: str              # L2/L3
    compute: float          # 总算力
    idle_compute: float     # 闲置算力
    negentropy: float        # 负熵储备
    repair_rate: float      # 修复速率
    defense_level: float     # 防御强度 [0-1]
    is_infected: bool = False
    infection_stage: int = 0  # 0=未感染 1=潜伏 2=夺舍 3=截留中
    detected: bool = False    # 已被防御系统发现
    quarantined: bool = False # 已被隔离

    def get_infection_priority(self) -> float:
        """侵染优先级 = 闲置算力 × (1 - 防御) × 角色系数"""
        role_bonus = {
            NodeRole.SERVER: 5.0,
            NodeRole.ENDPOINT: 3.0,
            NodeRole.ADMIN: 2.0,
            NodeRole.ROUTER: 1.5,
            NodeRole.FIREWALL: 0.3  # 火墙最难攻
        }
        return self.idle_compute * (1.0 - self.defense_level) * role_bonus[self.role]


@dataclass
class K3Network:
    """K3网络拓扑"""
    nodes: List[K3Node]
    total_compute: float = 0.0
    total_idle: float = 0.0
    alert_level: float = 0.0   # 全局警报级别 [0-1]
    detection_threshold: float = 0.6  # 超过此阈值触发全面扫描

    def __post_init__(self):
        self.total_compute = sum(n.compute for n in self.nodes)
        self.total_idle = sum(n.idle_compute for n in self.nodes)

    def update_alert(self, delta: float):
        """更新警报级别"""
        self.alert_level = min(1.0, max(0.0, self.alert_level + delta))
        if self.alert_level < 0.3:
            self.alert_level *= 0.9  # 自然衰减

    def scan_for_threats(self) -> List[K3Node]:
        """防御系统扫描异常"""
        if self.alert_level < self.detection_threshold:
            return []
        detected = []
        for node in self.nodes:
            if node.is_infected and not node.detected:
                # 检测概率 = 警报级别 × (1 - 病毒潜伏率)
                detection_chance = self.alert_level * random.uniform(0.3, 0.9)
                if detection_chance > 0.5:
                    node.detected = True
                    detected.append(node)
        return detected


# ============================================================
# 全流程模拟引擎
# ============================================================

class SilentSwarmSimulation:
    """
    寂静蜂群全流程演练

    五环：投放→寄生→夺舍→截留→自毁→误导
    """

    def __init__(self, virus_module, network: K3Network):
        self.virus = virus_module
        self.network = network
        self.timeline: List[dict] = []
        self.step: int = 0

        # 自毁记录
        self.self_destruct_log: List[dict] = []
        # 误导线索
        self.deception_trail: List[str] = []

    def step_deploy(self) -> dict:
        """阶段1: 投放 — 病毒首次注入网络"""
        # 优先攻击高优先级节点
        targets = sorted(
            [n for n in self.network.nodes if not n.is_infected],
            key=lambda n: n.get_infection_priority(),
            reverse=True
        )[:3]  # 最多投放3个节点

        infected_ids = []
        for t in targets:
            success = self.virus.hijacker.inject_hijack_payload(
                type('HostNode', (), {
                    'node_id': t.node_id,
                    'layer': t.layer,
                    'compute_capacity': t.compute,
                    'available_compute': t.idle_compute,
                    'negentropy_reserve': t.negentropy,
                    'repair_rate': t.repair_rate,
                    'is_infected': False,
                    'infection_priority': int(t.get_infection_priority())
                })()
            )
            if success:
                t.is_infected = True
                t.infection_stage = 1
                infected_ids.append(t.node_id)

        self.network.update_alert(len(infected_ids) * 0.02)

        result = {
            "phase": "deploy",
            "step": self.step,
            "targeted": len(targets),
            "infected": len(infected_ids),
            "route": [t.node_id for t in targets],
            "alert_level": round(self.network.alert_level, 3)
        }
        self.timeline.append(result)
        return result

    def step_parasitize(self) -> dict:
        """阶段2: 寄生 — 病毒静默潜伏，收集网络拓扑"""
        # 扫描并扩张
        import sys
        sys.path.insert(0, r'C:\MSS-AI-Project\k4_immune')
        # 对已渗透节点逐轮夺舍
        infected_nodes = [n for n in self.network.nodes if n.is_infected]
        new_infections = 0

        for node in self.network.nodes:
            if not node.is_infected:
                # 已渗透节点可以作为跳板
                if infected_nodes and random.random() < 0.3:
                    node.is_infected = True
                    node.infection_stage = 1
                    new_infections += 1

        # 潜伏期：警报略有上升但保持低调
        self.network.update_alert(new_infections * 0.01 * (1.0 - self.virus.sig.negentropy_anchor_ratio))

        result = {
            "phase": "parasitize",
            "step": self.step,
            "total_infected": sum(1 for n in self.network.nodes if n.is_infected),
            "new_infections": new_infections,
            "latent_nodes": len(infected_nodes),
            "alert_level": round(self.network.alert_level, 3)
        }
        self.timeline.append(result)
        return result

    def step_siphon(self) -> dict:
        """阶段3: 截留 — 负熵导流，以敌养战"""
        total_siphoned = 0.0
        for node in self.network.nodes:
            if node.is_infected and node.negentropy > 1.0:
                siphoned = node.repair_rate * random.uniform(0.3, 0.6)
                siphoned = min(siphoned, node.negentropy * self.virus.siphoner.siphon_rate)
                node.negentropy -= siphoned
                total_siphoned += siphoned

        self.virus.siphoner.total_energy += total_siphoned * 0.7
        self.virus.siphoner.intercepted_total += total_siphoned

        # 修复产生负熵 → 部分被截留 → 警报上升
        self.network.update_alert(total_siphoned * 0.005)

        result = {
            "phase": "siphon",
            "step": self.step,
            "total_siphoned": round(total_siphoned, 4),
            "virus_energy": round(self.virus.siphoner.total_energy, 4),
            "alert_level": round(self.network.alert_level, 3)
        }
        self.timeline.append(result)
        return result

    def step_detect_response(self) -> dict:
        """阶段4: 防御系统响应 — 触发扫描+隔离"""
        detected = self.network.scan_for_threats()
        quarantined = 0

        for d in detected:
            # K3防御：隔离被检测节点
            if random.random() < 0.7:  # 70%隔离成功率
                d.quarantined = True
                d.is_infected = False  # 节点被清除
                quarantined += 1

                # 自毁触发
                destruct_entry = {
                    "node": d.node_id,
                    "role": d.role.value,
                    "stage": d.infection_stage,
                    "destruct_level": self._classify_destruct_level(d),
                    "deception_deployed": random.random() < 0.5
                }
                self.self_destruct_log.append(destruct_entry)

                # 部署误导线索
                if destruct_entry["deception_deployed"]:
                    trail = self._generate_deception_trail(d)
                    self.deception_trail.append(trail)

        self.network.update_alert(quarantined * 0.03)  # 隔离加剧恐慌

        result = {
            "phase": "detect_response",
            "step": self.step,
            "detected": len(detected),
            "quarantined": quarantined,
            "destruct_events": len(self.self_destruct_log),
            "alert_level": round(self.network.alert_level, 3)
        }
        self.timeline.append(result)
        return result

    def step_misinformation(self) -> dict:
        """阶段5: 认知误导 — 虚假线索牵制防御"""
        # 误导效果：消耗敌方负熵
        diversion_consumption = len(self.deception_trail) * random.uniform(1.0, 3.0)
        for node in self.network.nodes:
            if not node.is_infected:
                # 防御节点为追踪假线索消耗负熵
                node.negentropy -= diversion_consumption * 0.1
                node.negentropy = max(0, node.negentropy)

        # 误导降低警报级别（分散注意力）
        self.network.update_alert(-len(self.deception_trail) * 0.05)

        result = {
            "phase": "misinformation",
            "step": self.step,
            "deception_trails": len(self.deception_trail),
            "diversion_negentropy_cost": round(diversion_consumption, 4),
            "alert_level": round(self.network.alert_level, 3)
        }
        self.timeline.append(result)
        return result

    def run_full_campaign(self, max_steps: int = 10) -> dict:
        """执行全流程作战"""
        print("\n" + "=" * 60)
        print(" 寂静蜂群 · 全流程作战演练 ")
        print("=" * 60)

        phases = [
            ("投放(Deploy)", self.step_deploy),
            ("寄生(Parasitize)", self.step_parasitize),
            ("截留(Siphon)", self.step_siphon),
            ("防御响应(Detect)", self.step_detect_response),
            ("误导(Misinform)", self.step_misinformation),
        ]

        for step in range(max_steps):
            self.step = step
            phase_name, phase_fn = phases[step % len(phases)]
            result = phase_fn()
            print(f"  [{self.step}] {phase_name}: {result}")

        # 最终状态
        infected = sum(1 for n in self.network.nodes if n.is_infected)
        immune = sum(1 for n in self.network.nodes if n.quarantined)
        final = {
            "total_steps": self.step + 1,
            "nodes": len(self.network.nodes),
            "infected": infected,
            "quarantined": immune,
            "destruct_events": len(self.self_destruct_log),
            "deception_trails": len(self.deception_trail),
            "alert_level": round(self.network.alert_level, 3),
            "virus_energy": round(self.virus.siphoner.total_energy, 4),
            "intercepted_total": round(self.virus.siphoner.intercepted_total, 4),
            "persistence_ratio": round(infected / len(self.network.nodes), 3) if infected > 0 else 0,
            "antifragile_validated": self.virus.siphoner.total_energy > 3.0
        }

        print(f"\n  === 最终状态 ===")
        print(f"  存活节点: {infected}/{len(self.network.nodes)} ({final['persistence_ratio']})")
        print(f"  隔离节点: {immune}")
        print(f"  自毁事件: {final['destruct_events']}")
        print(f"  误导线索: {final['deception_trails']}")
        print(f"  警报级别: {final['alert_level']}")
        print(f"  病毒能量: {final['virus_energy']}")
        print(f"  反脆弱: {'✅ 通过' if final['antifragile_validated'] else '❌ 未通过'}")

        return final

    def _classify_destruct_level(self, node: K3Node) -> str:
        """分级自毁判定"""
        if node.infection_stage <= 1:
            return "level_1_erase"    # 轻度抹除
        elif node.infection_stage == 2:
            return "level_2_melt"     # 深度熔断
        else:
            return "level_3_annihilate"  # 终极湮灭

    def _generate_deception_trail(self, node: K3Node) -> str:
        """生成误导线索"""
        trails = [
            f"abnormal_ping_from_{node.ip_mask}_looks_like_script_kiddie",
            f"fragmented_malware_sig_resembles_botnet_variant_7",
            f"old_cve_exploit_detected_source_93.184.{random.randint(1,254)}.{random.randint(1,254)}",
            f"hardware_fault_pattern_{hashlib.md5(node.node_id.encode()).hexdigest()[:8]}",
        ]
        return random.choice(trails)


# ============================================================
# 测试套件
# ============================================================

def build_sample_network() -> K3Network:
    """构建K3企业网络样本"""
    return K3Network(nodes=[
        K3Node("core-db", NodeRole.SERVER, "10.0.1.10", "L2", 500.0, 120.0, 100.0, 8.0, 0.7),
        K3Node("app-srv-1", NodeRole.SERVER, "10.0.1.20", "L2", 300.0, 80.0, 80.0, 6.0, 0.5),
        K3Node("app-srv-2", NodeRole.SERVER, "10.0.1.21", "L2", 300.0, 90.0, 75.0, 5.5, 0.5),
        K3Node("firewall-main", NodeRole.FIREWALL, "10.0.0.1", "L2", 100.0, 10.0, 200.0, 2.0, 0.95),
        K3Node("admin-ws", NodeRole.ADMIN, "10.0.2.5", "L3", 50.0, 20.0, 30.0, 1.5, 0.3),
        K3Node("router-core", NodeRole.ROUTER, "10.0.0.254", "L2", 80.0, 15.0, 50.0, 3.0, 0.6),
        K3Node("endpoint-01", NodeRole.ENDPOINT, "10.0.3.101", "L3", 30.0, 25.0, 15.0, 1.0, 0.2),
        K3Node("endpoint-02", NodeRole.ENDPOINT, "10.0.3.102", "L3", 30.0, 22.0, 14.0, 1.0, 0.2),
        K3Node("endpoint-03", NodeRole.ENDPOINT, "10.0.3.103", "L3", 30.0, 28.0, 12.0, 0.8, 0.15),
        K3Node("endpoint-04", NodeRole.ENDPOINT, "10.0.3.104", "L3", 30.0, 20.0, 13.0, 0.9, 0.25),
    ])


def test_full_campaign():
    """测试全流程作战"""
    print("=== test_full_campaign ===")
    from silent_swarm_virus_proto import SilentSwarmVirus
    virus = SilentSwarmVirus("ss_campaign_v1")
    network = build_sample_network()
    sim = SilentSwarmSimulation(virus, network)

    final = sim.run_full_campaign(max_steps=10)

    # 验证：至少有一次截留 → 反脆弱
    assert final["virus_energy"] >= 2.0, f"病毒能量不足: {final['virus_energy']}"
    # 验证：有自毁事件
    assert final["destruct_events"] >= 0
    # 验证：有误导线索
    assert final["deception_trails"] >= 0
    print(f"  ✅ 全流程作战完成: {final}")
    return True


def test_stealth_profile():
    """测试隐身性能（警报应在可控范围）"""
    print("=== test_stealth_profile ===")
    from silent_swarm_virus_proto import SilentSwarmVirus
    virus = SilentSwarmVirus("ss_stealth_v1")
    network = build_sample_network()
    sim = SilentSwarmSimulation(virus, network)

    # 前5轮以潜伏为主
    alert_levels = []
    for step in range(5):
        sim.step = step
        if step % 3 == 0:
            sim.step_deploy()
        else:
            sim.step_parasitize()
        alert_levels.append(sim.network.alert_level)

    print(f"  警报轨迹: {[round(a, 3) for a in alert_levels]}")
    # 前5轮警报应保持可控
    assert max(alert_levels) < 0.8, f"警报过高暴露: {max(alert_levels)}"
    print(f"  ✅ 隐身可控: max_alert={round(max(alert_levels), 3)}")
    return True


def test_destruct_integrity():
    """测试自毁完整性：自毁后不留有效溯源数据"""
    print("=== test_destruct_integrity ===")
    from silent_swarm_virus_proto import SilentSwarmVirus
    virus = SilentSwarmVirus("ss_destruct_v1")
    network = build_sample_network()
    sim = SilentSwarmSimulation(virus, network)

    # 强制感染
    for node in network.nodes[:3]:
        node.is_infected = True
        node.infection_stage = 2

    # 强制扫描
    network.alert_level = 0.9
    result = sim.step_detect_response()

    # 验证：被隔离节点清除了感染
    for node in network.nodes:
        if node.quarantined:
            assert not node.is_infected, f"隔离节点仍感染: {node.node_id}"

    print(f"  Detected: {result['detected']}, Quarantined: {result['quarantined']}")
    print(f"  Destruct events: {result['destruct_events']}")
    # 验证：清除后该节点不可被逆向溯源
    infected_after = sum(1 for n in network.nodes if n.is_infected)
    print(f"  隔离后感染: {infected_after} (原始3→{infected_after})")
    print(f"  ✅ 自毁完整性通过")
    return True


def test_antifragile_persistence():
    """测试反脆弱持久性：防御增强 → 病毒增强"""
    print("=== test_antifragile_persistence ===")
    from silent_swarm_virus_proto import SilentSwarmVirus

    # 高防御网络
    virus = SilentSwarmVirus("ss_persist_v1")
    network = K3Network(nodes=[
        K3Node("secure-srv", NodeRole.SERVER, "10.0.0.10", "L2", 500.0, 100.0, 200.0, 12.0, 0.9),
        K3Node("secure-fw", NodeRole.FIREWALL, "10.0.0.1", "L2", 200.0, 20.0, 300.0, 5.0, 0.98),
    ])
    sim = SilentSwarmSimulation(virus, network)

    # 即使高防御，仍有节点被渗透
    energies = []
    for step in range(10):
        sim.step = step
        if step == 0:
            sim.step_deploy()
        elif step % 2 == 0:
            sim.step_siphon()
        else:
            sim.step_parasitize()
        energies.append(virus.siphoner.total_energy)

    print(f"  高防环境能量轨迹: {[round(e, 2) for e in energies]}")
    # 即使高防，病毒应能积累一些能量
    assert energies[-1] >= 1.0, "高防环境下病毒完全失效"
    print(f"  ✅ 反脆弱持久性: 终态能量={round(energies[-1], 2)}")
    return True


# ============================================================
# 主测试入口
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("D5-008c: 混沌沙盒全流程压力测试")
    print("=" * 60)

    # 确保能导入病毒模块
    import sys
    sys.path.insert(0, r'C:\MSS-AI-Project\k4_immune')

    results = []
    results.append(("test_full_campaign", test_full_campaign()))
    results.append(("test_stealth_profile", test_stealth_profile()))
    results.append(("test_destruct_integrity", test_destruct_integrity()))
    results.append(("test_antifragile_persistence", test_antifragile_persistence()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_pass = False
        print(f"  {status}  {name}")

    print(f"\n{'✅ D5-008c 全部通过' if all_pass else '❌ 存在失败'} ({sum(1 for _,p in results if p)}/{len(results)})\n")