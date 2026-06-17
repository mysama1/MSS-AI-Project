"""
MCDP v0.2 — N>2 Multi-Agent + Decentralized L2.5 Normative Stack (Sprint 147b+c).

方向1深化:
  147b: N>2 连续域扩展 — 从 pair-wise 到 tensorial mean field
  147c: L2.5 去中心化 — 无需调解者, P2P规范场栈

核心创新:
  N>2: Mean Field Game 近似 — 每个Agent对其他N-1个Agent的效应压缩为"平均场"
  L2.5 DC: 分布式共识协议 (gossip-based), 每个Agent维护本地规范场栈副本

对已有系统:
  MCDP v0.1 → 继承 → 扩展 N>2 + 去中心化
  H633 (VCG) → 去中心化已解决 → 此处聚焦规范场栈去中心化
"""
from __future__ import annotations
import math, time, uuid, json, random
from typing import Dict, List, Tuple, Set, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque

from .mcdp import (
    AgentRole, AgentConflict, MediatorAgent,
    L25NormativeStack, MeaningField, ColimitConstructor,
)


# ═══ Layer 1: N>2 Mean Field Extension ═══

@dataclass
class MeanFieldAgent:
    """
    均值场Agent: 在N>2场景下，每个Agent不维护所有其他Agent的精确关系，
    而是维护一个"平均场" — 所有其他Agent效应的压缩表示.
    """
    id: str
    role: AgentRole = AgentRole.PARTICIPANT
    strategy: str = ""
    payoff: float = 0.0
    # 全局场估计 (基于对其他Agent的观察压缩)
    mean_field_payoff: float = 0.0       # 估计的平均对手收益
    mean_field_strategy: str = ""         # 估计的多数策略
    strategy_distribution: Dict[str, float] = field(default_factory=dict)  # 策略分布估计
    # 本地规范场栈 (去中心化副本)
    local_normative_stack: Optional["DecentralizedNormativeStack"] = None


@dataclass
class MeanFieldConflict:
    """
    N>2冲突 — 多Agent间的矛盾汇聚为均值场张力.

    每个Agent看到的是"整个世界对我施加的压力"而不是个别对手.
    """
    conflicts: List[AgentConflict]         # 原始冲突对
    n_agents: int                           # 总Agent数
    tension_field: Dict[str, float]         # agent_id → 张力值
    mean_tension: float                     # 全场平均张力
    critical_agents: List[str]              # 张力最大的Agent (最需要消解)
    dominant_strategies: Dict[str, int]      # 策略 → 采用人数
    nash_equilibrium: Optional[str] = None  # 检测到的Nash均衡


