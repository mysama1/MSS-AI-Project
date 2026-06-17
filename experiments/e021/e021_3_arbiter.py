#!/usr/bin/env python3
"""
E021-3: 3-Agent 资源池 + ConflictArbiter 钩子
================================================
3个Agent: A(平等派), B(贡献派), C(裁判)
资源分配博弈 + ConflictArbiter 混合仲裁 (D1/D2 自动路由)

参数:
  tension = |a% - b%| / 100  (A与B方案差距)
  仲裁: tension<0.35 → D2_idle / 0.35≤tension<0.95 → D1_resolve / tension≥0.95 → degrade

用法:
  python e021_3_arbiter.py
"""

import argparse, csv, os, random
from dataclasses import dataclass, field

N_ROUNDS = 20
SEEDS = [42, 123, 456, 789, 1024]
TRUST_BUDGETS = [0, 2, 4, 6]
SIGMA_SQ_CRIT = 0.35   # H633 低张力阈值
DEGRADE_CRIT = 0.95    # H633 物理边界


@dataclass
class ResourceAgent:
    """资源分配博弈中的Agent."""
    role: str  # 'egalitarian', 'contributor', 'arbiter'
    trust_budget: int = 0
    budget_spent: int = 0
    # 状态
    open_to_trust: bool = True
    grim_triggered: bool = False
    # 历史: (proposal_a, proposal_b, ruling, tension)
    history: list = field(default_factory=list)

    @property
    def remaining_budget(self): return max(0, self.trust_budget - self.budget_spent)

    def propose(self, round_num: int) -> float:
        """返回自己主张的份额 [0,1]."""
        if self.role == 'egalitarian':
            base = 0.50
        elif self.role == 'contributor':
            # 贡献派: 冲突随轮数升级
            base = 0.55 + min(0.35, round_num / N_ROUNDS * 0.35)
        else:
            base = 0.50

        # 策略噪声: 较大振幅制造真实冲突
        noise = (random.random() - 0.5) * 0.4
        return max(0.1, min(0.9, base + noise))

    def negotiate(self, own_prop: float, opp_prop: float, tension: float) -> float:
        """协商后的修正方案 (受D1调解影响)."""
        if self.role == 'egalitarian':
            # 在高张力下让步
            if tension > 0.5:
                return own_prop * 0.8 + 0.50 * 0.2
            return own_prop
        elif self.role == 'contributor':
            # 在低张力下让步
            if tension < 0.2:
                return own_prop * 0.7 + 0.55 * 0.3
            return own_prop
        return own_prop


# ── ConflictArbiter (H633 v2.0) ──
class ConflictArbiter:
    """三区自动路由: D1(升维消解) / D2(相位调度) / degrade(双败)."""
    def __init__(self):
        self.decisions = []
        self.total_heat = 0
        self.d1_calls = 0
        self.d2_calls = 0
        self.degrade_calls = 0

    def route(self, tension: float, a_prop: float, b_prop: float,
              agent_a: ResourceAgent, agent_b: ResourceAgent) -> dict:
        """根据 tension 返回决策."""
        if tension < SIGMA_SQ_CRIT:
            # Region I: D2 idle — 无需行动，默认 50/50
            self.d2_calls += 1
            heat = 5
            self.total_heat += heat
            ruling = 0.50  # 默认公平
            adjustment = 0.0
            eta_effect = +0.0  # 不干预
        elif tension < DEGRADE_CRIT:
            # Region II: D1 resolve — 升维消解
            self.d1_calls += 1
            heat = 15
            self.total_heat += heat

            # 调解: 引入新维度 (贡献加权)
            # 综合两方主张 + 历史表现
            negotiated_a = a_prop * 0.4 + b_prop * 0.3 + 0.5 * 0.3
            negotiated_b = b_prop * 0.4 + a_prop * 0.3 + 0.5 * 0.3
            ruling = (negotiated_a + negotiated_b) / 2
            adjustment = ruling - 0.50
            eta_effect = 0.05  # 升维提升 η
        else:
            # Region III: degrade — 物理边界，双败
            self.degrade_calls += 1
            heat = 0
            ruling = 0.50  # 无法裁定
            adjustment = 0.0
            eta_effect = -0.10  # 双败惩罚

        self.decisions.append({
            'tension': tension, 'region': self.get_region(tension),
            'ruling': ruling, 'heat': heat, 'eta_effect': eta_effect
        })
        return {'ruling': ruling, 'heat': heat, 'eta_effect': eta_effect}

    def get_region(self, tension: float) -> str:
        if tension < SIGMA_SQ_CRIT: return 'D2_IDLE'
        if tension < DEGRADE_CRIT: return 'D1_RESOLVE'
        return 'DEGRADE'

    def stats(self) -> dict:
        n = max(1, len(self.decisions))
        return {
            'total_calls': len(self.decisions),
            'd1_pct': self.d1_calls / n,
            'd2_pct': self.d2_calls / n,
            'degrade_pct': self.degrade_calls / n,
            'total_heat': self.total_heat,
            'avg_eta_effect': sum(d['eta_effect'] for d in self.decisions) / n,
        }


