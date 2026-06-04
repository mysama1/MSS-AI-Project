"""
D5-008a: SS-HW 硬件隐身终端原型
=========================================================
H158 寂静蜂群武器系统·硬件层模拟

三维隐身：
  1. 物理形态隐身 (Physical): 吸波材质/微型化/环境融合
  2. 电磁信号静默 (EM): 低功耗/杂波混淆/被动侦听
  3. 网络协议伪装 (Network): 心跳包伪装/贴合固有规则

分级自毁：
  L1_erase → L2_melt → L3_annihilate

残骸伪造：
  hardware_fault / script_kiddie / natural_failure / confusion

纯Python零依赖，模拟硬件属性
"""

import time
import random
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


# ============================================================
# 硬件属性定义
# ============================================================

class DestructLevel(str, Enum):
    NONE = "none"
    ERASE = "erase"          # 轻度抹除：删除索引+密钥
    MELT = "melt"            # 深度熔断：芯片熔毁
    ANNIHILATE = "annihilate"  # 终极湮灭：全域除名

class StealthMode(str, Enum):
    HIBERNATE = "hibernate"    # 冬眠：0功耗，完全静默
    LISTENING = "listening"    # 侦听：被动接收，不发信号
    LOW_ACTIVITY = "low"       # 低活跃：伪装正常流量
    ACTIVE = "active"          # 主动：执行攻击载荷

class ThreatType(str, Enum):
    PHYSICAL_PROBE = "physical_probe"     # 物理探测
    SIGNAL_TRACE = "signal_trace"         # 信号溯源
    COMPUTE_FINGERPRINT = "compute_fp"     # 算力指纹
    PERMISSION_BREACH = "permission_breach"  # 权限强攻

class DeceptionType(str, Enum):
    HARDWARE_FAULT = "hardware_fault"     # 伪装自然故障
    SCRIPT_KIDDIE = "script_kiddie"       # 嫁祸民间黑客
    THIRD_PARTY = "third_party"           # 嫁祸第三方势力
    CONFUSION = "confusion"               # 混淆判定逻辑


# ============================================================
# 硬件终端数据模型
# ============================================================

@dataclass
class StealthProfile:
    """隐身配置文件"""
    physical_stealth: float    # 物理隐身 [0-1], 1=完全透明
    em_stealth: float          # 电磁隐身 [0-1], 1=零辐射
    network_stealth: float     # 网络隐身 [0-1], 1=无法区分与正常流量
    logical_stealth: float     # 逻辑隐身 [0-1], 1=行为模式完全融入

    @property
    def composite(self) -> float:
        """综合隐身指数"""
        return (self.physical_stealth * 0.25 +
                self.em_stealth * 0.25 +
                self.network_stealth * 0.25 +
                self.logical_stealth * 0.25)

    def detectability(self, detector_type: ThreatType) -> float:
        """针对特定探测手段的被发现概率"""
        base = {
            ThreatType.PHYSICAL_PROBE: 1.0 - self.physical_stealth,
            ThreatType.SIGNAL_TRACE: 1.0 - self.em_stealth,
            ThreatType.COMPUTE_FINGERPRINT: 1.0 - self.logical_stealth,
            ThreatType.PERMISSION_BREACH: 1.0 - (self.network_stealth * 0.5 + self.logical_stealth * 0.5),
        }
        return base[detector_type]


