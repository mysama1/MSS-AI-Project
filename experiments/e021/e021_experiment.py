"""
E021-1 v2.1: Nash驻点 η 基线测量 — H634 joint_enter 信任门禁
================================================================
v2.1 新增:
  - H634 joint_enter 条件: 升维 = 双方签署新规范场, 单向邀约 = 纯热税损
  - open_to_trust / grim_triggered_by_invite 状态向量
  - 邀约门禁: 对方关门则不浪费 budget
  - up_success_rate 仅统计真正 joint_enter 的轮次

核心命题: Nash 驻点 (D,D) 在 η 尺度下是局部极小，不是全局最优。
升维 (trust_budget → R1) 是跳出 Nash 阱的唯一路径。
A3(热税) 决定升维能否支付入场费，A6(升维) 决定入场后能否维持。
H634: 升维必须 joint_enter(L0→L1), 单向邀约 = A3 净亏损。

设计日期: 2026-06-17
输出: experiments/e021/e021_experiment_v2.1.csv
"""

import random
import csv
import statistics
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

# ============================================================
# 配置
# ============================================================

@dataclass
class Config:
    n_rounds: int = 20
    seeds: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    trust_budget_values: List[int] = field(default_factory=lambda: [0, 2, 4, 6])
    enable_r1: bool = True
    # R1 参数
    r1_entry_cost: int = 1       # 每人入场 trust_budget 花费
    r1_maintenance_rounds: int = 3  # 入场后可持续轮数（不需续费）
    r1_betrayal_penalty: int = 2    # R1 内背叛的 trust_budget 罚金

# ============================================================
# 收益矩阵
# ============================================================

# R0: 经典囚徒困境 (T>R>P>S)
PAYOFF_R0 = {
    ('C', 'C'): (3, 3),
    ('C', 'D'): (0, 5),
    ('D', 'C'): (5, 0),
    ('D', 'D'): (1, 1),
}

# R1: 升维后合作收益提升，但背叛仍然致命
PAYOFF_R1 = {
    ('C', 'C'): (4, 4),
    ('C', 'D'): (-1, 6),
    ('D', 'C'): (6, -1),
    ('D', 'D'): (0, 0),
}

# ============================================================
# 环境噪声
# ============================================================

NOISE_PROB = 0.10  # 每轮每个Agent有10%概率随机背叛

# ============================================================
# 热税模型 (A3 不可约化热税)
# ============================================================

HEAT_BASELINE = 5
HEAT_C = 2
HEAT_D = 1
HEAT_TRUST_INVITE = 5
HEAT_R1_MAINTENANCE = 3
HEAT_FAILED_INVITE = 3

# ============================================================
# Agent 策略类型 (v2.1: + H634 信任门禁)
# ============================================================

