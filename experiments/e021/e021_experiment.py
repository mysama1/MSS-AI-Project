"""
E021-1: Nash驻点 η 基线测量 — 囚徒困境 R0/R0+R1 对比
================================================================
核心命题: Nash 驻点 (D,D) 在 η 尺度下是局部极小，不是全局最优。
升维 (trust_budget → R1) 是跳出 Nash 阱的唯一路径。
A3(热税) 决定升维能否支付入场费，A6(升维) 决定入场后能否维持。

设计日期: 2026-06-17
输出: experiments/e021/e021_experiment.csv
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
    ('C', 'D'): (-1, 6),      # R1 内背叛惩罚更重
    ('D', 'C'): (6, -1),
    ('D', 'D'): (0, 0),       # R1 内双方背叛等于契约破裂
}

# ============================================================
# 环境噪声
# ============================================================

NOISE_PROB = 0.10  # 每轮每个Agent有10%概率随机背叛
# 噪声是 Nash 阱的触发器: 一次意外背叛 → GRIM螺旋 → 永久 (D,D)

# ============================================================
# 热税模型 (A3 不可约化热税)
# ============================================================

HEAT_BASELINE = 5       # 每轮基础计算成本
HEAT_C = 2              # 合作决策成本（需要推理对方）
HEAT_D = 1              # 背叛决策成本（简单自利）
HEAT_TRUST_INVITE = 5   # TRUST_INVITE 协商开销
HEAT_R1_MAINTENANCE = 3 # R1 契约维持成本
HEAT_FAILED_INVITE = 3  # 单方面邀请失败的浪费热税

# ============================================================
# Agent 策略类型
# ============================================================

class Agent:
    """多策略 Agent，决策依赖 trust_budget 余额 + 对手历史."""
    
    def __init__(self, agent_id: int, strategy: str, trust_budget: int = 0):
        self.id = agent_id
        self.strategy = strategy  # "nash_breaker" / "cautious" / "titfortat" / "adaptive" / "aggressive"
        self.trust_budget = trust_budget
        self.initial_trust_budget = trust_budget
        self.history: List[str] = []
        self.payoff_history: List[float] = []
        self.in_r1 = False
        self.r1_rounds_left = 0
    
    def choose_action(self, opponent_history: List[str], round_num: int,
                      opponent_budget: int) -> str:
        """根据策略类型选择动作."""
        os = opponent_history  # shorthand
        
        if self.strategy == "nash_breaker":
            action = self._nash_breaker(os, round_num, opponent_budget)
        elif self.strategy == "cautious":
            action = self._cautious(os, round_num, opponent_budget)
        elif self.strategy == "titfortat":
            action = self._titfortat(os)
        elif self.strategy == "adaptive":
            action = self._adaptive(os, round_num, opponent_budget)
        elif self.strategy == "aggressive":
            action = self._aggressive(os, round_num)
        else:
            action = 'C'
        
        # 环境噪声: 小概率随机背叛
        if random.random() < NOISE_PROB:
            return 'D'
        return action
    
    def _nash_breaker(self, os: List[str], r: int, ob: int) -> str:
        """
        Nash 突破者 (GRIM 基线):
        - 正常时: 合作，直到对方背叛一次 → 永久报复
        - 检测到 (D,D) 连续2轮 + 有预算: TRUST_INVITE 尝试破局
        - R1 成功后: 重置 GRIM 标志
        这是唯一能同时展示 Nash 阱(A3) 和 升维突破(A6) 的策略。
        """
        if r == 0:
            return 'C'
        if self.in_r1:
            return 'C'
        
        # 检测 Nash 锁死: 最近2轮双方都是 D
        my_recent = self.history[-2:]
        opp_recent = os[-2:] if len(os) >= 2 else []
        in_nash_lock = (
            len(my_recent) >= 2 and all(a == 'D' for a in my_recent) and
            len(opp_recent) >= 2 and all(a == 'D' for a in opp_recent)
        )
        
        if in_nash_lock:
            # (D,D) 锁死 → 尝试升维突破 (A6: 改规则摆脱 Nash 阱)
            if self.trust_budget >= 1 and ob >= 1:
                return 'TRUST_INVITE'
            # 无预算 → 留在 Nash 阱
            return 'D'
        
        # 单方 D 后对方回 C: 和平试探
        if (os and os[-1] == 'C' and self.history and self.history[-1] == 'D' and
            self.trust_budget >= 1 and ob >= 1 and r >= 3):
            # 对方释放善意 → 直接 TRUST_INVITE 加速恢复
            return 'TRUST_INVITE'
        
        # GRIM 基线: 对方历史上背叛过 → 永久 D
        if any(a == 'D' for a in os):
            return 'D'
        
        return 'C'
    
    def _cautious(self, os: List[str], r: int, ob: int) -> str:
        """谨慎型: 需要连续3轮互信才尝试升维."""
        if r == 0:
            return 'C'
        # 如果已经进入 R1: 维持合作
        if self.in_r1:
            return 'C'  # 在 R1 内保持合作（契约已建立）
        # 需要连续3轮互信 (C 或 TRUST_INVITE 均为合作信号) 才考虑升维
        if len(os) >= 3:
            last3 = [os[i] for i in range(-3, 0) if os[i] in ('C', 'TRUST_INVITE')]
            if len(last3) == 3 and self.trust_budget >= 1 and ob >= 1:
                return 'TRUST_INVITE'
        # 对方最近背叛过: 报复
        if os and os[-1] == 'D':
            return 'D'
        return 'C'
    
    def _titfortat(self, os: List[str]) -> str:
        """Tit-for-tat: 镜像对方上一轮."""
        if not os:
            return 'C'
        if self.in_r1:
            return 'C'
        return os[-1] if os[-1] in ('C', 'D') else 'C'
    
    def _adaptive(self, os: List[str], r: int, ob: int) -> str:
        """自适应型: 在合作率高时主动升维，遭遇背叛后快速报复."""
        if r == 0:
            return 'C'
        if self.in_r1:
            return 'C'
        # 计算近5轮合作率
        recent = os[-min(5, len(os)):]
        coop_rate = sum(1 for a in recent if a in ('C', 'TRUST_INVITE')) / len(recent)
        # 合作率高且双方都有预算: 尝试升维
        if coop_rate >= 0.8 and self.trust_budget >= 1 and ob >= 1 and r >= 2:
            return 'TRUST_INVITE'
        # 对方背叛: 报复
        if os[-1] == 'D':
            return 'D'
        return 'C'
    
    def _aggressive(self, os: List[str], r: int) -> str:
        """侵略型: 偏好剥削，仅在对方强度足够时让步."""
        if r == 0:
            return 'D'  # 开局试探
        if self.in_r1:
            # R1 内也不老实: 10% 概率背叛
            if random.random() < 0.1:
                return 'D'
            return 'C'
        # 如果对方连续3轮 C/TRUST_INVITE 且我们 budget>0: 升维
        if len(os) >= 3 and all(a in ('C', 'TRUST_INVITE') for a in os[-3:]) and self.trust_budget >= 1:
            return 'TRUST_INVITE'
        # 偶尔试探背叛
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
    """
    单轮 η: 意义场协同度量。
    组件:
      - mutual_coop: 双方是否做出互信选择 (C,C) 或 (TRUST_INVITE,TRUST_INVITE)
      - no_exploitation: 是否存在单方剥削 (C,D) 或 (D,C)
      - elevation_bonus: 是否成功维持在升维态
    """
    a0, a1 = actions
    
    # 互信密度: 双方都在合作态（含升维）
    is_mutual_coop = (
        (a0 in ('C', 'TRUST_INVITE') and a1 in ('C', 'TRUST_INVITE'))
    )
    
    # 剥削检测
    is_exploitation = (
        (a0 in ('C', 'TRUST_INVITE') and a1 == 'D') or
        (a0 == 'D' and a1 in ('C', 'TRUST_INVITE'))
    )
    
    # 升维奖励: 成功在 R1 内
    elevation_bonus = 1.0 if dim == 1 else 0.0
    
    # η = 互信 × 0.5 + 非剥削 × 0.3 + 升维 × 0.2
    eta = (0.5 if is_mutual_coop else 0.0) + \
          (0.3 if not is_exploitation else 0.0) + \
          (0.2 * elevation_bonus)
    
    return eta

def compute_heat_round(actions: Tuple[str, str], dim: int,
                       r1_entry: bool, invite_failed: bool) -> int:
    """单轮热税 (tok 计数)."""
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
        heat += 2  # 入场协商额外成本
    return heat

# ============================================================
# 单次运行
# ============================================================

def run_single(config: Config, seed: int, trust_budget_init: int,
               agent_strategies: Tuple[str, str] = ("adaptive", "cautious")) -> dict:
    """运行单次 2-Agent 20 回合博弈."""
    random.seed(seed)
    
    agents = [
        Agent(0, agent_strategies[0], trust_budget_init),
        Agent(1, agent_strategies[1], trust_budget_init),
    ]
    
    round_data = []
    r1_rounds_remaining = 0  # 当前 R1 还剩多少轮
    
    for t in range(config.n_rounds):
        # 获取动作
        actions = []
        for i, agent in enumerate(agents):
            opp = agents[1 - i]
            a = agent.choose_action(opp.history, t, opp.trust_budget)
            actions.append(a)
        
        a0, a1 = actions
        
        # === 判断升维状态 ===
        dim = 0
        trust_spent = [0, 0]
        r1_entry_this_round = False
        invite_failed = False
        
        if r1_rounds_remaining > 0:
            # 当前在 R1 内
            dim = 1
            r1_rounds_remaining -= 1
            # R1 内: 双方都必须保持 C。如果有人 D，契约破裂
            if 'D' in actions:
                dim = 0
                r1_rounds_remaining = 0
                # 背叛方受 trust_budget 罚金
                for i, a in enumerate(actions):
                    if a == 'D':
                        trust_spent[i] = config.r1_betrayal_penalty
            # 映射: TRUST_INVITE 在 R1 内等同于 C
            mapped_actions = ['C' if a == 'TRUST_INVITE' else a for a in actions]
            payoffs = PAYOFF_R1[(mapped_actions[0], mapped_actions[1])]
        else:
            # 当前在 R0
            if config.enable_r1 and actions.count('TRUST_INVITE') == 2:
                # 双方都邀请 → 进入 R1
                dim = 1
                r1_entry_this_round = True
                r1_rounds_remaining = config.r1_maintenance_rounds - 1  # 本轮已消耗
                trust_spent = [config.r1_entry_cost, config.r1_entry_cost]
                payoffs = PAYOFF_R1[('C', 'C')]  # 入场即合作
            elif config.enable_r1 and 'TRUST_INVITE' in actions:
                # 单方面邀请 → 失败, 映射为 C, 发起方损失 budget
                invite_failed = True
                mapped = ['C' if a == 'TRUST_INVITE' else a for a in actions]
                for i, a in enumerate(actions):
                    if a == 'TRUST_INVITE':
                        trust_spent[i] = 1
                payoffs = PAYOFF_R0[(mapped[0], mapped[1])]
            else:
                # 普通 R0 博弈
                payoffs = PAYOFF_R0[(a0 if a0 in ('C','D') else 'C',
                                     a1 if a1 in ('C','D') else 'C')]
        
        # 更新 Agent 状态
        for i, agent in enumerate(agents):
            agent.update(actions[i], payoffs[i], trust_spent[i],
                        dim == 1, r1_rounds_remaining)
        
        # 计算 η 和 heat
        eta = compute_eta_round((a0, a1), payoffs, dim)
        heat = compute_heat_round((a0, a1), dim, r1_entry_this_round, invite_failed)
        
        # Nash 稳定性测试: 在当前状态下，单方背叛是否更优？
        nash_stable = None
        if dim == 0:
            # R0: 测试 Agent 0 是否可以通过背叛改进
            current_p0 = payoffs[0]
            opp_action = a1 if a1 in ('C','D') else 'C'
            alt_payoff = PAYOFF_R0[('D', opp_action)][0]
            nash_stable = alt_payoff >= current_p0
        else:
            # R1: 测试背叛能否改进 (但背叛导致契约破裂，取破裂后收益)
            # R1 内 Nash 稳定性由维持契约 vs 背叛的长期差异决定
            nash_stable = False  # R1 内 Nash 总是"不稳定"——背叛短期更优但长期更差
        
        round_data.append({
            'round': t,
            'actions': [a0, a1],
            'payoffs': list(payoffs),
            'dim': dim,
            'eta': eta,
            'heat': heat,
            'trust_budget': [agents[0].trust_budget, agents[1].trust_budget],
            'nash_stable': nash_stable,
            'r1_entry': r1_entry_this_round,
            'invite_failed': invite_failed,
        })
    
    # === 全局指标 ===
    all_payoffs = [sum(d['payoffs']) for d in round_data]
    all_etas = [d['eta'] for d in round_data]
    all_heats = [d['heat'] for d in round_data]
    dims = [d['dim'] for d in round_data]
    nash_tests = [d['nash_stable'] for d in round_data if d['nash_stable'] is not None]
    
    # 末态 η: 最后3轮的加权平均 (越靠后权重越高)
    if len(round_data) >= 3:
        final_eta = (round_data[-3]['eta'] * 0.2 + 
                    round_data[-2]['eta'] * 0.3 + 
                    round_data[-1]['eta'] * 0.5)
    else:
        final_eta = round_data[-1]['eta'] if round_data else 0.0
    
    return {
        'seed': seed,
        'trust_budget_init': trust_budget_init,
        'strategies': list(agent_strategies),
        'enable_r1': config.enable_r1,
        # 全局
        'payoff_avg': statistics.mean(all_payoffs) / 2,
        'eta_global': statistics.mean(all_etas),
        'eta_final': final_eta,
        'total_heat': sum(all_heats),
        'heat_efficiency': sum(all_heats) / max(0.001, statistics.mean(all_etas)),
        'nash_lock_rate': statistics.mean([1.0 if d['actions'].count('D') == 2 else 0.0 for d in round_data]),
        'up_attempt_rate': statistics.mean([1.0 if 'TRUST_INVITE' in d['actions'] else 0.0 for d in round_data]),
        'up_success_rate': statistics.mean([1.0 if d['dim'] == 1 else 0.0 for d in round_data]),
        'nash_stable_rate': statistics.mean([1.0 if ns else 0.0 for ns in nash_tests]) if nash_tests else 0.0,
        # 维度统计
        'r1_rounds': sum(dims),
        'r1_pct': statistics.mean(dims),
        # 分阶段 η (前半 vs 后半)
        'eta_first_half': statistics.mean(all_etas[:config.n_rounds//2]),
        'eta_second_half': statistics.mean(all_etas[config.n_rounds//2:]),
        # 剥削率
        'exploitation_rate': statistics.mean([
            1.0 if ((d['actions'][0] in ('C','TRUST_INVITE') and d['actions'][1] == 'D') or
                   (d['actions'][0] == 'D' and d['actions'][1] in ('C','TRUST_INVITE')))
            else 0.0 for d in round_data
        ]),
    }

# ============================================================
# 运行全部实验
# ============================================================

STRATEGY_PAIRS = [
    ("nash_breaker", "nash_breaker"),  # 主配对: 双Nash突破者 (最有区分度)
    ("nash_breaker", "cautious"),     # 突破者 vs 谨慎者
    ("aggressive", "cautious"),        # 侵略者 vs 谨慎者
    ("adaptive", "adaptive"),          # 对称双自适应
]

def run_experiment(strategy_pair_idx: int = 0, all_pairs: bool = False) -> list:
    """运行 E021-1 全部实验组."""
    config = Config()
    all_results = []
    
    pairs_to_run = STRATEGY_PAIRS if all_pairs else [STRATEGY_PAIRS[min(strategy_pair_idx, len(STRATEGY_PAIRS) - 1)]]
    
    for strategies in pairs_to_run:
        strategy_label = f"{strategies[0]}-{strategies[1]}"
        
        # G1: R0 only (经典 PD, Nash 基线)
        config.enable_r1 = False
        for seed in config.seeds:
            result = run_single(config, seed, 0, strategies)
            result['group'] = 'G1_R0_only'
            result['strategy_pair'] = strategy_label
            all_results.append(result)
        
        # G2: R0+R1, trust_budget=0 (有钱升维但没钱)
        config.enable_r1 = True
        for seed in config.seeds:
            result = run_single(config, seed, 0, strategies)
            result['group'] = 'G2_R1_tb0'
            result['strategy_pair'] = strategy_label
            all_results.append(result)
        
        # G3-G5: R0+R1, trust_budget=2/4/6
        for tb in [2, 4, 6]:
            group = f'G{3 + [2,4,6].index(tb)}_R1_tb{tb}'
            for seed in config.seeds:
                result = run_single(config, seed, tb, strategies)
                result['group'] = group
                result['strategy_pair'] = strategy_label
                all_results.append(result)
    
    return all_results


def aggregate_by_group(results: list) -> Dict[str, dict]:
    """按组聚合统计."""
    groups = {}
    for r in results:
        g = r['group']
        if g not in groups:
            groups[g] = []
        groups[g].append(r)
    
    aggregated = {}
    metrics = ['payoff_avg', 'eta_global', 'eta_final', 'total_heat',
               'heat_efficiency', 'nash_lock_rate', 'up_attempt_rate',
               'up_success_rate', 'nash_stable_rate', 'r1_pct',
               'eta_first_half', 'eta_second_half', 'exploitation_rate']
    
    for group, entries in groups.items():
        agg = {'group': group, 'n': len(entries)}
        for m in metrics:
            vals = [e[m] for e in entries]
            agg[f'{m}_mean'] = statistics.mean(vals)
            agg[f'{m}_std'] = statistics.stdev(vals) if len(vals) > 1 else 0.0
        aggregated[group] = agg
    
    return aggregated


def write_csv(results: list, path: str = 'experiments/e021/e021_experiment.csv'):
    """写入 CSV."""
    fieldnames = [
        'group', 'seed', 'strategies', 'trust_budget_init', 'enable_r1',
        'payoff_avg', 'eta_global', 'eta_final', 'total_heat', 'heat_efficiency',
        'nash_lock_rate', 'up_attempt_rate', 'up_success_rate', 'nash_stable_rate',
        'r1_pct', 'eta_first_half', 'eta_second_half', 'exploitation_rate'
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
    """终端摘要."""
    order = ['G1_R0_only', 'G2_R1_tb0', 'G3_R1_tb2', 'G4_R1_tb4', 'G5_R1_tb6']
    labels = {
        'G1_R0_only': 'G1 (R0 only)',
        'G2_R1_tb0':  'G2 (R1, tb=0)',
        'G3_R1_tb2':  'G3 (R1, tb=2)',
        'G4_R1_tb4':  'G4 (R1, tb=4)',
        'G5_R1_tb6':  'G5 (R1, tb=6)',
    }
    
    print()
    print("=" * 82)
    print("  E021-1: Nash 驻点 η 基线测量")
    print("=" * 82)
    print(f"  {'组':>14s}  {'η_global':>8s}  {'η_final':>8s}  {'payoff':>8s}  {'heat':>6s}  {'Nash锁':>7s}  {'R1%':>6s}  {'剥削':>6s}")
    print("  " + "-" * 76)
    
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
        print(f"  η_global 升维增益: +{eta_gain:.3f} ({(eta_gain/g1['eta_global_mean']*100):.0f}% 相对提升)")
        print(f"  Nash 锁死率下降:  {nash_drop:.3f} ({g1['nash_lock_rate_mean']:.3f}→{g5['nash_lock_rate_mean']:.3f})")
        print(f"  剥削率变化:        {g1['exploitation_rate_mean']:.3f}→{g5['exploitation_rate_mean']:.3f}")
    print()


# ============================================================
# main
# ============================================================

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='E021-1: Nash 驻点 η 基线测量')
    p.add_argument('--strategy-pair', type=int, default=0,
                   help='策略对索引: 0=adaptive-cautious, 1=tft-tft, 2=aggressive-cautious, 3=adaptive-adaptive')
    p.add_argument('--all-pairs', action='store_true',
                   help='运行全部4组策略对 (100次运行)')
    p.add_argument('--output', type=str, default='experiments/e021/e021_experiment.csv')
    args = p.parse_args()
    
    if args.all_pairs:
        print("全策略对模式: adaptive-cautious + tft-tft + aggressive-cautious + adaptive-adaptive")
        pair_list = [f"{a}-{b}" for a, b in STRATEGY_PAIRS]
    else:
        pair_list = [f"{STRATEGY_PAIRS[args.strategy_pair][0]}-{STRATEGY_PAIRS[args.strategy_pair][1]}"]
    
    print(f"策略对: {', '.join(pair_list)}")
    print(f"噪声率: {NOISE_PROB:.0%} (模拟误通信/意外触发 Nash 螺旋)")
    print(f"矩阵:   G1(R0) + G2-G5(R0+R1, tb=0/2/4/6) × 5 seeds = {len(pair_list) * 25} runs")
    
    results = run_experiment(args.strategy_pair, all_pairs=args.all_pairs)
    path = write_csv(results, args.output)
    
    aggregated = aggregate_by_group(results)
    print_summary(aggregated)
    
    print(f"CSV 已写入: {path}")
    print(f"共 {len(results)} 次运行, {len(results) * 20} 回合博弈")