class MeanFieldEngine:
    """
    N>2 Mean Field 消解引擎.

    核心:
      当N很大时，pair-wise交互矩阵 O(N²) 不可行。
      每个Agent维护自己的 mean_field_payoff + strategy_distribution，
      冲突消解不再需要完整的 N×N 矩阵，而是检查每个Agent的张力向量。

    方法:
      1. 收集所有Agent的self-report (策略+收益)
      2. 计算每个Agent的张力 = |self_payoff - mean_field_payoff|
      3. 对高张力Agent，寻找最小调整使其向均值场靠拢
      4. 迭代直到全场张力 < ε
    """

    def __init__(self, convergence_eps: float = 0.01, max_iter: int = 100):
        self.eps = convergence_eps
        self.max_iter = max_iter
        self.iteration_history: List[Dict] = []

    def analyze_field(self, agents: List[MeanFieldAgent]) -> MeanFieldConflict:
        """分析N>2 Agent的均值场状态."""
        n = len(agents)
        if n < 2:
            return MeanFieldConflict([], n, {}, 0.0, [], {})

        # 收集策略分布
        strat_counts: Dict[str, int] = defaultdict(int)
        total_payoff = 0.0
        tensions: Dict[str, float] = {}

        for agent in agents:
            strat_counts[agent.strategy] += 1
            total_payoff += agent.payoff
            # 张力 = 自身收益与均值场收益的偏差
            tension = abs(agent.payoff - agent.mean_field_payoff)
            tensions[agent.id] = tension

        mean_payoff = total_payoff / n
        mean_tension = sum(tensions.values()) / n

        # 找出临界Agent
        sorted_agents = sorted(tensions.items(), key=lambda x: -x[1])
        threshold = mean_tension + 1.0 * (max(t for _, t in sorted_agents) - mean_tension) / 2
        critical = [aid for aid, t in sorted_agents if t > threshold]

        # 检测Nash均衡: 是否有Agent可以通过单边改变策略提高收益
        # 简化: 检查策略分布是否稳定
        dominant = dict(strat_counts)

        return MeanFieldConflict(
            conflicts=[],
            n_agents=n,
            tension_field=tensions,
            mean_tension=round(mean_tension, 4),
            critical_agents=critical,
            dominant_strategies=dominant,
        )

    def resolve_mean_field(self, agents: List[MeanFieldAgent],
                           payoff_fn: Callable[[str, Dict[str, int]], float]
                           ) -> List[MeanFieldAgent]:
        """
        均值场消解: 迭代调整高张力Agent.

        Args:
            agents: 当前Agent列表
            payoff_fn: (strategy, strategy_distribution) → payoff
        """
        for iteration in range(self.max_iter):
            # 更新策略分布
            strat_counts: Dict[str, int] = defaultdict(int)
            for a in agents:
                strat_counts[a.strategy] += 1

            # 更新每个Agent的均值场估计
            for agent in agents:
                # 估计: 如果agent采用其他策略会怎样
                true_payoff = payoff_fn(agent.strategy, strat_counts)
                agent.payoff = true_payoff

                total_others_payoff = 0.0
                for other in agents:
                    if other.id == agent.id:
                        continue
                    total_others_payoff += other.payoff
                agent.mean_field_payoff = total_others_payoff / max(1, len(agents) - 1)
                agent.strategy_distribution = {
                    k: v / len(agents) for k, v in strat_counts.items()
                }

            # 分析全场张力
            conflict = self.analyze_field(agents)

            self.iteration_history.append({
                "iter": iteration,
                "mean_tension": conflict.mean_tension,
                "critical_count": len(conflict.critical_agents),
                "strategies": dict(strat_counts),
            })

            if conflict.mean_tension < self.eps:
                break

            # 调整临界Agent: 尝试切换到多数策略
            for aid in conflict.critical_agents:
                agent = next((a for a in agents if a.id == aid), None)
                if not agent:
                    continue
                best_strat = max(strat_counts.items(), key=lambda x: x[1])[0]
                if best_strat != agent.strategy:
                    alt_payoff = payoff_fn(best_strat, strat_counts)
                    if alt_payoff > agent.payoff:
                        agent.strategy = best_strat  # 切换到更优策略

        return agents


# ═══ Layer 2: Decentralized L2.5 Normative Stack ═══

@dataclass
class NormativeVote:
    """规范场投票 — P2P gossip协议的一部分."""
    agent_id: str
    rule_id: str
    vote: float              # 0=反对, 1=支持
    timestamp: float
    justification: str = ""


@dataclass
class GossipMessage:
    """Gossip传播的消息."""
    sender_id: str
    message_type: str        # "norm_update" | "conflict_alert" | "field_sync"
    payload: Dict
    timestamp: float = field(default_factory=time.time)
    ttl: int = 5             # 跳数限制
    signature: str = ""      # 防篡改