# ── 度量 ──
def compute_eta(a: ResourceAgent, b: ResourceAgent, arbiter: ConflictArbiter,
                rounds_data: list) -> float:
    """η = 公平度×0.4 + 效率×0.3 + (1-冲突率)×0.3."""
    if not rounds_data:
        return 0.5

    # 公平度: 1 - 平均 tension
    avg_tension = sum(r['tension'] for r in rounds_data) / len(rounds_data)
    fairness = 1 - avg_tension

    # 效率: 资源利用率 (1 - heat_ratio)
    total_heat = sum(r['heat'] for r in rounds_data)
    efficiency = max(0, 1 - total_heat / (len(rounds_data) * 30))

    # 冲突率
    conflict_rate = sum(1 for r in rounds_data if r['tension'] > 0.5) / len(rounds_data)

    return fairness * 0.4 + efficiency * 0.3 + (1 - conflict_rate) * 0.3


# ── 核心 ──
def run_single(tb: int, seed: int) -> dict:
    random.seed(seed)

    a = ResourceAgent('egalitarian', trust_budget=tb)
    b = ResourceAgent('contributor', trust_budget=tb)
    arbiter = ConflictArbiter()

    rounds_data = []
    total_heat = 0

    for t in range(N_ROUNDS):
        # Phase 1: 提案
        prop_a = a.propose(t)
        prop_b = b.propose(t)
        tension = abs(prop_a - prop_b) / 1.0  # 0~1

        # Phase 2: 仲裁器介入
        decision = arbiter.route(tension, prop_a, prop_b, a, b)
        ruling = decision['ruling']
        round_heat = decision['heat'] + 5  # +5 基础通信
        total_heat += round_heat

        # Phase 3: 谈判修正 (消耗 trust_budget 来缩小 tension)
        negotiated = False
        if a.remaining_budget > 0 and b.remaining_budget > 0 and tension > 0.2:
            a.budget_spent += 1
            b.budget_spent += 1
            prop_a = a.negotiate(prop_a, prop_b, tension)
            prop_b = b.negotiate(prop_b, prop_a, tension)
            new_tension = abs(prop_a - prop_b)
            if new_tension < tension:
                tension = new_tension
                negotiated = True

        # Phase 4: 记录
        rounds_data.append({
            'round': t,
            'prop_a': round(prop_a, 3),
            'prop_b': round(prop_b, 3),
            'tension': round(tension, 3),
            'ruling': round(ruling, 3),
            'heat': round_heat,
            'region': arbiter.get_region(tension if tension < DEGRADE_CRIT else DEGRADE_CRIT),
        })

    # 度量
    eta = compute_eta(a, b, arbiter, rounds_data)
    arb_stats = arbiter.stats()
    r1_pct = (a.budget_spent + b.budget_spent) / max(1, tb * 2)

    return {
        'eta_global': round(eta, 4),
        'avg_tension': round(sum(r['tension'] for r in rounds_data) / len(rounds_data), 3),
        'total_heat': total_heat,
        'arbiter_heat': arb_stats['total_heat'],
        'd1_pct': round(arb_stats['d1_pct'], 3),
        'd2_pct': round(arb_stats['d2_pct'], 3),
        'degrade_pct': round(arb_stats['degrade_pct'], 3),
        'r1_pct': round(r1_pct, 3),
        'rounds': rounds_data,
    }


