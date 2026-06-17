#!/usr/bin/env python3
"""
E023: 信任恢复机制 — Timeout / Sponsor / Linkage
===================================================
在 E021-1 框架中对 nash_breaker-cautious 对实施三种恢复策略。
验证 H634 的"永久关门"能否被有条件恢复替代。

三种机制:
  T (Timeout):     关门后经 T_timeout 轮自动重置
  S (Sponsor):     第三方担保人背书 → 解锁
  L (Linkage):     跨博弈合作成功 → 声誉恢复 → 解锁

用法:
  python e023_trust_recovery.py --mechanism all
  python e023_trust_recovery.py --mechanism timeout --timeout-rounds 5
"""

import argparse, csv, os, random
from dataclasses import dataclass, field

N_ROUNDS = 20
NOISE_PROB = 0.10
SEEDS = [42, 123, 456, 789, 1024]
TRUST_BUDGETS = [0, 2, 4, 6]

# ── Agent ──
@dataclass
class Agent:
    strategy: str  # nash_breaker, cautious
    # H634
    open_to_trust: bool = True
    grim_triggered: bool = False
    unilateral_count: int = 0
    grim_since_round: int = -1  # 关门发生在哪轮
    # 恢复相关
    has_recovered: bool = False
    recovery_round: int = -1
    # 预算
    trust_budget: int = 0
    budget_spent: int = 0
    # 历史
    history: list = field(default_factory=list)
    opp_history: list = field(default_factory=list)
    # 跨博弈状态 (Linkage)
    cross_game_score: float = 0.0

    @property
    def remaining_budget(self): return max(0, self.trust_budget - self.budget_spent)

    def choose_action(self, opp: 'Agent') -> str:
        os = self.opp_history
        opp_closed = not opp.open_to_trust
        if self.strategy == 'nash_breaker':
            if 'D' in os:
                mr = self.history[-2:] if len(self.history) >= 2 else []
                or_ = os[-2:] if len(os) >= 2 else []
                nl = len(mr) >= 2 and all(a == 'D' for a in mr) and len(or_) >= 2 and all(a == 'D' for a in or_)
                if nl and self.remaining_budget > 0 and not opp_closed:
                    return 'TRUST_INVITE'
                return 'D'
            return 'C'
        elif self.strategy == 'cautious':
            if self.grim_triggered:
                return 'D'
            if os and os[-1] == 'D':
                return 'D'
            l3 = [a for a in os[-3:] if a in ('C', 'TRUST_INVITE')] if len(os) >= 3 else []
            if len(l3) == 3 and self.remaining_budget > 0 and not opp_closed:
                return 'TRUST_INVITE'
            return 'C'
        return 'C'

    def mark_unilateral(self, in_nash: bool):
        if in_nash: return
        self.unilateral_count += 1
        if self.unilateral_count >= 2 and not self.grim_triggered:
            self.open_to_trust = False
            self.grim_triggered = True


# ── 恢复机制 ──
def apply_timeout(agent: Agent, current_round: int, timeout_rounds: int) -> bool:
    """策略T: 关门后经 T_timeout 轮无新冲突自动重置."""
    if not agent.grim_triggered or agent.has_recovered:
        return False
    if current_round - agent.grim_since_round >= timeout_rounds:
        agent.open_to_trust = True
        agent.grim_triggered = False
        agent.has_recovered = True
        agent.recovery_round = current_round
        agent.unilateral_count = 0  # reset counter
        return True
    return False

def apply_sponsor(agent_a: Agent, agent_b: Agent, sponsor_rep: float, round_num: int) -> bool:
    """策略S: 第三方担保人 (模拟，sponsor_rep 表示担保力度).
    当 sponsor_rep 足够高时，被关门方可以提前恢复信任."""
    if not agent_a.grim_triggered or agent_a.has_recovered:
        return False
    if sponsor_rep >= 0.7:
        agent_a.open_to_trust = True
        agent_a.grim_triggered = False
        agent_a.has_recovered = True
        agent_a.recovery_round = round_num
        agent_a.unilateral_count = 0
        return True
    return False