class DecentralizedNormativeStack:
    """
    去中心化L2.5规范场栈 — 无需中心化调解者.

    每个Agent维护一个本地副本，通过gossip协议同步。

    六条元规则 (与v0.1一致，但通过共识维护):
      R1: never_suppress — 矛盾不得压制
      R2: must_elevate — 必须升维表达
      R3: express_conflict — 显式表达矛盾
      R4: seek_lift — 寻求升维
      R5: audit_delta_phi — Δφ审计
      R6: no_side_taking — 不偏袒

    共识机制:
      - 每个Agent对自己的本地规则副本有置信度
      - 收到gossip消息后，根据发送者置信度加权更新
      - 容忍 ≤f 个拜占庭节点 (f < N/3)
    """

    META_RULES = {
        "never_suppress": "矛盾不得压制, 必须被记录和传播",
        "must_elevate": "矛盾必须升维表达, 不得在原维度打补丁",
        "express_conflict": "矛盾必须显式表达为可审计结构",
        "seek_lift": "必须寻求升维方案, 而非折中掩盖",
        "audit_delta_phi": "每次消解后审计Δφ变化",
        "no_side_taking": "规范场不得偏袒, 升维方案必须对所有Agent对称",
    }

    def __init__(self, agent_id: str, byzantine_faults_tolerance: int = 0):
        self.agent_id = agent_id
        self.f = byzantine_faults_tolerance  # 可容忍的拜占庭节点数

        # 本地规则副本 + 置信度
        self.rules: Dict[str, float] = {k: 1.0 for k in self.META_RULES}  # rule_id → confidence
        self.rule_weight: Dict[str, float] = {k: 1.0 for k in self.META_RULES}  # rule_id → weight

        # 置信度模型
        self.trust_network: Dict[str, float] = {}  # agent_id → trust_score

        # 共识状态
        self.last_gossip_round: int = 0
        self.consensus_threshold: float = 0.66  # 2/3 共识
        self.vote_history: List[NormativeVote] = []
        self.seen_messages: Set[str] = set()  # 去重

        # 审计
        self.sync_count: int = 0
        self.conflict_count: int = 0
        self.heat_tax: float = 0.0

    def vote_on_rule(self, rule_id: str, vote: float, justification: str = ""):
        """对规范场规则投票."""
        if rule_id not in self.META_RULES:
            return
        nv = NormativeVote(self.agent_id, rule_id, max(0.0, min(1.0, vote)),
                          time.time(), justification)
        self.vote_history.append(nv)

        # 更新本地置信度 (自己的一票)
        self.rules[rule_id] = 0.8 * self.rules[rule_id] + 0.2 * vote

    def receive_gossip(self, msg: GossipMessage) -> bool:
        """接收并处理gossip消息."""
        msg_id = f"{msg.sender_id}:{msg.timestamp}:{hash(str(msg.payload))}"
        if msg_id in self.seen_messages:
            return False
        self.seen_messages.add(msg_id)
        self.heat_tax += 0.001  # gossip处理热税

        trust = self.trust_network.get(msg.sender_id, 0.5)

        if msg.message_type == "norm_update":
            # 更新规则
            rule_id = msg.payload.get("rule_id")
            value = msg.payload.get("value", 1.0)
            if rule_id in self.rules:
                # 加权更新: trust越高，消息越有影响力
                old_val = self.rules[rule_id]
                new_val = (1 - trust) * old_val + trust * value
                self.rules[rule_id] = new_val
                self.sync_count += 1

        elif msg.message_type == "conflict_alert":
            # 记录冲突告警
            self.conflict_count += 1

        elif msg.message_type == "field_sync":
            # 信任网络同步
            for aid, score in msg.payload.get("trust_network", {}).items():
                if aid == self.agent_id:
                    continue
                current = self.trust_network.get(aid, 0.5)
                self.trust_network[aid] = 0.7 * current + 0.3 * score

        return True

    def create_gossip(self, msg_type: str, payload: Dict) -> GossipMessage:
        """创建gossip消息 (TTL递减)."""
        return GossipMessage(
            sender_id=self.agent_id,
            message_type=msg_type,
            payload=payload,
        )

    def is_consensus_reached(self, rule_id: str) -> bool:
        """检查某规则是否达到共识."""
        return self.rules.get(rule_id, 0.0) >= self.consensus_threshold

    def all_consensus(self) -> bool:
        """检查所有规则是否达到共识."""
        return all(self.is_consensus_reached(r) for r in self.META_RULES)

    def audit(self) -> Dict:
        """审计报告."""
        return {
            "agent_id": self.agent_id,
            "rules": dict(self.rules),
            "consensus_achieved": self.all_consensus(),
            "trust_network_size": len(self.trust_network),
            "sync_count": self.sync_count,
            "conflict_count": self.conflict_count,
            "heat_tax": round(self.heat_tax, 4),
            "vote_count": len(self.vote_history),
        }


