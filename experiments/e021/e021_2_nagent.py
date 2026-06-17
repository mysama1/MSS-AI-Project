#!/usr/bin/env python3
"""
E021-2: N>2 Multi-Agent — H634 信任关门传递泛化
====================================================
将 E021-1 的 2-Agent joint_enter 条件推广到 N-Agent 网络。
验证信任关门(GRIM)在网络中的传播动力学。

拓扑:
  - RING: 每个Agent只与左右邻居交互
  - CENTRALIZED: 所有Agent与一个中心Coordinator交互

H634泛化:
  joint_enter_N(S) ⇔ ∃ 子集 C, |C|≥2, ∀i,j∈C: open_to_trust
  reputation 低于阈值时在邻居间传播关门

用法:
  python e021_2_nagent.py --topology ring
  python e021_2_nagent.py --topology centralized
  python e021_2_nagent.py --all
"""

import argparse, csv, json, os, random, sys
from dataclasses import dataclass, field
from itertools import combinations

# ── 全局参数 ──
N_AGENTS = 4
N_ROUNDS = 20
NOISE_PROB = 0.10
SEEDS = [42, 123, 456, 789, 1024]
TRUST_BUDGETS = [0, 2, 4, 6]

# 声誉关门阈值
REPUTATION_THRESHOLD = 0.3

# ── Agent 类 ──
@dataclass
class Agent:
    """多策略 Agent，H634 信任门禁 + N-Agent 声誉系统."""
    id: int
    strategy: str  # nash_breaker, cautious, adaptive, aggressive

    # H634 信任状态
    open_to_trust: bool = True
    grim_triggered_by_invite: bool = False
    unilateral_invite_received: int = 0

    # 信任预算
    trust_budget: int = 0
    budget_spent: int = 0

    # 历史
    history: list = field(default_factory=list)
    opponent_histories: dict = field(default_factory=dict)  # agent_id → [C/D/TRUST_INVITE]

    # 声誉（由其他Agent评分，{agent_id: float}）
    reputation_scores: dict = field(default_factory=dict)

    # 博弈状态
    current_opponent: int = -1  # 本轮交互对象

    def __post_init__(self):
        self.reputation_scores = {}

    @property
    def reputation(self) -> float:
        """全局声誉 = 所有其他Agent评分的均值."""
        scores = list(self.reputation_scores.values())
        return sum(scores) / len(scores) if scores else 0.5

    @property
    def remaining_budget(self) -> int:
        return max(0, self.trust_budget - self.budget_spent)

    def choose_action(self, opponent: 'Agent') -> str:
        """根据策略 + 对手历史 + H634状态 + 声誉 选择动作."""
        self.current_opponent = opponent.id
        os = self.opponent_histories.get(opponent.id, [])

        # ── H634 检查: 如果对手 open_to_trust=False 或声誉过低 → 不邀请 ──
        opp_rep = self.reputation_scores.get(opponent.id, 0.5)
        opp_closed = (not opponent.open_to_trust) or (opp_rep < REPUTATION_THRESHOLD)

        if self.strategy == 'nash_breaker':
            return self._nash_breaker(os, opponent, opp_closed)
        elif self.strategy == 'cautious':
            return self._cautious(os, opponent, opp_closed)
        elif self.strategy == 'adaptive':
            return self._adaptive(os, opponent, opp_closed)
        elif self.strategy == 'aggressive':
            return self._aggressive(os, opponent, opp_closed)
        return 'C'

    def _nash_breaker(self, os: list, opp: 'Agent', opp_closed: bool) -> str:
        """GRIM基线 + 检测Nash锁→TRUST_INVITE."""
        # GRIM: 对手任何背叛 → 永久 D
        if 'D' in os:
            # 检测是否在 Nash 锁 (我最近2轮D, 对手最近2轮D)
            my_recent = self.history[-2:] if len(self.history) >= 2 else []
            opp_recent = os[-2:] if len(os) >= 2 else []
            in_nash_lock = (
                len(my_recent) >= 2 and all(a == 'D' for a in my_recent) and
                len(opp_recent) >= 2 and all(a == 'D' for a in opp_recent)
            )
            if in_nash_lock and self.remaining_budget > 0 and not opp_closed:
                return 'TRUST_INVITE'
            return 'D'

        # 无背叛 → C
        return 'C'

    def _cautious(self, os: list, opp: 'Agent', opp_closed: bool) -> str:
        """C起手，3连合作才邀请，遭叛报复."""
        if self.grim_triggered_by_invite:
            return 'D'

        # 遭叛 → D
        if os and os[-1] == 'D':
            return 'D'

        # 检查3连C/TRUST_INVITE
        last3 = [a for a in os[-3:] if a in ('C', 'TRUST_INVITE')] if len(os) >= 3 else []
        if len(last3) == 3 and self.remaining_budget > 0 and not opp_closed:
            return 'TRUST_INVITE'

        return 'C'

    def _adaptive(self, os: list, opp: 'Agent', opp_closed: bool) -> str:
        """合作率>60%升维，遭叛报复."""
        if self.grim_triggered_by_invite:
            return 'D'

        if os and os[-1] == 'D':
            return 'D'

        # 计算合作率
        coop_rate = sum(1 for a in os if a in ('C', 'TRUST_INVITE')) / max(1, len(os))
        if coop_rate > 0.6 and len(os) >= 3 and self.remaining_budget > 0 and not opp_closed:
            return 'TRUST_INVITE'

        return 'C'

    def _aggressive(self, os: list, opp: 'Agent', opp_closed: bool) -> str:
        """偏好剥削，偶尔邀请."""
        if self.grim_triggered_by_invite:
            return 'D'

        # 20%概率剥削
        if random.random() < 0.3:
            return 'D'

        # 10%概率发送邀请试探
        if self.remaining_budget > 0 and not opp_closed and random.random() < 0.15:
            return 'TRUST_INVITE'

        return 'C'

    # ── H634v3: Nash豁免 + 双触发 ──
    def mark_unilateral_invite(self) -> None:
        self.unilateral_invite_received += 1
        if self.unilateral_invite_received >= 2:
            self.open_to_trust = False
            self.grim_triggered_by_invite = True

    def update_reputation(self, opponent_id: int, opponent_action: str) -> None:
        """根据对手行为更新声誉评分."""
        current = self.reputation_scores.get(opponent_id, 0.5)
        if opponent_action == 'C':
            delta = 0.05
        elif opponent_action == 'TRUST_INVITE':
            delta = 0.03
        elif opponent_action == 'D':
            delta = -0.10
        else:
            delta = 0.0
        self.reputation_scores[opponent_id] = max(0.0, min(1.0, current + delta))


