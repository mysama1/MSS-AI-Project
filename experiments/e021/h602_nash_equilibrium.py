#!/usr/bin/env python3
"""
H602: Nash均衡形式化 + E021实证
===================================
前置: H601 骨架 (搜索退化的存在性陈述)
目标: 测量 trust_budget 在 Nash 阱中对 η 的因果效应，验证升维可打破均衡

核心假设 (来自H601):
  H₀: trust_budget 对 η_global 无因果效应 (Δη=0)
  H₁: trust_budget 对 η_global 有正向因果效应 (Δη>0)
  
  子假设:
  H₂: 效应只存在于 nash_breaker 对 (破阱策略)
  H₃: nash_breaker-cautious 单向升维产生负效应 (热税净损失)
  H₄: 效应 magnitude 随 tb 增长而递减 (边际递减, A3证实)

设计:
  4策略对 × 5 trust_budget 组 × 20 seeds = 400 runs
  每个 run: 20轮, 10%噪声, H634 joint_enter gate

用法:
  python h602_nash_equilibrium.py
  python h602_nash_equilibrium.py --pairs nash_breaker,nash_breaker --seeds 50
"""

import argparse, csv, os, random, statistics
from dataclasses import dataclass, field
from itertools import product
import json

# ── 全局参数 ──
N_ROUNDS = 20
NOISE_PROB = 0.10
SEEDS = list(range(42, 42 + 20))  # 20 seeds for statistical power
TRUST_BUDGETS = [0, 2, 4, 6, 8]   # 5 groups (G1-G5)
STRATEGY_PAIRS = [
    ('nash_breaker', 'nash_breaker'),
    ('nash_breaker', 'cautious'),
    ('adaptive', 'adaptive'),
    ('aggressive', 'cautious'),
]

# ── Agent (E021-1 v2.1 H634) ──
@dataclass
class Agent:
    name: str = "A"
    strategy: str = "nash_breaker"
    trust_budget: int = 0
    open_to_trust: bool = True
    grim_triggered: bool = False
    unilateral_invite_received: int = 0
    budget_spent: int = 0
    history: list = field(default_factory=list)
    opp_history: list = field(default_factory=list)

    @property
    def remaining_budget(self): return max(0, self.trust_budget - self.budget_spent)

    def choose_action(self, opp: 'Agent') -> str:
        os = self.opp_history
        opp_closed = not opp.open_to_trust

        if self.strategy == 'nash_breaker':
            return self._nash_breaker(os, opp_closed)
        elif self.strategy == 'cautious':
            return self._cautious(os, opp_closed)
        elif self.strategy == 'adaptive':
            return self._adaptive(os, opp_closed)
        elif self.strategy == 'aggressive':
            return self._aggressive(os)
        return 'C'

    def _nash_breaker(self, os, opp_closed):
        if 'D' in os:
            my_recent = self.history[-2:] if len(self.history) >= 2 else []
            opp_recent = os[-2:] if len(os) >= 2 else []
            in_nash = (len(my_recent) >= 2 and all(a == 'D' for a in my_recent) and
                       len(opp_recent) >= 2 and all(a == 'D' for a in opp_recent))
            if in_nash and self.remaining_budget > 0 and not opp_closed:
                return 'TRUST_INVITE'
            return 'D'
        return 'C'

    def _cautious(self, os, opp_closed):
        if self.grim_triggered:
            return 'D'
        if os and os[-1] == 'D':
            return 'D'
        recent = [a for a in os[-3:] if a in ('C', 'TRUST_INVITE')] if len(os) >= 3 else []
        if len(recent) == 3 and self.remaining_budget > 0 and not opp_closed:
            return 'TRUST_INVITE'
        return 'C'

    def _adaptive(self, os, opp_closed):
        if self.grim_triggered:
            return 'D'
        if os and os[-1] == 'D':
            return 'D'
        cr = sum(1 for a in os if a in ('C', 'TRUST_INVITE')) / max(1, len(os))
        if cr > 0.6 and len(os) >= 3 and self.remaining_budget > 0 and not opp_closed:
            return 'TRUST_INVITE'
        return 'C'

    def _aggressive(self, os):
        if os and os[-1] in ('C', 'TRUST_INVITE'):
            return 'D'
        return 'C'

    # H634 v2.1c: Nash豁免 + 双触发
    def mark_unilateral_invite(self, was_in_nash: bool):
        if was_in_nash:
            return  # Nash阱内噪声豁免
        self.unilateral_invite_received += 1
        if self.unilateral_invite_received >= 2:
            self.open_to_trust = False
            self.grim_triggered = True