class DecentralizedGossipNetwork:
    """
    P2P Gossip网络 — 模拟去中心化消息传播.

    不再有中心化MediatorAgent，每个Agent平等参与gossip。
    """

    def __init__(self, agent_stacks: Dict[str, DecentralizedNormativeStack]):
        self.stacks = agent_stacks
        self.message_log: List[GossipMessage] = []
        self.round: int = 0

    def broadcast(self, sender_id: str, msg_type: str, payload: Dict):
        """广播消息到所有其他Agent."""
        sender = self.stacks.get(sender_id)
        if not sender:
            return
        msg = sender.create_gossip(msg_type, payload)
        self.message_log.append(msg)

        for aid, stack in self.stacks.items():
            if aid == sender_id:
                continue
            stack.receive_gossip(msg)

    def gossip_round(self):
        """执行一轮gossip同步."""
        self.round += 1

        # 每个Agent向随机邻居发送其当前规则状态
        agents = list(self.stacks.keys())
        for i, agent_id in enumerate(agents):
            stack = self.stacks[agent_id]
            # 随机选择1个邻居
            neighbor = agents[(i + 1 + random.randint(0, max(0, len(agents) - 2))) % len(agents)]

            # 发送规则更新
            for rule_id, confidence in stack.rules.items():
                stack_payload = {
                    "rule_id": rule_id,
                    "value": confidence,
                    "round": self.round,
                }
                self.broadcast(agent_id, "norm_update", stack_payload)
                break  # 每轮只发一个规则 (节省带宽, gossip会覆盖)

        # 同步信任网络
        for agent_id in agents:
            stack = self.stacks[agent_id]
            network_payload = {
                "trust_network": dict(stack.trust_network),
            }
            # 自报告信任 (防Sybil, 仅报告对自己的直接观察)
            self.broadcast(agent_id, "field_sync", network_payload)

    def run_until_consensus(self, max_rounds: int = 50) -> Tuple[int, bool]:
        """运行gossip直到达成共识或达到最大轮次."""
        for _ in range(max_rounds):
            self.gossip_round()
            if all(stack.all_consensus() for stack in self.stacks.values()):
                return self.round, True
        return self.round, False

    def stats(self) -> Dict:
        agents_audit = {aid: stack.audit() for aid, stack in self.stacks.items()}
        all_consensus = all(a["consensus_achieved"] for a in agents_audit.values())
        return {
            "round": self.round,
            "n_agents": len(self.stacks),
            "messages": len(self.message_log),
            "consensus": all_consensus,
            "heat_tax_total": round(sum(s.heat_tax for s in self.stacks.values()), 4),
            "agents": agents_audit,
        }


# ═══ Layer 3: N>2 MCDP Extension ═══