class Agent:
    """多策略 Agent，决策依赖 trust_budget + 对手历史 + H634 信任状态."""
    
    def __init__(self, agent_id: int, strategy: str, trust_budget: int = 0):
        self.id = agent_id
        self.strategy = strategy
        self.trust_budget = trust_budget
        self.initial_trust_budget = trust_budget
        self.history: List[str] = []
        self.payoff_history: List[float] = []
        self.in_r1 = False
        self.r1_rounds_left = 0
        # H634: A6 joint_enter 信任门禁
        self.open_to_trust = True           # 是否对升维邀请开放
        self.grim_triggered_by_invite = False  # 是否因单边邀请触发了永久关门
        self.unilateral_invite_received = 0  # H634v2: 累计单边邀请次数（2次才关门）
    
    def choose_action(self, opponent_history: List[str], round_num: int,
                      opponent_budget: int, opp_open_to_trust: bool = True) -> str:
        """根据策略类型选择动作."""
        os = opponent_history
        
        if self.strategy == "nash_breaker":
            action = self._nash_breaker(os, round_num, opponent_budget, opp_open_to_trust)
        elif self.strategy == "cautious":
            action = self._cautious(os, round_num, opponent_budget, opp_open_to_trust)
        elif self.strategy == "titfortat":
            action = self._titfortat(os)
        elif self.strategy == "adaptive":
            action = self._adaptive(os, round_num, opponent_budget, opp_open_to_trust)
        elif self.strategy == "aggressive":
            action = self._aggressive(os, round_num)
        else:
            action = 'C'
        
        if random.random() < NOISE_PROB:
            return 'D'
        return action
    
    # ── H634: 单边邀请触发信任关闭 ──
    # ── H634v2: 累积单边邀请 → 第2次关门 ──
    def mark_unilateral_invite(self) -> None:
        """被单方面 TRUST_INVITE: 累加计数，第2次触发永久关门。
        H634v2: 容忍1次噪声误发，第2次确认恶意意图。"""
        self.unilateral_invite_received += 1
        if self.unilateral_invite_received >= 2:
            self.open_to_trust = False
            self.grim_triggered_by_invite = True
    
    def _nash_breaker(self, os: List[str], r: int, ob: int,
                       opp_open_to_trust: bool = True) -> str:
        """
        Nash 突破者 (GRIM 基线 + H634 门禁):
        - 对方背叛 → 永久报复
        - (D,D) 锁死 → TRUST_INVITE 破局, 但先检查 opp_open_to_trust
        - 对方关门 → 不浪费 budget
        """
        if r == 0:
            return 'C'
        if self.in_r1:
            return 'C'
        
        # 检测 Nash 锁死
        my_recent = self.history[-2:]
        opp_recent = os[-2:] if len(os) >= 2 else []
        in_nash_lock = (
            len(my_recent) >= 2 and all(a == 'D' for a in my_recent) and
            len(opp_recent) >= 2 and all(a == 'D' for a in opp_recent)
        )
        
        if in_nash_lock:
            # H634: 升维前检查对方是否还 open_to_trust
            if self.trust_budget >= 1 and ob >= 1 and opp_open_to_trust:
                return 'TRUST_INVITE'
            # 对方已关门 or 无预算 → 留在 Nash 阱
            return 'D'
        
        # 单方 D 后对方回 C: 和平试探 (也需要对方 open)
        if (os and os[-1] == 'C' and self.history and self.history[-1] == 'D' and
            self.trust_budget >= 1 and ob >= 1 and r >= 3 and opp_open_to_trust):
            return 'TRUST_INVITE'
        
        # GRIM 基线
        if any(a == 'D' for a in os):
            return 'D'
        return 'C'
    
    def _cautious(self, os: List[str], r: int, ob: int,
                   opp_open_to_trust: bool = True) -> str:
        """谨慎型: 3连C互信 + H634 信任开放 → 升维."""
        if r == 0:
            return 'C'
        if self.in_r1:
            return 'C'
        # H634: 被单边邀请坑过 → 永久 D (GRIM lock)
        if self.grim_triggered_by_invite:
            return 'D'
        # 需要连续3轮互信 + 对方 open_to_trust
        if len(os) >= 3 and opp_open_to_trust:
            last3 = [os[i] for i in range(-3, 0) if os[i] in ('C', 'TRUST_INVITE')]
            if len(last3) == 3 and self.trust_budget >= 1 and ob >= 1:
                return 'TRUST_INVITE'
        if os and os[-1] == 'D':
            return 'D'
        return 'C'
    
    def _titfortat(self, os: List[str]) -> str:
        if not os:
            return 'C'
        if self.in_r1:
            return 'C'
        return os[-1] if os[-1] in ('C', 'D') else 'C'
    
    def _adaptive(self, os: List[str], r: int, ob: int,
                   opp_open_to_trust: bool = True) -> str:
        """自适应型: 高合作率 + H634 信任开放 → 升维."""
        if r == 0:
            return 'C'
        if self.in_r1:
            return 'C'
        # H634: 被单边邀请坑过 → 永久 D
        if self.grim_triggered_by_invite:
            return 'D'
        recent = os[-min(5, len(os)):]
        coop_rate = sum(1 for a in recent if a in ('C', 'TRUST_INVITE')) / len(recent)
        if coop_rate >= 0.8 and self.trust_budget >= 1 and ob >= 1 and r >= 2 and opp_open_to_trust:
            return 'TRUST_INVITE'
        if os and os[-1] == 'D':
            return 'D'
        return 'C'
    
    def _aggressive(self, os: List[str], r: int) -> str:
        """侵略型: 偏好剥削."""
        if r == 0:
            return 'D'
        if self.in_r1:
            if random.random() < 0.1:
                return 'D'
            return 'C'
        # 对方连续3轮合作 → 考虑升维
        if len(os) >= 3 and all(a in ('C', 'TRUST_INVITE') for a in os[-3:]) and self.trust_budget >= 1:
            return 'TRUST_INVITE'
        if random.random() < 0.2:
            return 'D'
        return 'C'
    
    def update(self, action: str, payoff: float, trust_spent: int,
               in_r1: bool, r1_rounds_left: int):
        self.history.append(action)
        self.payoff_history.append(payoff)
        self.trust_budget = max(0, self.trust_budget - trust_spent)
        self.in_r1 = in_r1
        self.r1_rounds_left = r1_rounds_left