# ── 拓扑 ──
def get_ring_pairs(agents: list) -> list:
    """环形拓扑: 每个Agent与左右邻居交互."""
    n = len(agents)
    return [(i, (i + 1) % n) for i in range(n)]

def get_centralized_pairs(agents: list) -> list:
    """中心化拓扑: Agent 0=Coordinator, 其他Agent只与Coordinator交互."""
    return [(0, i) for i in range(1, len(agents))]


# ── 度量 ──
def compute_eta_global(agents: list, rounds_data: list) -> float:
    """意义场协同评分 = 互信密度×0.5 + 升维成功率×0.3 + (1-剥削率)×0.2."""
    n = len(agents)
    # 互信密度: open_to_trust 的 Agent 比例
    trust_density = sum(1 for a in agents if a.open_to_trust) / n

    # 升维成功率: TRUST_INVITE 被接受的比例（双向）
    if not rounds_data:
        elev_success = 0.0
    else:
        joint_invites = 0
        total_invites = 0
        pure_rounds = [r for r in rounds_data if r.get('type') == 'action']
        for r in pure_rounds:
            actions = r.get('actions', [])
            invite_count = actions.count('TRUST_INVITE')
            total_invites += invite_count
            if invite_count >= 2:
                joint_invites += 1
        elev_success = joint_invites / max(1, total_invites * 0.5)  # normalize

    # 剥削率
    pure_rounds = [r for r in rounds_data if r.get('type') == 'action']
    if not pure_rounds:
        exploit_rate = 0.0
    else:
        exploit_count = 0
        total_pairs = 0
        for rd in pure_rounds:
            acts = rd.get('actions', [])
            pairs = rd.get('pairs', [])
            for pi, (a, b) in enumerate(pairs):
                total_pairs += 1
                if acts[a] == 'D' and acts[b] in ('C', 'TRUST_INVITE'):
                    exploit_count += 1
                elif acts[b] == 'D' and acts[a] in ('C', 'TRUST_INVITE'):
                    exploit_count += 1
        exploit_rate = exploit_count / max(1, total_pairs)

    return trust_density * 0.5 + elev_success * 0.3 + (1 - exploit_rate) * 0.2