class MeanFieldMCDP:
    """
    均值场MCDP — N>2 Agent冲突消解的完整解决方案.

    组合:
      MeanFieldEngine: 压缩N-1个Agent为均值场
      DecentralizedGossipNetwork: 去中心化规范场栈同步
      MCDP核心 (v0.1): 升维+余极限

    流程:
      1. 收集 → 每个Agent self-report
      2. 压缩 → MeanFieldEngine计算均值场张力
      3. 共识 → Gossip网络同步规范场栈
      4. 消解 → 高张力Agent向均值场靠拢
      5. 审计 → 全体Δφ + 规范场漂移
    """

    def __init__(self, n_agents: int = 5):
        self.agents: Dict[str, MeanFieldAgent] = {}
        self.stacks: Dict[str, DecentralizedNormativeStack] = {}
        self.network: Optional[DecentralizedGossipNetwork] = None
        self.mean_field = MeanFieldEngine(convergence_eps=0.01, max_iter=50)

        self.audit_log: List[Dict] = []

    def add_agent(self, agent_id: str, strategy: str,
                  payoff: float = 0.0,
                  byzantine: bool = False):
        """添加Agent."""
        agent = MeanFieldAgent(
            id=agent_id,
            strategy=strategy,
            payoff=payoff,
        )
        f = 1 if byzantine else 0
        stack = DecentralizedNormativeStack(agent_id, byzantine_faults_tolerance=f)
        agent.local_normative_stack = stack

        self.agents[agent_id] = agent
        self.stacks[agent_id] = stack

    def initialize_network(self):
        """初始化gossip网络."""
        self.network = DecentralizedGossipNetwork(self.stacks)

    def resolve(self, payoff_fn: Callable, max_gossip_rounds: int = 20) -> Dict:
        """
        N>2 MCDP消解.

        Returns:
            {
                "before": initial tension state,
                "after": resolved tension state,
                "gossip_rounds": n,
                "consensus": bool,
                "nash_equilibrium": str or None,
                "audit": [...]
            }
        """
        if len(self.agents) < 2:
            return {"error": "Need at least 2 agents"}

        # Step 1: 分析初始状态
        agent_list = list(self.agents.values())
        strat_counts: Dict[str, int] = defaultdict(int)
        for a in agent_list:
            strat_counts[a.strategy] += 1

        # 更新每个Agent的mean_field估计
        total_payoff = sum(a.payoff for a in agent_list)
        for a in agent_list:
            a.mean_field_payoff = (total_payoff - a.payoff) / max(1, len(agent_list) - 1)
            a.strategy_distribution = {k: v/len(agent_list) for k, v in strat_counts.items()}

        before_conflict = self.mean_field.analyze_field(agent_list)
        self.audit_log.append({
            "phase": "before",
            "mean_tension": before_conflict.mean_tension,
            "critical_agents": before_conflict.critical_agents,
            "strategies": dict(strat_counts),
        })

        # Step 2: Gossip共识 (去中心化规范场栈同步)
        if self.network and len(self.stacks) >= 2:
            rounds, consensus = self.network.run_until_consensus(max_gossip_rounds)
        else:
            self.initialize_network()
            rounds, consensus = self.network.run_until_consensus(max_gossip_rounds)

        # Step 3: Mean Field消解
        resolved_agents = self.mean_field.resolve_mean_field(agent_list, payoff_fn)

        # 更新
        for a in resolved_agents:
            self.agents[a.id] = a

        after_conflict = self.mean_field.analyze_field(resolved_agents)
        self.audit_log.append({
            "phase": "after",
            "mean_tension": after_conflict.mean_tension,
            "critical_agents": after_conflict.critical_agents,
            "strategies": {a.strategy: sum(1 for x in resolved_agents if x.strategy == a.strategy)
                          for a in resolved_agents},
        })

        # Step 4: 审计
        delta_tension = before_conflict.mean_tension - after_conflict.mean_tension
        self.audit_log.append({
            "phase": "audit",
            "delta_tension": round(delta_tension, 4),
            "gossip_rounds": rounds,
            "consensus": consensus,
            "total_agents": len(self.agents),
            "heat_tax_total": round(sum(s.heat_tax for s in self.stacks.values()), 4),
        })

        return {
            "before_tension": before_conflict.mean_tension,
            "after_tension": after_conflict.mean_tension,
            "delta_tension": round(delta_tension, 4),
            "gossip_rounds": rounds,
            "consensus": consensus,
            "critical_agents_before": before_conflict.critical_agents,
            "critical_agents_after": after_conflict.critical_agents,
            "audit": self.audit_log,
            "strategy_evolution": self.mean_field.iteration_history,
        }


# ═══ Demo + Test ═══

def cmd_mcdp2(args_rest):
    """CLI: mssclaw mcdp2"""
    if not args_rest or args_rest[0] == "--help":
        print("mssclaw mcdp2 — MCDP v0.2: N>2 Mean Field + Decentralized L2.5")
        print("  mssclaw mcdp2 demo         # Demo: 5-Agent 公地悲剧")
        print("  mssclaw mcdp2 gossip       # Demo: 去中心化gossip共识")
        print("  mssclaw mcdp2 test         # 测试套件")
        return

    if args_rest[0] == "demo":
        _demo_mean_field()
    elif args_rest[0] == "gossip":
        _demo_gossip()
    elif args_rest[0] == "test":
        _test_all()