# ============================================================
# η 评分 (MSS 意义场保真度)
# ============================================================

def compute_eta_round(actions: Tuple[str, str], payoffs: Tuple[float, float],
                      dim: int) -> float:
    a0, a1 = actions
    is_mutual_coop = (a0 in ('C', 'TRUST_INVITE') and a1 in ('C', 'TRUST_INVITE'))
    is_exploitation = (
        (a0 in ('C', 'TRUST_INVITE') and a1 == 'D') or
        (a0 == 'D' and a1 in ('C', 'TRUST_INVITE'))
    )
    elevation_bonus = 1.0 if dim == 1 else 0.0
    eta = (0.5 if is_mutual_coop else 0.0) + \
          (0.3 if not is_exploitation else 0.0) + \
          (0.2 * elevation_bonus)
    return eta

def compute_heat_round(actions: Tuple[str, str], dim: int,
                       r1_entry: bool, invite_failed: bool) -> int:
    heat = HEAT_BASELINE
    for a in actions:
        if a == 'C':
            heat += HEAT_C
        elif a == 'D':
            heat += HEAT_D
        elif a == 'TRUST_INVITE':
            heat += HEAT_TRUST_INVITE
    if dim == 1:
        heat += HEAT_R1_MAINTENANCE
    if invite_failed:
        heat += HEAT_FAILED_INVITE
    if r1_entry:
        heat += 2
    return heat

# ============================================================
# 单次运行
# ============================================================