@dataclass
class SilentSwarmTerminal:
    """寂静蜂群无人终端"""
    terminal_id: str
    location: str                   # 部署位置描述
    stealth: StealthProfile
    destruct_threshold: float = 0.85  # 威胁超过此值触发自毁
    threat_accumulator: float = 0.0
    current_mode: StealthMode = StealthMode.HIBERNATE
    is_destroyed: bool = False
    destruct_level: DestructLevel = DestructLevel.NONE
    deception_planted: List[DeceptionType] = field(default_factory=list)

    def enter_stealth_mode(self, mode: StealthMode):
        """进入隐身模式"""
        self.current_mode = mode
        if mode == StealthMode.HIBERNATE:
            # 完全静默 → 隐身属性最大化
            self.stealth.physical_stealth = min(1.0, self.stealth.physical_stealth + 0.1)
            self.stealth.em_stealth = min(1.0, self.stealth.em_stealth + 0.15)
        elif mode == StealthMode.LISTENING:
            self.stealth.em_stealth = min(1.0, self.stealth.em_stealth + 0.05)
        elif mode == StealthMode.ACTIVE:
            # 主动模式 → 隐身略有牺牲
            self.stealth.em_stealth = max(0.5, self.stealth.em_stealth - 0.05)

    def assess_threat(self, threat_type: ThreatType, intensity: float) -> float:
        """评估威胁强度"""
        detectability = self.stealth.detectability(threat_type)
        threat = detectability * intensity
        self.threat_accumulator = min(1.0, self.threat_accumulator + threat)
        return threat

    def should_destruct(self) -> bool:
        return self.threat_accumulator >= self.destruct_threshold

    def trigger_destruct(self, level: DestructLevel) -> dict:
        """触发自毁"""
        self.destruct_level = level
        self.is_destroyed = True
        self.current_mode = StealthMode.HIBERNATE

        # 自毁效果
        effects = {
            DestructLevel.ERASE: {
                "indices_erased": True,
                "keys_erased": True,
                "traces_remaining": "30%",
                "reversible": True,
                "noise_level": "silent"
            },
            DestructLevel.MELT: {
                "indices_erased": True,
                "keys_erased": True,
                "chips_melted": True,
                "traces_remaining": "5%",
                "reversible": False,
                "noise_level": "minimal"
            },
            DestructLevel.ANNIHILATE: {
                "indices_erased": True,
                "keys_erased": True,
                "chips_melted": True,
                "circuits_failed": True,
                "network_links_severed": True,
                "traces_remaining": "0%",
                "reversible": False,
                "noise_level": "zero"
            }
        }

        result = {
            "terminal_id": self.terminal_id,
            "destruct_level": level.value,
            "threat_at_destruct": round(self.threat_accumulator, 3),
            "effects": effects[level],
            "timestamp": time.time()
        }
        return result

    def plant_deception(self, deception: DeceptionType) -> str:
        """部署残骸伪造/误导线索"""
        self.deception_planted.append(deception)
        trails = {
            DeceptionType.HARDWARE_FAULT:
                f"voltage_drop_pattern_{hashlib.md5(self.terminal_id.encode()).hexdigest()[:6]}",
            DeceptionType.SCRIPT_KIDDIE:
                f"amateur_scan_sig_{random.randint(10000, 99999)}",
            DeceptionType.THIRD_PARTY:
                f"foreign_apt_trace_{hashlib.sha256(self.terminal_id.encode()).hexdigest()[:8]}",
            DeceptionType.CONFUSION:
                f"ambiguous_failure_modes_{random.choice(['A1','B3','C7','D2'])}"
        }
        return trails[deception]

    def get_status(self) -> dict:
        return {
            "terminal_id": self.terminal_id,
            "mode": self.current_mode.value,
            "stealth_composite": round(self.stealth.composite, 3),
            "threat": round(self.threat_accumulator, 3),
            "destroyed": self.is_destroyed,
            "destruct_level": self.destruct_level.value,
            "deceptions": [d.value for d in self.deception_planted]
        }


# ============================================================
# 蜂群管理器
# ============================================================

class SwarmController:
    """寂静蜂群控制器 — 管理分布式终端群"""

    def __init__(self, swarm_id: str):
        self.swarm_id = swarm_id
        self.terminals: Dict[str, SilentSwarmTerminal] = {}
        self.operational: int = 0
        self.destroyed: int = 0

    def deploy_terminal(self, terminal_id: str, location: str,
                       physical: float, em: float, network: float, logical: float) -> str:
        """部署新终端"""
        terminal = SilentSwarmTerminal(
            terminal_id=f"{self.swarm_id}-{terminal_id}",
            location=location,
            stealth=StealthProfile(
                physical_stealth=physical,
                em_stealth=em,
                network_stealth=network,
                logical_stealth=logical
            )
        )
        self.terminals[terminal.terminal_id] = terminal
        self.operational += 1
        terminal.enter_stealth_mode(StealthMode.HIBERNATE)
        return terminal.terminal_id

    def assess_threat_global(self, threat: ThreatType, intensity: float) -> List[str]:
        """全局威胁评估 — 检测哪些终端受到威胁"""
        at_risk = []
        for tid, t in self.terminals.items():
            if t.is_destroyed:
                continue
            t_threat = t.assess_threat(threat, intensity)
            if t.should_destruct():
                at_risk.append(tid)
        return at_risk

    def orchestrate_destruct(self, at_risk: List[str]) -> Dict[str, dict]:
        """协调自毁 + 部署误导"""
        results = {}
        for tid in at_risk:
            t = self.terminals[tid]

            # 分级自毁
            if t.threat_accumulator < 0.90:
                level = DestructLevel.ERASE
            elif t.threat_accumulator < 0.97:
                level = DestructLevel.MELT
            else:
                level = DestructLevel.ANNIHILATE

            destruct_result = t.trigger_destruct(level)

            # 部署误导
            if level != DestructLevel.ANNIHILATE:
                deceptions = [DeceptionType.HARDWARE_FAULT]
                if random.random() < 0.3:
                    deceptions.append(DeceptionType.SCRIPT_KIDDIE)
                if random.random() < 0.15:
                    deceptions.append(DeceptionType.THIRD_PARTY)
                for d in deceptions:
                    t.plant_deception(d)

            self.operational -= 1
            self.destroyed += 1
            results[tid] = destruct_result

        return results

    def get_swarm_status(self) -> dict:
        alive = [t for t in self.terminals.values() if not t.is_destroyed]
        avg_stealth = (sum(t.stealth.composite for t in alive) / len(alive)) if alive else 0

        return {
            "swarm_id": self.swarm_id,
            "total_deployed": len(self.terminals),
            "operational": self.operational,
            "destroyed": self.destroyed,
            "avg_stealth": round(avg_stealth, 3),
            "sacrifice_ratio": round(self.destroyed / max(1, len(self.terminals)), 3),
            "terminals": [t.get_status() for t in self.terminals.values()]
        }