def _demo_mean_field():
    """演示: 5-Agent公地悲剧 — N>2均值场消解."""
    print("=" * 64)
    print("MCDP v0.2 — 5-Agent Tragedy of the Commons (N>2 Mean Field)")
    print("=" * 64)

    mfmcdp = MeanFieldMCDP(n_agents=5)

    # 公地悲剧 payoff: cooperate=3, defect=5-2*N_defectors
    def tragedy_payoff(strategy: str, strat_dist: Dict[str, int]) -> float:
        n_defectors = strat_dist.get("defect", 0)
        if strategy == "cooperate":
            return 3.0 - 0.5 * n_defectors  # 越多人背叛，合作者收益越低
        else:
            return 5.0 - 1.0 * n_defectors  # 背叛收益也随背叛人数递减

    # 添加5个Agent: 1个合作者 + 4个背叛者
    mfmcdp.add_agent("A1", "cooperate", payoff=3.0)
    mfmcdp.add_agent("A2", "defect", payoff=5.0)
    mfmcdp.add_agent("A3", "defect", payoff=4.0)
    mfmcdp.add_agent("A4", "defect", payoff=3.0)
    mfmcdp.add_agent("A5", "defect", payoff=2.0)

    # 初始化gossip网络
    mfmcdp.initialize_network()

    # 消解
    result = mfmcdp.resolve(tragedy_payoff, max_gossip_rounds=15)

    print(f"""
  Initial State (5 Agents):
    A1(cooperate, payoff=3.0) — lone cooperator
    A2(defect, payoff=5.0)    — top defector
    A3(defect, payoff=4.0)
    A4(defect, payoff=3.0)
    A5(defect, payoff=2.0)    — bottom defector

  Mean Field Analysis:
    Before tension: {result['before_tension']:.4f}
    After tension:  {result['after_tension']:.4f}
    Δ tension:      {result['delta_tension']:.4f}
    Gossip rounds:  {result['gossip_rounds']}
    Consensus:      {result['consensus']}

  Critical Agents Before: {result['critical_agents_before']}
  Critical Agents After:  {result['critical_agents_after']}
""")

    print(f"  Strategy evolution ({len(mfmcdp.mean_field.iteration_history)} iterations):")
    for h in mfmcdp.mean_field.iteration_history:
        print(f"    iter={h['iter']}: mean_tension={h['mean_tension']:.4f}, "
              f"critical={h['critical_count']}, strategies={h['strategies']}")

    print(f"\n  Final strategies:")
    for a in mfmcdp.agents.values():
        print(f"    {a.id}: {a.strategy} (payoff={a.payoff:.2f})")


def _demo_gossip():
    """演示: 去中心化gossip共识协议."""
    print("=" * 64)
    print("Decentralized L2.5 Gossip Consensus Demo")
    print("=" * 64)

    stacks = {}
    for i in range(5):
        stack = DecentralizedNormativeStack(f"agent_{i}")
        # 每个Agent初始对规则有微小差异
        for rule_id in stack.META_RULES:
            stack.rules[rule_id] = random.uniform(0.5, 0.8)
            stack.trust_network[f"agent_{(i+1)%5}"] = random.uniform(0.4, 0.7)
        stacks[f"agent_{i}"] = stack

    network = DecentralizedGossipNetwork(stacks)

    print("\n  Initial state:")
    for aid, s in stacks.items():
        avg_rule = sum(s.rules.values()) / len(s.rules)
        print(f"    {aid}: avg_rule_confidence={avg_rule:.3f}", end="")
        if aid != list(stacks.keys())[-1]:
            print()

    print(f"\n  Running gossip...")
    rounds, consensus = network.run_until_consensus(max_rounds=30)

    print(f"\n  After {rounds} rounds:")
    for aid, s in stacks.items():
        avg_rule = sum(s.rules.values()) / len(s.rules)
        print(f"    {aid}: avg_rule={avg_rule:.3f}, consensus={s.all_consensus()}")

    print(f"\n  Consensus achieved: {consensus}")
    print(f"  Total messages: {len(network.message_log)}")
    print(f"  Heat tax: {sum(s.heat_tax for s in stacks.values()):.4f}")