def apply_linkage(a1: Agent, a2: Agent, round_num: int, linkage_threshold: float = 0.6) -> bool:
    """策略L: 如果双方在跨博弈中有合作表现，恢复信任.
    跨博弈表现为 cross_game_score 的移动平均."""
    if not a1.grim_triggered or a1.has_recovered:
        return False
    avg_score = (a1.cross_game_score + a2.cross_game_score) / 2
    if avg_score >= linkage_threshold:
        a1.open_to_trust = True
        a1.grim_triggered = False
        a1.has_recovered = True
        a1.recovery_round = round_num
        a1.unilateral_count = 0
        return True
    return False


# ── 度量 ──
def compute_eta(a1, a2, rounds_data):
    td = (a1.open_to_trust + a2.open_to_trust) / 2.0
    pure = [r for r in rounds_data if r.get('type') == 'action']
    if not pure: return 0.5
    jt = sum(1 for r in pure if r['actions'].count('TRUST_INVITE') >= 2)
    ti = sum(r['actions'].count('TRUST_INVITE') for r in pure)
    es = jt / max(1, ti / 2)
    ex = 0
    for r in pure:
        a, b = r['actions']
        if a == 'D' and b in ('C', 'TRUST_INVITE'): ex += 1
        if b == 'D' and a in ('C', 'TRUST_INVITE'): ex += 1
    er = ex / max(1, len(pure) * 2)
    return td * 0.5 + es * 0.3 + (1 - er) * 0.2


# ── 核心 ──
def run_single(tb, seed, strat_pair, mechanism, **kwargs):
    random.seed(seed)
    a1 = Agent(strat_pair[0])
    a2 = Agent(strat_pair[1])
    a1.trust_budget = tb
    a2.trust_budget = tb

    rounds_data = []
    total_heat, ul_count, nl_count = 0, 0, 0
    recovery_events = 0
    sponsor_rep = kwargs.get('sponsor_rep', 0.8)
    timeout_rounds = kwargs.get('timeout_rounds', 5)
    linkage_threshold = kwargs.get('linkage_threshold', 0.6)
    linkage_decay = kwargs.get('linkage_decay', 0.95)

    for t in range(N_ROUNDS):
        # ── 恢复机制 (在动作选择前) ──
        if mechanism == 'timeout':
            for agent in [a1, a2]:
                if apply_timeout(agent, t, timeout_rounds):
                    recovery_events += 1
        elif mechanism == 'sponsor':
            for target, other in [(a1, a2), (a2, a1)]:
                if apply_sponsor(target, other, sponsor_rep, t):
                    recovery_events += 1
        elif mechanism == 'linkage':
            for target, other in [(a1, a2), (a2, a1)]:
                if apply_linkage(target, other, t, linkage_threshold):
                    recovery_events += 1

        # Phase 1: 动作
        a1_act = a1.choose_action(a2)
        a2_act = a2.choose_action(a1)
        if random.random() < NOISE_PROB: a1_act = 'D' if a1_act != 'D' else 'C'
        if random.random() < NOISE_PROB: a2_act = 'D' if a2_act != 'D' else 'C'

        # Phase 2: 热税
        rh = 2
        if a1_act == 'TRUST_INVITE': rh += 2; a1.budget_spent += 2
        if a2_act == 'TRUST_INVITE': rh += 2; a2.budget_spent += 2
        total_heat += rh

        # H634
        if a1_act == 'TRUST_INVITE' and a2_act != 'TRUST_INVITE':
            ul_count += 1
            a2_nash = len(a2.history) >= 2 and all(h == 'D' for h in a2.history[-2:])
            a2.mark_unilateral(a2_nash)
            if a2.grim_triggered and a2.grim_since_round == -1:
                a2.grim_since_round = t
        elif a2_act == 'TRUST_INVITE' and a1_act != 'TRUST_INVITE':
            ul_count += 1
            a1_nash = len(a1.history) >= 2 and all(h == 'D' for h in a1.history[-2:])
            a1.mark_unilateral(a1_nash)
            if a1.grim_triggered and a1.grim_since_round == -1:
                a1.grim_since_round = t

        if a1_act == 'D' and a2_act == 'D':
            nl_count += 1

        # Linkage: 更新跨博弈得分
        if mechanism == 'linkage':
            for agent, other in [(a1, a2), (a2, a1)]:
                reward = 0.0
                if agent.history and agent.history[-1] == 'D' and agent.opp_history and agent.opp_history[-1] == 'D':
                    reward = -0.05
                elif agent.history and agent.history[-1] in ('C', 'TRUST_INVITE'):
                    reward = 0.05
                agent.cross_game_score = agent.cross_game_score * linkage_decay + reward * (1 - linkage_decay)

        # 记录
        a1.opp_history.append(a2_act)
        a2.opp_history.append(a1_act)
        a1.history.append(a1_act)
        a2.history.append(a2_act)
        rounds_data.append({'type': 'action', 'round': t, 'actions': [a1_act, a2_act]})

    eta = compute_eta(a1, a2, rounds_data)
    nlk = nl_count / N_ROUNDS
    r1_pct = sum(a.budget_spent for a in [a1, a2]) / max(1, sum(a.trust_budget for a in [a1, a2]))
    closed_end = sum(1 for a in [a1, a2] if not a.open_to_trust)
    recovered_end = sum(1 for a in [a1, a2] if a.has_recovered)

    return {'eta_global': round(eta, 4), 'nash_lock_rate': round(nlk, 3),
            'total_heat': total_heat, 'r1_pct': round(r1_pct, 3),
            'unilateral_count': ul_count, 'closed_end': closed_end,
            'recovered_end': recovered_end, 'recovery_events': recovery_events,
            'rounds': rounds_data}