# ── 度量 ──
def compute_eta(a1: Agent, a2: Agent, rounds_data: list) -> dict:
    """返回 η_global 及其三个分量."""
    trust_density = (a1.open_to_trust + a2.open_to_trust) / 2.0

    pure = [r for r in rounds_data if r.get('type') == 'action']
    if not pure:
        return {'eta_global': 0.5, 'trust_density': trust_density,
                'elevation_success': 0.0, 'exploit_rate': 0.0}

    # 升维成功率
    joint = sum(1 for r in pure if r['actions'].count('TRUST_INVITE') >= 2)
    total_inv = sum(r['actions'].count('TRUST_INVITE') for r in pure)
    elev_success = joint / max(1, total_inv / 2)

    # 剥削率
    exploit = 0
    for r in pure:
        a, b = r['actions']
        if a == 'D' and b in ('C', 'TRUST_INVITE'): exploit += 1
        if b == 'D' and a in ('C', 'TRUST_INVITE'): exploit += 1
    exploit_rate = exploit / max(1, len(pure) * 2)

    eta = trust_density * 0.5 + elev_success * 0.3 + (1 - exploit_rate) * 0.2
    return {'eta_global': eta, 'trust_density': trust_density,
            'elevation_success': elev_success, 'exploit_rate': exploit_rate}


# ── 单次运行 ──
def run_single(tb: int, seed: int, pair: tuple) -> dict:
    random.seed(seed)
    a1 = Agent(name="A", strategy=pair[0], trust_budget=tb)
    a2 = Agent(name="B", strategy=pair[1], trust_budget=tb)

    rounds_data = []
    total_heat = 0
    nash_lock_rounds = 0
    unilateral_events = 0
    joint_invites = 0

    for t in range(N_ROUNDS):
        a1_act = a1.choose_action(a2)
        a2_act = a2.choose_action(a1)

        # 噪声
        if random.random() < NOISE_PROB:
            a1_act = 'D' if a1_act != 'D' else 'C'
        if random.random() < NOISE_PROB:
            a2_act = 'D' if a2_act != 'D' else 'C'

        # 热税
        round_heat = 2  # base comms
        if a1_act == 'TRUST_INVITE':
            round_heat += 2
            a1.budget_spent += 2
        if a2_act == 'TRUST_INVITE':
            round_heat += 2
            a2.budget_spent += 2
        total_heat += round_heat

        # H634: 单边邀请检测
        if a1_act == 'TRUST_INVITE' and a2_act != 'TRUST_INVITE':
            unilateral_events += 1
            a2_nash = len(a2.history) >= 2 and all(h == 'D' for h in a2.history[-2:])
            a2.mark_unilateral_invite(a2_nash)
        elif a2_act == 'TRUST_INVITE' and a1_act != 'TRUST_INVITE':
            unilateral_events += 1
            a1_nash = len(a1.history) >= 2 and all(h == 'D' for h in a1.history[-2:])
            a1.mark_unilateral_invite(a1_nash)

        if a1_act == 'TRUST_INVITE' and a2_act == 'TRUST_INVITE':
            joint_invites += 1

        if a1_act == 'D' and a2_act == 'D':
            nash_lock_rounds += 1

        a1.history.append(a1_act)
        a2.history.append(a2_act)
        a1.opp_history.append(a2_act)
        a2.opp_history.append(a1_act)
        rounds_data.append({'type': 'action', 'round': t, 'actions': [a1_act, a2_act]})

    eta = compute_eta(a1, a2, rounds_data)
    return {
        **eta,
        'nash_lock_rate': nash_lock_rounds / N_ROUNDS,
        'unilateral_events': unilateral_events,
        'joint_invites': joint_invites,
        'total_heat': total_heat,
        'budget_used': (a1.budget_spent + a2.budget_spent) / 2,
        'closed_end': sum(1 for a in [a1, a2] if not a.open_to_trust),
    }