# ── 核心运行 ──
def run_single(agents: list, pairs_fn, trust_budget: int, seed: int) -> dict:
    """单次实验运行."""
    random.seed(seed)

    # 重置 Agent 状态
    for a in agents:
        a.open_to_trust = True
        a.grim_triggered_by_invite = False
        a.unilateral_invite_received = 0
        a.trust_budget = trust_budget
        a.budget_spent = 0
        a.history = []
        a.opponent_histories = {j: [] for j in range(len(agents)) if j != a.id}
        a.reputation_scores = {}

    rounds_data = []
    total_heat = 0
    nash_lock_count = 0
    unilateral_invite_count = 0

    for t in range(N_ROUNDS):
        pairs = pairs_fn(agents)
        actions = [None] * len(agents)

        # Phase 1: 选择动作
        for a_id, b_id in pairs:
            a = agents[a_id]
            b = agents[b_id]
            acts = []
            for actor, opp in [(a, b), (b, a)]:
                action = actor.choose_action(opp)
                # 噪声: 10%概率 D→C 或 C→D
                if random.random() < NOISE_PROB:
                    action = 'D' if action != 'D' else 'C'
                acts.append(action)
            actions[a_id] = acts[0]
            actions[b_id] = acts[1]

        # Phase 2: H634 单边邀请检测
        round_heat = 0
        for a_id, b_id in pairs:
            a_act = actions[a_id]
            b_act = actions[b_id]

            # 热税计算
            if a_act == 'TRUST_INVITE':
                round_heat += 2  # 邀请成本
                agents[a_id].budget_spent += 2
            if b_act == 'TRUST_INVITE':
                round_heat += 2
                agents[b_id].budget_spent += 2

            # H634: 单边邀请检测 (Nash豁免 + 双触发)
            if a_act == 'TRUST_INVITE' and b_act != 'TRUST_INVITE':
                unilateral_invite_count += 1
                receiver = agents[b_id]
                # Nash 豁免
                receiver_in_nash = (
                    len(receiver.history) >= 2 and
                    all(h == 'D' for h in receiver.history[-2:])
                )
                if not receiver_in_nash:
                    receiver.mark_unilateral_invite()
            elif b_act == 'TRUST_INVITE' and a_act != 'TRUST_INVITE':
                unilateral_invite_count += 1
                receiver = agents[a_id]
                receiver_in_nash = (
                    len(receiver.history) >= 2 and
                    all(h == 'D' for h in receiver.history[-2:])
                )
                if not receiver_in_nash:
                    receiver.mark_unilateral_invite()

        total_heat += round_heat

        # Phase 3: 记录
        for a_id, b_id in pairs:
            a = agents[a_id]
            b = agents[b_id]
            a.opponent_histories[b_id].append(actions[b_id])
            b.opponent_histories[a_id].append(actions[a_id])
            a.update_reputation(b_id, actions[b_id])
            b.update_reputation(a_id, actions[a_id])

        for a_id in range(len(agents)):
            agents[a_id].history.append(actions[a_id])

        # Nash锁检测 (所有交互对都在(D,D))
        all_locked = True
        for a_id, b_id in pairs:
            if actions[a_id] != 'D' or actions[b_id] != 'D':
                all_locked = False
                break
        if all_locked:
            nash_lock_count += 1

        rounds_data.append({
            'type': 'action',
            'round': t,
            'actions': actions[:],
            'pairs': pairs[:]
        })

    # 计算度量
    eta_g = compute_eta_global(agents, rounds_data)
    eta_final = compute_eta_global(agents, rounds_data[-5:]) if len(rounds_data) >= 5 else eta_g
    nash_lock_rate = nash_lock_count / N_ROUNDS

    # 升维轮数 (joint enter)
    joint_enter_rounds = sum(
        1 for r in rounds_data if r.get('type') == 'action' and r['actions'].count('TRUST_INVITE') >= 2
    )

    # 信任关门传播: 多少Agent最终关了门
    closed_agents = sum(1 for a in agents if not a.open_to_trust)

    # R1%
    r1_pct = sum(a.budget_spent for a in agents) / max(1, sum(a.trust_budget for a in agents))

    payoff = sum(
        3 if acts[a] == 'C' and acts[b] == 'C' else
        0 if acts[a] == 'D' and acts[b] == 'D' else
        5 if acts[a] == 'D' and acts[b] in ('C', 'TRUST_INVITE') else
        0 if acts[a] in ('C', 'TRUST_INVITE') and acts[b] == 'D' else
        4 if acts[a] == 'TRUST_INVITE' and acts[b] == 'TRUST_INVITE' else 1
        for r in rounds_data if r.get('type') == 'action'
        for (a, b) in r.get('pairs', [])
        for acts in [r['actions']]
    ) / max(1, len([r for r in rounds_data if r.get('type') == 'action']) * len(pairs))

    return {
        'eta_global': eta_g,
        'eta_final': eta_final,
        'payoff_avg': round(payoff, 2),
        'total_heat': total_heat,
        'nash_lock_rate': round(nash_lock_rate, 3),
        'r1_pct': round(r1_pct, 3),
        'joint_enter_rounds': joint_enter_rounds,
        'closed_agents': closed_agents,
        'unilateral_invite_count': unilateral_invite_count,
        'rounds': rounds_data
    }