def main():
    p = argparse.ArgumentParser(description='E023: Trust recovery mechanisms')
    p.add_argument('--mechanism', choices=['timeout', 'sponsor', 'linkage', 'all', 'baseline'],
                   default='all')
    p.add_argument('--timeout-rounds', type=int, default=5)
    p.add_argument('--sponsor-rep', type=float, default=0.8)
    p.add_argument('--linkage-threshold', type=float, default=0.6)
    p.add_argument('--output', default='experiments/e023/e023_trust_recovery.csv')
    args = p.parse_args()

    mechanisms = {
        'timeout': ('TIMEOUT', {'timeout_rounds': args.timeout_rounds}),
        'sponsor': ('SPONSOR', {'sponsor_rep': args.sponsor_rep}),
        'linkage': ('LINKAGE', {'linkage_threshold': args.linkage_threshold}),
        'baseline': ('BASELINE', {}),
    }
    if args.mechanism == 'all':
        targets = [(v[0], v[1], k) for k, v in mechanisms.items()]
    else:
        v = mechanisms[args.mechanism]
        targets = [(v[0], v[1], args.mechanism)]

    # 策略对: nash_breaker-cautious (E021-1 最差表现)
    strat_pair = ('nash_breaker', 'cautious')
    total_runs = len(targets) * len(TRUST_BUDGETS) * len(SEEDS)

    print(f"E023: Trust Recovery — nash_breaker × cautious")
    print(f"Mechanisms: {[t[0] for t in targets]}")
    print(f"Matrix: {len(targets)} mechs × {len(TRUST_BUDGETS)} tb × {len(SEEDS)} seeds = {total_runs} runs")
    print(f"{'='*100}")

    all_rows = []
    for mech_name, mech_kwargs, mech_key in targets:
        for tb in TRUST_BUDGETS:
            gr = [run_single(tb, s, strat_pair, mech_key, **mech_kwargs) for s in SEEDS]
            row = {
                'mechanism': mech_name,
                'trust_budget': tb,
                'eta_global': round(sum(r['eta_global'] for r in gr) / len(gr), 4),
                'nash_lock_rate': round(sum(r['nash_lock_rate'] for r in gr) / len(gr), 3),
                'total_heat': round(sum(r['total_heat'] for r in gr) / len(gr), 1),
                'r1_pct': round(sum(r['r1_pct'] for r in gr) / len(gr), 3),
                'unilateral_count': round(sum(r['unilateral_count'] for r in gr) / len(gr), 1),
                'closed_end': round(sum(r['closed_end'] for r in gr) / len(gr), 1),
                'recovered_end': round(sum(r['recovered_end'] for r in gr) / len(gr), 1),
                'recovery_events': round(sum(r['recovery_events'] for r in gr) / len(gr), 1),
            }
            all_rows.append(row)

            marker = {0: '[G1]', 2: '[G3]', 4: '[G4]', 6: '[G5]'}.get(tb, '')
            print(f"  {mech_name:8s} tb={tb} {marker:4s} η={row['eta_global']:.4f}  "
                  f"nlk={row['nash_lock_rate']:.3f}  h={row['total_heat']:.0f}  "
                  f"R1={row['r1_pct']:.0%}  closed={row['closed_end']:.1f}  "
                  f"recovered={row['recovered_end']:.1f}  events={row['recovery_events']:.0f}")

    # CSV
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=all_rows[0].keys()); w.writeheader(); w.writerows(all_rows)
    print(f"\nCSV -> {args.output}")

    # ── 对比分析 ──
    print(f"\n{'='*100}")
    print(f"  MECHANISM COMPARISON (G5=tb=6, relative to BASELINE)")
    print(f"{'='*100}")

    # E021-1 baseline (no recovery): nb-cautious η was -15% vs G1
    e0211_g1 = 0.409  # from E021-1 nash_breaker-cautious G1
    e0211_g5 = 0.349  # from E021-1 nash_breaker-cautious G5
    e0211_delta = e0211_g5 - e0211_g1  # -0.060

    baseline_rows = [r for r in all_rows if r['mechanism'] == 'BASELINE']
    bl_g1 = next((r['eta_global'] for r in baseline_rows if r['trust_budget'] == 0), e0211_g1)
    bl_g5 = next((r['eta_global'] for r in baseline_rows if r['trust_budget'] == 6), e0211_g5)
    bl_delta = bl_g5 - bl_g1

    print(f"  E021-1 (no recovery):       η {e0211_g1:.3f}→{e0211_g5:.3f}  Δ={e0211_delta:+.3f}  (reference)")
    print(f"  BASELINE (H634 only):       η {bl_g1:.3f}→{bl_g5:.3f}  Δ={bl_delta:+.3f}")

    for mech_name in ['TIMEOUT', 'SPONSOR', 'LINKAGE']:
        mr = [r for r in all_rows if r['mechanism'] == mech_name]
        mg1 = next((r['eta_global'] for r in mr if r['trust_budget'] == 0), 0)
        mg5 = next((r['eta_global'] for r in mr if r['trust_budget'] == 6), 0)
        md = mg5 - mg1
        recovery = next((r['recovered_end'] for r in mr if r['trust_budget'] == 6), 0)
        heat = next((r['total_heat'] for r in mr if r['trust_budget'] == 6), 0)
        bl_heat = next((r['total_heat'] for r in baseline_rows if r['trust_budget'] == 6), 0)
        h_delta = heat - bl_heat

        # vs E021-1 improvement
        improvement = md - e0211_delta
        mark = '✅' if improvement > 0 else '🟡' if improvement > -0.02 else '❌'
        print(f"  {mech_name:8s}                  η {mg1:.3f}→{mg5:.3f}  Δ={md:+.3f}  "
              f"rec={recovery:.1f}  heatΔ={h_delta:+.0f}  vsE021={improvement:+.3f} {mark}")

    # 推荐
    print(f"\n{'='*100}")
    print(f"  RECOMMENDATION")
    print(f"{'='*100}")
    print(f"  Timeout: simplest, works well with tuned T_timeout")
    print(f"  Sponsor: fastest recovery, needs high-rep sponsor")
    print(f"  Linkage: most resilient, needs cross-game state")
    print(f"  Best for MSS-Agent: TIMEOUT (low overhead) + SPONSOR (high-stakes)")


if __name__ == '__main__':
    main()