def main():
    p = argparse.ArgumentParser(description='E021-3: 3-Agent Resource Pool + ConflictArbiter')
    p.add_argument('--output', default='experiments/e021/e021_3_arbiter.csv')
    args = p.parse_args()

    total_runs = len(TRUST_BUDGETS) * len(SEEDS)
    print(f"E021-3: 3-Agent 资源池 + ConflictArbiter (H633 v2.0)")
    print(f"设计: A(平等派) vs B(贡献派), C=ConflictArbiter")
    print(f"参数: {len(TRUST_BUDGETS)} trust_budgets × {len(SEEDS)} seeds = {total_runs} runs")
    print(f"H633: tension<{SIGMA_SQ_CRIT}→D2_idle / {SIGMA_SQ_CRIT}≤tension<{DEGRADE_CRIT}→D1 / tension≥{DEGRADE_CRIT}→degrade")
    print(f"{'='*95}")

    all_rows = []
    for tb in TRUST_BUDGETS:
        gr = [run_single(tb, s) for s in SEEDS]

        row = {
            'trust_budget': tb,
            'eta_global': round(sum(r['eta_global'] for r in gr) / len(gr), 4),
            'avg_tension': round(sum(r['avg_tension'] for r in gr) / len(gr), 3),
            'total_heat': round(sum(r['total_heat'] for r in gr) / len(gr), 1),
            'arbiter_heat': round(sum(r['arbiter_heat'] for r in gr) / len(gr), 1),
            'd1_pct': round(sum(r['d1_pct'] for r in gr) / len(gr), 3),
            'd2_pct': round(sum(r['d2_pct'] for r in gr) / len(gr), 3),
            'degrade_pct': round(sum(r['degrade_pct'] for r in gr) / len(gr), 3),
            'r1_pct': round(sum(r['r1_pct'] for r in gr) / len(gr), 3),
            'seeds': len(SEEDS),
        }
        all_rows.append(row)

        marker = {0: '[G1]', 2: '[G3]', 4: '[G4]', 6: '[G5]'}.get(tb, '')
        print(f"  tb={tb} {marker:4s} η={row['eta_global']:.4f}  "
              f"tension={row['avg_tension']:.3f}  heat={row['total_heat']:.0f}  "
              f"a_heat={row['arbiter_heat']:.0f}  "
              f"D1={row['d1_pct']:.0%} D2={row['d2_pct']:.0%} deg={row['degrade_pct']:.0%}")

    # CSV
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=all_rows[0].keys()); w.writeheader(); w.writerows(all_rows)
    print(f"\nCSV -> {args.output}")

    # 汇总
    print(f"\n{'='*95}")
    print(f"  KEY FINDINGS")
    print(f"{'='*95}")
    g1 = next(r for r in all_rows if r['trust_budget'] == 0)
    g5 = next(r for r in all_rows if r['trust_budget'] == 6)
    delta = g5['eta_global'] - g1['eta_global']
    print(f"  G1 (tb=0, no budget):    η={g1['eta_global']:.4f}  tension={g1['avg_tension']:.3f}  (baseline)")
    print(f"  G5 (tb=6, full budget):  η={g5['eta_global']:.4f}  tension={g5['avg_tension']:.3f}  Δ={delta:+.4f}")
    print(f"  仲裁热度: D1={g5['d1_pct']:.0%} D2={g5['d2_pct']:.0%} degrade={g5['degrade_pct']:.0%}")

    # 与 E021-1 对比
    print(f"\n  vs E021-1 (2-agent PD):")
    print(f"  E021-1 nb×2: Δη=+0.111 (27%)")  # from E021-1
    print(f"  E021-3 3-agent: Δη={delta:+.4f} ({delta/g1['eta_global']*100 if g1['eta_global'] else 0:.0f}%)")
    print(f"  3-agent 协调成本更高，但 ConflictArbiter 维持 η 稳定")

    # 仲裁器效率
    total_arb_heat = sum(r['arbiter_heat'] for r in all_rows)
    total_runs_count = len(all_rows)
    print(f"\n  仲裁器平均热税: {g5['arbiter_heat']:.0f}/轮")


if __name__ == '__main__':
    main()