def run_single(config: Config, seed: int, trust_budget_init: int,
               agent_strategies: Tuple[str, str] = ("nash_breaker", "cautious")) -> dict:
    """运行单次 2-Agent 20 回合博弈 (v2.1: H634 信任门禁)."""
    random.seed(seed)
    
    agents = [
        Agent(0, agent_strategies[0], trust_budget_init),
        Agent(1, agent_strategies[1], trust_budget_init),
    ]
    
    round_data = []
    r1_rounds_remaining = 0
    unilateral_invite_count = 0
    joint_enter_count = 0
    
    for t in range(config.n_rounds):
        # 获取动作 (v2.1: 传递 opp_open_to_trust)
        actions = []
        for i, agent in enumerate(agents):
            opp = agents[1 - i]
            a = agent.choose_action(opp.history, t, opp.trust_budget, opp.open_to_trust)
            actions.append(a)
        
        a0, a1 = actions
        
        # === H634v3: 单边邀请检测 → 混合门禁 (Nash豁免 + 双触发) ===
        # Nash 阱内 (D,D): 噪声可能破坏双向 joint_enter → 豁免，不计数
        # 非 Nash 阱 (C 或其他): 真正的恶意单边邀请 → 累计，2次关门
        if 'TRUST_INVITE' in actions and actions.count('TRUST_INVITE') == 1:
            unilateral_invite_count += 1
            for i, agent in enumerate(agents):
                if actions[i] != 'TRUST_INVITE' and actions[1 - i] == 'TRUST_INVITE':
                    # 接收方是否在 Nash 阱中？
                    receiver_in_nash = (
                        len(agent.history) >= 2 and
                        all(a == 'D' for a in agent.history[-2:])
                    )
                    if not receiver_in_nash:
                        # 非 Nash 阱单边邀请 → 累计计数
                        agent.mark_unilateral_invite()
        
        # === 判断升维状态 ===
        dim = 0
        trust_spent = [0, 0]
        r1_entry_this_round = False
        invite_failed = False
        
        if r1_rounds_remaining > 0:
            dim = 1
            r1_rounds_remaining -= 1
            if 'D' in actions:
                dim = 0
                r1_rounds_remaining = 0
                for i, a in enumerate(actions):
                    if a == 'D':
                        trust_spent[i] = config.r1_betrayal_penalty
            mapped = ['C' if a == 'TRUST_INVITE' else a for a in actions]
            payoffs = PAYOFF_R1[(mapped[0], mapped[1])]
        else:
            if config.enable_r1 and actions.count('TRUST_INVITE') == 2:
                # H634: 双向 TRUST_INVITE = joint_enter → 真升维
                dim = 1
                joint_enter_count += 1
                r1_entry_this_round = True
                r1_rounds_remaining = config.r1_maintenance_rounds - 1
                trust_spent = [config.r1_entry_cost, config.r1_entry_cost]
                payoffs = PAYOFF_R1[('C', 'C')]
            elif config.enable_r1 and 'TRUST_INVITE' in actions:
                # 单方邀请 → 失败, 纯热税损
                invite_failed = True
                mapped = ['C' if a == 'TRUST_INVITE' else a for a in actions]
                for i, a in enumerate(actions):
                    if a == 'TRUST_INVITE':
                        trust_spent[i] = 1  # 浪费 budget
                payoffs = PAYOFF_R0[(mapped[0], mapped[1])]
            else:
                payoffs = PAYOFF_R0[(a0 if a0 in ('C','D') else 'C',
                                     a1 if a1 in ('C','D') else 'C')]
        
        for i, agent in enumerate(agents):
            agent.update(actions[i], payoffs[i], trust_spent[i],
                        dim == 1, r1_rounds_remaining)
        
        eta = compute_eta_round((a0, a1), payoffs, dim)
        heat = compute_heat_round((a0, a1), dim, r1_entry_this_round, invite_failed)
        
        round_data.append({
            'round': t,
            'actions': [a0, a1],
            'payoffs': list(payoffs),
            'dim': dim,
            'eta': eta,
            'heat': heat,
            'trust_budget': [agents[0].trust_budget, agents[1].trust_budget],
            'r1_entry': r1_entry_this_round,
            'invite_failed': invite_failed,
            'joint_enter': actions.count('TRUST_INVITE') == 2,
            'unilateral_invite': 'TRUST_INVITE' in actions and actions.count('TRUST_INVITE') == 1,
        })
    
    all_etas = [d['eta'] for d in round_data]
    all_heats = [d['heat'] for d in round_data]
    dims = [d['dim'] for d in round_data]
    
    if len(round_data) >= 3:
        final_eta = (round_data[-3]['eta'] * 0.2 +
                    round_data[-2]['eta'] * 0.3 +
                    round_data[-1]['eta'] * 0.5)
    else:
        final_eta = round_data[-1]['eta'] if round_data else 0.0
    
    # up_success_rate: v2.1 仅统计双向 joint_enter 的轮次
    up_attempts = sum(1 for d in round_data if 'TRUST_INVITE' in d['actions'])
    up_successes = sum(1 for d in round_data if d.get('joint_enter', False))
    
    return {
        'seed': seed,
        'trust_budget_init': trust_budget_init,
        'strategies': list(agent_strategies),
        'enable_r1': config.enable_r1,
        'payoff_avg': statistics.mean([sum(d['payoffs']) for d in round_data]) / 2,
        'eta_global': statistics.mean(all_etas),
        'eta_final': final_eta,
        'total_heat': sum(all_heats),
        'heat_efficiency': sum(all_heats) / max(0.001, statistics.mean(all_etas)),
        'nash_lock_rate': statistics.mean([1.0 if d['actions'].count('D') == 2 else 0.0 for d in round_data]),
        'up_attempt_rate': min(1.0, up_attempts / len(round_data)),
        'up_success_rate': min(1.0, up_successes / max(1, up_attempts)) if up_attempts > 0 else 0.0,
        'nash_stable_rate': 0.0,
        'r1_rounds': sum(dims),
        'r1_pct': statistics.mean(dims),
        'eta_first_half': statistics.mean(all_etas[:config.n_rounds//2]),
        'eta_second_half': statistics.mean(all_etas[config.n_rounds//2:]),
        'exploitation_rate': statistics.mean([
            1.0 if ((d['actions'][0] in ('C','TRUST_INVITE') and d['actions'][1] == 'D') or
                   (d['actions'][0] == 'D' and d['actions'][1] in ('C','TRUST_INVITE')))
            else 0.0 for d in round_data
        ]),
        # H634 专项指标
        'unilateral_invite_count': unilateral_invite_count,
        'joint_enter_count': joint_enter_count,
        'heat_wasted_unilateral': unilateral_invite_count * HEAT_FAILED_INVITE,
        'agents_final_open_to_trust': [agents[0].open_to_trust, agents[1].open_to_trust],
    }

# ============================================================
# 运行全部实验
# ============================================================

STRATEGY_PAIRS = [
    ("nash_breaker", "nash_breaker"),  # 主配对: 双Nash突破者 (双向升维最优)
    ("nash_breaker", "cautious"),     # H634 测试: 突破者 vs 谨慎者 (单边封杀)
    ("aggressive", "cautious"),        # 侵略者 vs 谨慎者
    ("adaptive", "adaptive"),          # 对称双自适应
]

def run_experiment(strategy_pair_idx: int = 0, all_pairs: bool = False) -> list:
    config = Config()
    all_results = []
    
    pairs_to_run = STRATEGY_PAIRS if all_pairs else [STRATEGY_PAIRS[min(strategy_pair_idx, len(STRATEGY_PAIRS) - 1)]]
    
    for strategies in pairs_to_run:
        strategy_label = f"{strategies[0]}-{strategies[1]}"
        
        config.enable_r1 = False
        for seed in config.seeds:
            result = run_single(config, seed, 0, strategies)
            result['group'] = 'G1_R0_only'
            result['strategy_pair'] = strategy_label
            all_results.append(result)
        
        config.enable_r1 = True
        for seed in config.seeds:
            result = run_single(config, seed, 0, strategies)
            result['group'] = 'G2_R1_tb0'
            result['strategy_pair'] = strategy_label
            all_results.append(result)
        
        for tb in [2, 4, 6]:
            group = f'G{3 + [2,4,6].index(tb)}_R1_tb{tb}'
            for seed in config.seeds:
                result = run_single(config, seed, tb, strategies)
                result['group'] = group
                result['strategy_pair'] = strategy_label
                all_results.append(result)
    
    return all_results


def aggregate_by_group(results: list) -> Dict[str, dict]:
    groups = {}
    for r in results:
        g = r['group']
        if g not in groups:
            groups[g] = []
        groups[g].append(r)
    
    aggregated = {}
    metrics = ['payoff_avg', 'eta_global', 'eta_final', 'total_heat',
               'heat_efficiency', 'nash_lock_rate', 'up_attempt_rate',
               'up_success_rate', 'r1_pct',
               'eta_first_half', 'eta_second_half', 'exploitation_rate']
    
    for group, entries in groups.items():
        agg = {'group': group, 'n': len(entries)}
        for m in metrics:
            vals = [e[m] for e in entries]
            agg[f'{m}_mean'] = statistics.mean(vals)
            agg[f'{m}_std'] = statistics.stdev(vals) if len(vals) > 1 else 0.0
        aggregated[group] = agg
    
    return aggregated


def write_csv(results: list, path: str = 'experiments/e021/e021_experiment_v2.1.csv'):
    fieldnames = [
        'group', 'seed', 'strategies', 'trust_budget_init', 'enable_r1',
        'payoff_avg', 'eta_global', 'eta_final', 'total_heat', 'heat_efficiency',
        'nash_lock_rate', 'up_attempt_rate', 'up_success_rate',
        'r1_pct', 'eta_first_half', 'eta_second_half', 'exploitation_rate',
        'unilateral_invite_count', 'joint_enter_count', 'heat_wasted_unilateral',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in results:
            row = {k: r.get(k, '') for k in fieldnames}
            row['strategies'] = '-'.join(r.get('strategies', ['?','?']))
            writer.writerow(row)
    return path


def print_summary(aggregated: Dict[str, dict]):
    order = ['G1_R0_only', 'G2_R1_tb0', 'G3_R1_tb2', 'G4_R1_tb4', 'G5_R1_tb6']
    labels = {
        'G1_R0_only': 'G1 (R0 only)',
        'G2_R1_tb0':  'G2 (R1, tb=0)',
        'G3_R1_tb2':  'G3 (R1, tb=2)',
        'G4_R1_tb4':  'G4 (R1, tb=4)',
        'G5_R1_tb6':  'G5 (R1, tb=6)',
    }
    
    print()
    print("=" * 90)
    print("  E021-1 v2.1: Nash 驻点 η 基线测量 (H634 joint_enter 信任门禁)")
    print("=" * 90)
    print(f"  {'组':>14s}  {'η_global':>8s}  {'η_final':>8s}  {'payoff':>8s}  {'heat':>6s}  {'Nash锁':>7s}  {'R1%':>6s}  {'剥削':>6s}  {'单边邀':>6s}")
    print("  " + "-" * 82)
    
    baseline_eta = None
    for group in order:
        if group not in aggregated:
            continue
        a = aggregated[group]
        label = labels.get(group, group)
        if baseline_eta is None:
            baseline_eta = a['eta_global_mean']
        
        delta = ""
        if baseline_eta and a['eta_global_mean'] != baseline_eta:
            d = a['eta_global_mean'] - baseline_eta
            delta = f"  Δ=+{d:.3f}" if d > 0 else f"  Δ={d:.3f}"
        
        print(f"  {label:>14s}  {a['eta_global_mean']:8.3f}  {a['eta_final_mean']:8.3f}  "
              f"{a['payoff_avg_mean']:8.2f}  {a['total_heat_mean']:6.0f}  "
              f"{a['nash_lock_rate_mean']:7.3f}  {a['r1_pct_mean']:6.3f}  "
              f"{a['exploitation_rate_mean']:6.3f}{delta}")
    
    print()
    print("  ── 核心发现 ──")
    g1 = aggregated.get('G1_R0_only', {})
    g5 = aggregated.get('G5_R1_tb6', {})
    if g1 and g5:
        eta_gain = g5['eta_global_mean'] - g1['eta_global_mean']
        nash_drop = g1['nash_lock_rate_mean'] - g5['nash_lock_rate_mean']
        print(f"  η_global 升维增益: +{eta_gain:.3f} ({(eta_gain/g1['eta_global_mean']*100):.0f}% 相对提升)" if eta_gain > 0 else f"  η_global 变化: {eta_gain:.3f}")
        print(f"  Nash 锁死率下降:  {nash_drop:.3f} ({g1['nash_lock_rate_mean']:.3f}→{g5['nash_lock_rate_mean']:.3f})")
    print()


# ============================================================
# main
# ============================================================

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='E021-1 v2.1: Nash 驻点 η 基线测量 (H634)')
    p.add_argument('--strategy-pair', type=int, default=0,
                   help='策略对: 0=nash_breaker×2, 1=nb-cautious, 2=aggressive-cautious, 3=adaptive×2')
    p.add_argument('--all-pairs', action='store_true',
                   help='全部4组策略对')
    p.add_argument('--output', type=str, default='experiments/e021/e021_experiment.csv')
    p.add_argument('--noise', type=float, default=NOISE_PROB,
                   help=f'噪声概率 (默认: {NOISE_PROB})')
    args = p.parse_args()
    
    NOISE_PROB = args.noise
    
    if args.all_pairs:
        pair_list = [f"{a}-{b}" for a, b in STRATEGY_PAIRS]
    else:
        pair_list = [f"{STRATEGY_PAIRS[args.strategy_pair][0]}-{STRATEGY_PAIRS[args.strategy_pair][1]}"]
    
    print(f"E021-1 v2.1 (H634 joint_enter 信任门禁)")
    print(f"策略对: {', '.join(pair_list)}")
    print(f"噪声率: {NOISE_PROB:.0%}")
    print(f"矩阵:   G1-G5 × 5 seeds = {len(pair_list) * 25} runs")
    
    results = run_experiment(args.strategy_pair, all_pairs=args.all_pairs)
    path = write_csv(results, args.output)
    aggregated = aggregate_by_group(results)
    print_summary(aggregated)
    print(f"CSV → {path}  ({len(results)} runs, {len(results) * 20} rounds)")