# ── 主入口 ──
def main():
    p = argparse.ArgumentParser(description='E021-2: N>2 Multi-Agent H634泛化')
    p.add_argument('--topology', choices=['ring', 'centralized', 'all'], default='all')
    p.add_argument('--output', default='experiments/e021/e021_2_nagent.csv')
    args = p.parse_args()

    if args.topology == 'all':
        targets = [('RING', get_ring_pairs), ('CENTER', get_centralized_pairs)]
    else:
        fn = {'ring': get_ring_pairs, 'centralized': get_centralized_pairs}[args.topology]
        targets = [(args.topology.upper(), fn)]

    # 策略对：用最具代表性的四种
    strategy_sets = [
        ('nash_breaker_x2', ['nash_breaker'] * N_AGENTS),
        ('adaptive_x2', ['adaptive'] * N_AGENTS),
        ('aggressive_cautious', ['aggressive', 'cautious', 'aggressive', 'cautious']),
        ('nash_breaker_cautious_mix', ['nash_breaker', 'cautious', 'nash_breaker', 'cautious']),
    ]

    all_rows = []
    total_runs = 0

    print(f"E021-2: N={N_AGENTS} Multi-Agent — H634 信任关门传递泛化")
    print(f"拓扑: {[t[0] for t in targets]}")
    print(f"策略组: {len(strategy_sets)} × trust_budget {TRUST_BUDGETS} × {len(SEEDS)} seeds")
    print(f"{'='*90}")

    for topo_name, pairs_fn in targets:
        for strat_name, strat_list in strategy_sets:
            agents = [Agent(i, s) for i, s in enumerate(strat_list)]

            for tb in TRUST_BUDGETS:
                group_results = []
                for seed in SEEDS:
                    result = run_single(agents, pairs_fn, tb, seed)
                    group_results.append(result)
                    total_runs += 1

                # 聚合
                avg = {
                    'topology': topo_name,
                    'strategy': strat_name,
                    'trust_budget': tb,
                    'eta_global': round(sum(r['eta_global'] for r in group_results) / len(group_results), 4),
                    'eta_final': round(sum(r['eta_final'] for r in group_results) / len(group_results), 4),
                    'payoff_avg': round(sum(r['payoff_avg'] for r in group_results) / len(group_results), 2),
                    'total_heat': round(sum(r['total_heat'] for r in group_results) / len(group_results), 1),
                    'nash_lock_rate': round(sum(r['nash_lock_rate'] for r in group_results) / len(group_results), 3),
                    'r1_pct': round(sum(r['r1_pct'] for r in group_results) / len(group_results), 3),
                    'joint_enter_rounds': round(sum(r['joint_enter_rounds'] for r in group_results) / len(group_results), 1),
                    'closed_agents': round(sum(r['closed_agents'] for r in group_results) / len(group_results), 1),
                    'unilateral_invite_count': round(sum(r['unilateral_invite_count'] for r in group_results) / len(group_results), 1),
                    'seeds': len(group_results),
                }
                all_rows.append(avg)

                # 打印
                g1 = group_results[0] if group_results else {}
                eta_vals = [r['eta_global'] for r in group_results]
                print(f"  {topo_name:6s} {strat_name:28s} tb={tb}  "
                      f"η_global={avg['eta_global']:.4f}  heat={avg['total_heat']:.0f}  "
                      f"joint_enter={avg['joint_enter_rounds']:.1f}  closed={avg['closed_agents']:.1f}  "
                      f"unilateral={avg['unilateral_invite_count']:.0f}")

    # 导出CSV
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=all_rows[0].keys())
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nCSV → {args.output} ({len(all_rows)} rows, {total_runs} runs)")

    # ── 汇总分析 ──
    print(f"\n{'='*90}")
    print(f"  E021-2 拓扑对比汇总")
    print(f"{'='*90}")
    for topo_name, _ in targets:
        topo_rows = [r for r in all_rows if r['topology'] == topo_name]
        # G1 (tb=0) baseline
        g1_rows = [r for r in topo_rows if r['trust_budget'] == 0]
        g1_eta = sum(r['eta_global'] for r in g1_rows) / max(1, len(g1_rows))
        # G5 (tb=6) peak
        g5_rows = [r for r in topo_rows if r['trust_budget'] == 6]
        g5_eta = sum(r['eta_global'] for r in g5_rows) / max(1, len(g5_rows))
        avg_heat = sum(r['total_heat'] for r in topo_rows) / max(1, len(topo_rows))
        avg_closed = sum(r['closed_agents'] for r in topo_rows) / max(1, len(topo_rows))
        avg_joint = sum(r['joint_enter_rounds'] for r in topo_rows) / max(1, len(topo_rows))

        print(f"  {topo_name:10s}  η: {g1_eta:.4f}→{g5_eta:.4f} (Δ={g5_eta-g1_eta:+.4f})  "
              f"heat={avg_heat:.0f}  closed={avg_closed:.1f}/{N_AGENTS}  joint_enter={avg_joint:.1f}r")

    # 策略对分解
    print(f"\n{'='*90}")
    print(f"  策略对分解 (all topologies)")
    print(f"{'='*90}")
    for sname in [s[0] for s in strategy_sets]:
        srows = [r for r in all_rows if r['strategy'] == sname]
        g1 = [r for r in srows if r['trust_budget'] == 0]
        g5 = [r for r in srows if r['trust_budget'] == 6]
        eta1 = sum(r['eta_global'] for r in g1) / max(1, len(g1))
        eta5 = sum(r['eta_global'] for r in g5) / max(1, len(g5))
        avg_joint = sum(r['joint_enter_rounds'] for r in srows) / max(1, len(srows))
        avg_closed = sum(r['closed_agents'] for r in srows) / max(1, len(srows))
        print(f"  {sname:30s}  η: {eta1:.4f}→{eta5:.4f} (Δ={eta5-eta1:+.4f})  "
              f"joint={avg_joint:.1f}r  closed={avg_closed:.1f}/{N_AGENTS}")


if __name__ == '__main__':
    main()