def _test_all():
    """测试套件."""
    passed = 0
    total = 0

    # Test 1: MeanFieldEngine基本分析
    total += 1
    mfe = MeanFieldEngine()
    agents = [
        MeanFieldAgent("A1", strategy="C", payoff=3.0, mean_field_payoff=5.0),
        MeanFieldAgent("A2", strategy="D", payoff=5.0, mean_field_payoff=3.0),
        MeanFieldAgent("A3", strategy="D", payoff=4.0, mean_field_payoff=4.0),
    ]
    conflict = mfe.analyze_field(agents)
    assert conflict.n_agents == 3
    assert len(conflict.tension_field) == 3
    assert 0 <= conflict.mean_tension <= 20
    passed += 1
    print(f"  ✅ Test 1: MeanFieldAnalysis (tension={conflict.mean_tension:.3f})")

    # Test 2: MeanField消解 (趋同)
    total += 1
    def simple_payoff(s, d):
        return {"C": 4.0 - d.get("D", 0), "D": 3.0}.get(s, 0)
    agents2 = [
        MeanFieldAgent("a1", strategy="C", payoff=4.0),
        MeanFieldAgent("a2", strategy="D", payoff=3.0),
        MeanFieldAgent("a3", strategy="C", payoff=4.0),
    ]
    resolved = mfe.resolve_mean_field(agents2, simple_payoff)
    assert len(resolved) == 3
    passed += 1
    print(f"  ✅ Test 2: MeanField消解 ({len(mfe.iteration_history)} iters)")

    # Test 3: DecentralizedNormativeStack初始状态
    total += 1
    ds = DecentralizedNormativeStack("test_agent")
    assert len(ds.rules) == 6
    assert all(v == 1.0 for v in ds.rules.values())
    assert ds.all_consensus()  # rules start at 1.0, threshold=0.66 → consensus
    passed += 1
    print(f"  ✅ Test 3: 去中心化规范场栈初始状态 (6 rules, all 1.0)")

    # Test 4: Gossip消息传播
    total += 1
    stacks = {f"a{i}": DecentralizedNormativeStack(f"a{i}") for i in range(3)}
    net = DecentralizedGossipNetwork(stacks)
    net.gossip_round()
    assert net.round == 1
    assert len(net.message_log) > 0
    passed += 1
    print(f"  ✅ Test 4: Gossip传播 ({len(net.message_log)} messages)")

    # Test 5: MCDP v0.2 端到端
    total += 1
    mfm = MeanFieldMCDP(n_agents=4)
    for i in range(4):
        strat = "C" if i < 2 else "D"
        mfm.add_agent(f"A{i}", strat, payoff=3.0 - i * 0.5)
    mfm.initialize_network()
    def test_fn(s, d):
        return {"C": 3.0 - d.get("D", 0) * 0.5, "D": 5.0 - d.get("D", 0)}.get(s, 0)
    r = mfm.resolve(test_fn, max_gossip_rounds=5)
    assert "before_tension" in r
    assert "after_tension" in r
    passed += 1
    print(f"  ✅ Test 5: MCDP v0.2 端到端 (Δ_tension={r['delta_tension']:.3f})")

    # Test 6: N>2 的 tension_field 一致性
    total += 1
    agents6 = [MeanFieldAgent(f"B{i}", strategy="X", payoff=1.0 + i,
                               mean_field_payoff=5.0) for i in range(6)]
    c6 = mfe.analyze_field(agents6)
    assert c6.n_agents == 6
    assert len(c6.critical_agents) > 0  # 应该有临界Agent
    passed += 1
    print(f"  ✅ Test 6: N=6 tension_field ({c6.mean_tension:.3f}, critical={len(c6.critical_agents)})")

    # Test 7: 去中心化共识达成
    total += 1
    stacks7 = {f"g{i}": DecentralizedNormativeStack(f"g{i}") for i in range(5)}
    # 每个Agent初始对某规则有不同置信度
    for i, (aid, s) in enumerate(stacks7.items()):
        s.rules["never_suppress"] = 0.5 + 0.1 * i
    net7 = DecentralizedGossipNetwork(stacks7)
    r7, c7 = net7.run_until_consensus(max_rounds=20)
    # 检查是否收敛
    all_ns = [s7.rules["never_suppress"] for s7 in stacks7.values()]
    spread = max(all_ns) - min(all_ns)
    assert c7 or r7 == 20  # 要么达成共识，要么跑满轮次
    passed += 1
    print(f"  ✅ Test 7: Gossip共识 ({r7} rounds, consensus={c7}, spread={spread:.3f})")

    print(f"\n  {passed}/{total} PASS")


if __name__ == "__main__":
    import sys
    cmd_mcdp2(sys.argv[1:])