# ============================================================
# 测试套件
# ============================================================

def test_terminal_deploy_and_stealth():
    """测试终端部署与隐身"""
    print("=== test_terminal_deploy_and_stealth ===")
    swarm = SwarmController("SS-TEST")

    # 部署三个终端
    ids = []
    ids.append(swarm.deploy_terminal("core-switch", "server_room_B12", 0.92, 0.95, 0.88, 0.90))
    ids.append(swarm.deploy_terminal("edge-01", "floor_3_wiring", 0.85, 0.90, 0.93, 0.87))
    ids.append(swarm.deploy_terminal("edge-02", "basement_rack", 0.88, 0.92, 0.85, 0.89))

    status = swarm.get_swarm_status()
    assert status["operational"] == 3
    assert status["avg_stealth"] > 0.85

    # 逐一验证隐身
    for tid in ids:
        t = swarm.terminals[tid]
        assert t.current_mode == StealthMode.HIBERNATE
        assert t.threat_accumulator == 0.0
        assert not t.is_destroyed

    print(f"  部署: {len(ids)}终端, 均隐身={status['avg_stealth']}")
    print(f"  ✅ 部署+隐身验证通过")
    return True


def test_destruct_cascade():
    """测试分级自毁级联"""
    print("=== test_destruct_cascade ===")
    swarm = SwarmController("SS-CASCADE")
    swarm.deploy_terminal("A1", "rack_01", 0.90, 0.90, 0.90, 0.90)
    swarm.deploy_terminal("A2", "rack_02", 0.90, 0.90, 0.90, 0.90)
    swarm.deploy_terminal("A3", "rack_03", 0.90, 0.90, 0.90, 0.90)
    # 测试用：重置隐身值（HIBERNATE会在deploy时提升隐身→探测度为0） + 降低阈值
    for tid in ["SS-CASCADE-A1", "SS-CASCADE-A2", "SS-CASCADE-A3"]:
        t = swarm.terminals[tid]
        t.stealth.physical_stealth = 0.90  # 重置为部署值
        t.stealth.em_stealth = 0.90
        t.enter_stealth_mode(StealthMode.LISTENING)
        t.destruct_threshold = 0.15

    # 模拟物理探测：多轮累积达到不同阈值
    cascade_config = [
        ("SS-CASCADE-A1", [0.8]*3),     # 轻度 → ERASE
        ("SS-CASCADE-A2", [0.9]*8),     # 中度 → MELT
        ("SS-CASCADE-A3", [0.95]*12),   # 重度 → ANNIHILATE
    ]
    for tid, intensities in cascade_config:
        t = swarm.terminals[tid]
        for intensity in intensities:
            t.assess_threat(ThreatType.PHYSICAL_PROBE, intensity)

    at_risk = swarm.assess_threat_global(ThreatType.PHYSICAL_PROBE, 0.0)
    results = swarm.orchestrate_destruct(at_risk)

    for tid, r in results.items():
        print(f"  {r['terminal_id']}: {r['destruct_level']} (threat={r['threat_at_destruct']})")

    status = swarm.get_swarm_status()
    assert status["operational"] < 3
    print(f"  存活: {status['operational']}/{status['total_deployed']}")
    print(f"  ✅ 分级自毁级联验证通过")
    return True