# ── 效应量计算 ──
def cohens_d(g1, g5):
    """Cohen's d: G5 vs G1 的标准化效应量."""
    pooled_std = statistics.stdev(g1 + g5) if len(g1 + g5) > 1 else 1.0
    if pooled_std == 0:
        return 0.0
    return (statistics.mean(g5) - statistics.mean(g1)) / pooled_std


def bootstrap_ci(values, n_bootstrap=10000, alpha=0.05):
    """Bootstrap 95% CI for mean."""
    means = []
    for _ in range(n_bootstrap):
        sample = random.choices(values, k=len(values))
        means.append(statistics.mean(sample))
    means.sort()
    lo = means[int(alpha / 2 * n_bootstrap)]
    hi = means[int((1 - alpha / 2) * n_bootstrap)]
    return lo, hi


# ── 主入口 ──
def main():
    p = argparse.ArgumentParser(description='H602: Nash均衡形式化 + E021实证')
    p.add_argument('--pairs', type=str, default='all', help='策略对 (e.g. nash_breaker,nash_breaker or all)')
    p.add_argument('--seeds', type=int, default=20, help='种子数')
    p.add_argument('--output', default='experiments/e021/h602_nash_equilibrium.csv')
    p.add_argument('--report', default='experiments/e021/h602_effect_size_report.json')
    args = p.parse_args()

    if args.pairs == 'all':
        pairs = STRATEGY_PAIRS
    else:
        s1, s2 = args.pairs.split(',')
        pairs = [(s1, s2)]

    seeds = SEEDS[:args.seeds]
    total = len(pairs) * len(TRUST_BUDGETS) * len(seeds)
    print(f"H602: Nash均衡形式化 — 效应量验证")
    print(f"设计: {len(pairs)}对 × {len(TRUST_BUDGETS)}组 × {len(seeds)}seeds = {total} runs")
    print(f"H634: joint_enter + Nash豁免 + 双触发门禁")
    print(f"{'='*95}")

    all_rows = []
    effect_sizes = {}

    for pair in pairs:
        pair_name = f"{pair[0]}×{pair[1]}"
        print(f"\n── {pair_name} ──")
        pair_etas = {}  # tb -> list of eta values

        for tb in TRUST_BUDGETS:
            results = [run_single(tb, s, pair) for s in seeds]

            eta_vals = [r['eta_global'] for r in results]
            pair_etas[tb] = eta_vals

            row = {
                'pair': pair_name,
                'trust_budget': tb,
                'eta_global_avg': round(statistics.mean(eta_vals), 4),
                'eta_global_std': round(statistics.stdev(eta_vals) if len(eta_vals) > 1 else 0, 4),
                'eta_global_ci95_lo': round(bootstrap_ci(eta_vals)[0], 4),
                'eta_global_ci95_hi': round(bootstrap_ci(eta_vals)[1], 4),
                'nash_lock_rate': round(statistics.mean([r['nash_lock_rate'] for r in results]), 3),
                'joint_invites_avg': round(statistics.mean([r['joint_invites'] for r in results]), 1),
                'unilateral_avg': round(statistics.mean([r['unilateral_events'] for r in results]), 1),
                'closed_end_avg': round(statistics.mean([r['closed_end'] for r in results]), 1),
                'total_heat_avg': round(statistics.mean([r['total_heat'] for r in results]), 1),
                'elevation_success': round(statistics.mean([r['elevation_success'] for r in results]), 3),
                'n_seeds': len(seeds),
            }
            all_rows.append(row)

            # 效应量 (G5 vs G1 for tb=8 vs 0)
            if tb == 0:
                g1_vals = eta_vals
            elif tb == 8:
                d = cohens_d(pair_etas[0], eta_vals)
                ci = bootstrap_ci(eta_vals)

                marker = 'G1→G5'
                print(f"  {marker:6s} tb={tb}  η={row['eta_global_avg']:.4f}±{row['eta_global_std']:.3f}  "
                      f"d={d:+.3f}  95%CI=[{ci[0]:.3f},{ci[1]:.3f}]  "
                      f"nlk={row['nash_lock_rate']:.3f}  ji={row['joint_invites_avg']:.0f}")
            else:
                marker = {2: 'G3', 4: 'G4', 6: 'G5'}.get(tb, f'G{tb}')
                print(f"  {marker:6s} tb={tb}  η={row['eta_global_avg']:.4f}±{row['eta_global_std']:.3f}  "
                      f"nlk={row['nash_lock_rate']:.3f}  ji={row['joint_invites_avg']:.0f}")

        # 计算效应量
        eta_g1 = pair_etas[0]
        eta_g5 = pair_etas[8]
        d = cohens_d(eta_g1, eta_g5)
        delta_eta = statistics.mean(eta_g5) - statistics.mean(eta_g1)
        ci = bootstrap_ci(eta_g5)

        effect_sizes[pair_name] = {
            'cohens_d': round(d, 3),
            'delta_eta': round(delta_eta, 4),
            'delta_pct': round(delta_eta / max(0.001, statistics.mean(eta_g1)) * 100, 1),
            'ci95_lo': round(ci[0], 4),
            'ci95_hi': round(ci[1], 4),
            'significant': abs(d) > 0.5 and ci[0] * ci[1] > 0 if ci[0] > 0 == ci[1] > 0 else abs(d) > 0.5,
        }

    # ── 汇总报告 ──
    print(f"\n{'='*95}")
    print(f"  H602 效应量汇总 (Cohen's d: G5 vs G1, tb=8 vs 0)")
    print(f"{'='*95}")

    h1_supported = True
    for pair_name, es in effect_sizes.items():
        sig = '✅' if es['significant'] else '⚠️' if abs(es['cohens_d']) > 0.3 else '❌'
        print(f"  {pair_name:28s} Δη={es['delta_eta']:+.4f} ({es['delta_pct']:+.1f}%)  "
              f"d={es['cohens_d']:+.3f}  95%CI=[{es['ci95_lo']:.3f},{es['ci95_hi']:.3f}]  {sig}")
        if es['delta_eta'] <= 0 and 'nash_breaker×nash_breaker' in pair_name:
            h1_supported = False

    print(f"\n  H₁ (正向因果效应): {'✅ 支持' if h1_supported else '❌ 不支持'}")
    print(f"  H₂ (仅破阱策略有效): 分析中")
    print(f"  H₃ (单向负效应): 分析中")
    print(f"  H₄ (边际递减): 分析中")

    # CSV
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=all_rows[0].keys()); w.writeheader(); w.writerows(all_rows)
    print(f"\nCSV → {args.output}")

    # JSON report
    report = {
        'hypothesis': 'H602: Nash均衡形式化 + 升维效应量',
        'design': {
            'n_pairs': len(pairs),
            'n_budgets': len(TRUST_BUDGETS),
            'n_seeds': len(seeds),
            'n_total_runs': total,
            'n_rounds': N_ROUNDS,
            'noise_prob': NOISE_PROB,
            'h634_version': 'v2.1c (Nash豁免 + 双触发)',
        },
        'effect_sizes': effect_sizes,
        'interpretation': {
            'cohens_d > 0.8': 'large effect → strong causal',
            'cohens_d 0.5-0.8': 'medium effect → moderate causal',
            'cohens_d 0.2-0.5': 'small effect → weak causal',
            'cohens_d < 0.2': 'negligible → no causal',
        }
    }
    with open(args.report, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Report → {args.report}")


if __name__ == '__main__':
    main()