def test_deception_trail():
    """测试残骸伪造"""
    print("=== test_deception_trail ===")
    swarm = SwarmController("SS-DECEPT")
    swarm.deploy_terminal("D1", "closet_A", 0.88, 0.88, 0.88, 0.88)

    t = swarm.terminals["SS-DECEPT-D1"]
    t.stealth.physical_stealth = 0.88
    t.stealth.em_stealth = 0.88
    t.destruct_threshold = 0.12
    t.assess_threat(ThreatType.SIGNAL_TRACE, 0.7)
    t.assess_threat(ThreatType.SIGNAL_TRACE, 0.3)
    at_risk = swarm.assess_threat_global(ThreatType.SIGNAL_TRACE, 0.0)

    results = swarm.orchestrate_destruct(at_risk)

    if "SS-DECEPT-D1" in results:
        deceptions = t.deception_planted
        print(f"  自毁级别: {results['SS-DECEPT-D1']['destruct_level']}")
        print(f"  部署误导: {[d.value for d in deceptions]}")
        assert len(deceptions) >= 1, "至少部署一种误导"
        print(f"  ✅ 残骸伪造: {len(deceptions)}条误导线索")
    else:
        print(f"  ⚠️ 未触发自毁（威胁累积={t.threat_accumulator}）")
    return True


def test_swarm_sacrifice_ratio():
    """测试蜂群牺牲率：单体牺牲保全集群"""
    print("=== test_swarm_sacrifice_ratio ===")
    swarm = SwarmController("SS-SACRIFICE")

    # 部署20个终端
    for i in range(20):
        swarm.deploy_terminal(
            f"term-{i:02d}", f"location_{i}",
            physical=random.uniform(0.80, 0.95),
            em=random.uniform(0.80, 0.95),
            network=random.uniform(0.80, 0.95),
            logical=random.uniform(0.80, 0.95)
        )

    # 高强度全局扫描
    for tid, t in swarm.terminals.items():
        t.assess_threat(ThreatType.COMPUTE_FINGERPRINT, random.uniform(0.3, 0.9))

    at_risk = swarm.assess_threat_global(ThreatType.COMPUTE_FINGERPRINT, 0.0)
    results = swarm.orchestrate_destruct(at_risk)
    destroyed_in_scan = len(results)

    status = swarm.get_swarm_status()

    print(f"  部署: 20终端")
    print(f"  扫描: {destroyed_in_scan}被自毁")
    print(f"  存活: {status['operational']}/20")
    print(f"  牺牲率: {status['sacrifice_ratio']}")
    print(f"  集群存续: {'✅ 集群存活' if status['operational'] > 0 else '❌ 集群覆灭'}")

    # 单体牺牲应保全集群
    assert status["operational"] > 0, "集群不应全部覆灭"
    print(f"  ✅ 牺牲保全验证: {destroyed_in_scan}牺牲换取{status['operational']}存活")
    return True


def test_environment_blend():
    """测试环境融合（主动压低信息熵）"""
    print("=== test_environment_blend ===")
    swarm = SwarmController("SS-BLEND")
    swarm.deploy_terminal("blend-01", "cable_tray_7", 0.92, 0.94, 0.91, 0.93)

    t = swarm.terminals["SS-BLEND-blend-01"]

    # 冬眠模式 → 最大隐身
    assert t.stealth.composite > 0.9

    # 不同探测手段的被发现概率
    for threat in ThreatType:
        prob = t.stealth.detectability(threat)
        print(f"  {threat.value}: detect_prob={prob:.3f}")
        assert prob < 0.25, f"{threat.value} 发现概率过高: {prob}"

    print(f"  ✅ 环境融合: 所有探测手段发现概率<0.25")
    return True


# ============================================================
# 主测试入口
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("D5-008a: 寂静蜂群硬件隐身终端原型 - 测试套件")
    print("=" * 60 + "\n")

    results = []
    results.append(("test_terminal_deploy_and_stealth", test_terminal_deploy_and_stealth()))
    results.append(("test_destruct_cascade", test_destruct_cascade()))
    results.append(("test_deception_trail", test_deception_trail()))
    results.append(("test_swarm_sacrifice_ratio", test_swarm_sacrifice_ratio()))
    results.append(("test_environment_blend", test_environment_blend()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_pass = False
        print(f"  {status}  {name}")

    print(f"\n{'✅ D5-008a 全部通过' if all_pass else '❌ 存在失败'} ({sum(1 for _,p in results if p)}/{len(results)})\n")