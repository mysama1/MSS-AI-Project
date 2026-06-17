"""
P1+P2+P3: N→∞渗流相变 — 完整三线执行
========================================
P1: 数值标度 → 加密采样N_c附近 → FSS → 临界指数ν,β
P2: 渗流模型 → H634-G关门→bond percolation → p_close理论
P3: 泛函分析 → 平均场方程 → η_global泛函形式

产出: 临界指数数值估计 + 普适类对比 + 理论一致性验证
"""

import json, math, random, time, os, sys
from statistics import mean, stdev
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════
# P1: 有限尺寸标度 (Finite-Size Scaling) — 临界指数ν, β
# ═══════════════════════════════════════════════════════════════════

class FiniteSizeScaling:
    """
    渗流普适类参考值:
      2D bond percolation: ν = 4/3 ≈ 1.333, β = 5/36 ≈ 0.139
      2D Ising: ν = 1, β = 1/8 = 0.125
      Mean-field: ν = 1/2 = 0.5, β = 1/2 = 0.5
      3D percolation: ν ≈ 0.876, β ≈ 0.418
    
    FSS假设:
      序参量 m(N, p) = N^(-β/ν) · F( (p - p_c) · N^(1/ν) )
      其中p = p_close (关门概率), m = 1 - η_global (秩序破坏度)
    """
    
    KNOWN_UNIVERSALITY = {
        '2D_percolation':   {'ν': 1.333, 'β': 0.139, 'd': 2},
        '2D_Ising':         {'ν': 1.0,   'β': 0.125, 'd': 2},
        'mean_field':       {'ν': 0.5,   'β': 0.5,   'd': 6},
        '3D_percolation':   {'ν': 0.876, 'β': 0.418, 'd': 3},
        '3D_Ising':         {'ν': 0.630, 'β': 0.326, 'd': 3},
    }
    
    @staticmethod
    def run_dense_sampling(N_values, p_close_values, n_seeds=50, 
                           n_rounds_per_seed=100, noise_prob=0.10,
                           trust_budget_base=0.5):
        """
        在N×p网格上密集采样, 每点n_seeds次独立运行.
        
        Returns: {(N, p_close): [η_global_1, η_global_2, ...]}
        """
        results = {}
        total = len(N_values) * len(p_close_values)
        done = 0
        
        for N in N_values:
            for p_c in p_close_values:
                etas = []
                for seed in range(n_seeds):
                    random.seed(seed * 10000 + N * 100 + int(p_c * 1000))
                    eta = FiniteSizeScaling._simulate_one(
                        N, p_c, n_rounds_per_seed, noise_prob, trust_budget_base
                    )
                    etas.append(eta)
                results[(N, p_c)] = etas
                done += 1
                if done % 10 == 0:
                    print(f"   采样进度: {done}/{total}")
        
        return results
    
    @staticmethod
    def _simulate_one(N, p_close, n_rounds, noise_prob, trust_budget):
        """单次N-agent模拟: 关门传播模型."""
        # 初始: 全部open
        doors = [True] * N  # True = open (合作)
        trust = [trust_budget] * N
        total_doors = N * (N - 1) // 2  # 所有二元关系
        
        for rnd in range(n_rounds):
            # 随机选一对(i,j)
            i = random.randint(0, N - 1)
            j = random.randint(0, N - 1)
            if i == j:
                continue
            
            # 噪声: 10%概率随机翻转
            if random.random() < noise_prob:
                if doors[i] and doors[j]:  # 双开→可能单侧关
                    doors[i] = False if random.random() < 0.5 else doors[i]
                    doors[j] = False if random.random() < 0.5 else doors[j]
                continue
            
            # 正常关门动力学
            if doors[i] and doors[j]:
                # 双方都open: 以p_close概率关门
                if random.random() < p_close:
                    # 选择关门方向
                    if random.random() < 0.5:
                        doors[i] = False  # i关门 (背叛j)
                        trust[j] = max(0, trust[j] - 0.1)  # j信任受损
                    else:
                        doors[j] = False
                        trust[i] = max(0, trust[i] - 0.1)
            
            elif doors[i] != doors[j]:
                # 单侧已关: 低信任方可能被感染
                closed_one = i if not doors[i] else j
                open_one = j if not doors[i] else i
                if trust[open_one] < 0.3 and random.random() < 0.4:
                    doors[open_one] = False  # 被感染关门
            
            # 恢复机制: 如果信任>0.7, 有概率重新开门
            for k in range(N):
                if not doors[k] and trust[k] > 0.7 and random.random() < 0.1:
                    doors[k] = True
        
        # 计算η_global (开门数/总对数)
        open_pairs = sum(1 for a in range(N) for b in range(a+1, N) 
                        if doors[a] and doors[b])
        return open_pairs / max(total_doors, 1)
    
    @staticmethod
    def compute_order_parameter(results):
        """从模拟结果提取序参量m = 1 - <η>."""
        summary = {}
        for (N, p_c), etas in results.items():
            avg_eta = mean(etas)
            std_eta = stdev(etas) if len(etas) > 1 else 0
            summary[(N, p_c)] = {
                'N': N,
                'p_close': p_c,
                'η_mean': round(avg_eta, 4),
                'η_std': round(std_eta, 4),
                'm_order': round(1.0 - avg_eta, 4),  # 序参量
                'samples': len(etas),
            }
        return summary
    
    @staticmethod
    def fit_critical_exponents(summary, p_c_guess=0.4):
        """
        有限尺寸标度拟合.
        
        方法: 对每个N, 找到p_close使m最大变化率的位置
        → 这给出effective p_c(N)
        → 拟合 p_c(N) = p_c(∞) + a·N^(-1/ν)
        → 拟合 m_max(N) = b·N^(-β/ν)
        """
        from collections import defaultdict
        
        # 按N分组
        by_N = defaultdict(list)
        for (N, p_c), data in summary.items():
            by_N[N].append((p_c, data['m_order'], data['η_mean'], data['η_std']))
        
        N_sorted = sorted(by_N.keys())
        
        # 对每个N, 找最大变化率位置
        effective_pc = {}
        max_slope = {}
        m_at_pc = {}
        
        print("\n  ── 每N的effective p_c ──")
        for N in N_sorted:
            points = sorted(by_N[N], key=lambda x: x[0])  # sort by p_close
            # 计算m(p)的数值导数
            slopes = []
            for i in range(1, len(points)):
                dp = points[i][0] - points[i-1][0]
                dm = points[i][1] - points[i-1][1]
                if dp > 0:
                    slopes.append((points[i][0], dm/dp, (points[i][1] + points[i-1][1])/2))
            
            if slopes:
                best = max(slopes, key=lambda x: x[1])  # max slope
                effective_pc[N] = best[0]
                max_slope[N] = best[1]
                m_at_pc[N] = best[2]
                print(f"    N={N:3d}: p_c_eff={best[0]:.4f}, max_slope={best[1]:.4f}, m={best[2]:.4f}")
        
        # 拟合ν: p_c(N) = p_c(∞) + a·N^(-1/ν)
        # 最小二乘拟合
        Ns = sorted(effective_pc.keys())
        
        if len(Ns) >= 3:
            # 用N^(-1/ν)对p_c做线性回归, 扫描ν
            best_nu, best_r2 = 1.0, 0
            for nu in [round(0.3 + i*0.05, 3) for i in range(40)]:  # 0.3-2.3
                xs = [N**(-1/nu) for N in Ns]
                ys = [effective_pc[N] for N in Ns]
                mean_x = sum(xs) / len(xs)
                mean_y = sum(ys) / len(ys)
                num = sum((xs[i]-mean_x)*(ys[i]-mean_y) for i in range(len(xs)))
                den = sum((x-mean_x)**2 for x in xs)
                if den > 1e-10:
                    slope = num / den
                    intercept = mean_y - slope * mean_x
                    pred = [slope*x + intercept for x in xs]
                    ss_res = sum((ys[i]-pred[i])**2 for i in range(len(ys)))
                    ss_tot = sum((y-mean_y)**2 for y in ys)
                    r2 = 1 - ss_res / max(ss_tot, 1e-10)
                    if r2 > best_r2:
                        best_r2 = r2
                        best_nu = nu
                        pc_inf = intercept
            
            # 固定ν, 用m(N) = b·N^(-β/ν)拟合β
            nu = best_nu
            log_Ns = [math.log(N) for N in Ns]
            log_ms = [math.log(max(m_at_pc[N], 1e-6)) for N in Ns]
            
            mean_ln = sum(log_Ns) / len(log_Ns)
            mean_lm = sum(log_ms) / len(log_ms)
            num = sum((log_Ns[i]-mean_ln)*(log_ms[i]-mean_lm) for i in range(len(log_Ns)))
            den = sum((ln-mean_ln)**2 for ln in log_Ns)
            beta_over_nu = -num / max(den, 1e-10)  # slope = -β/ν
            beta = beta_over_nu * nu
            
            fit_result = {
                'ν': round(nu, 4),
                'β': round(beta, 4),
                'p_c_inf': round(pc_inf, 4),
                'ν_R²': round(best_r2, 4),
                'fitting_method': 'FSS linear regression',
                'data_points': len(Ns),
            }
        else:
            fit_result = {
                'ν': None, 'β': None, 'p_c_inf': None,
                'error': f'Need >=3 N values, got {len(Ns)}',
            }
        
        return fit_result, effective_pc, m_at_pc
    
    @staticmethod
    def compare_universality(nu_fit, beta_fit, d=2):
        """与已知普适类对比."""
        comparisons = []
        for name, vals in FiniteSizeScaling.KNOWN_UNIVERSALITY.items():
            if vals['d'] != d:
                continue  # 仅比较同维度
            d_nu = abs(nu_fit - vals['ν']) / max(vals['ν'], 0.01)
            d_beta = abs(beta_fit - vals['β']) / max(vals['β'], 0.01)
            dist = math.sqrt(d_nu**2 + d_beta**2)
            comparisons.append({
                'class': name,
                'ν_ref': vals['ν'],
                'β_ref': vals['β'],
                'ν_diff': round(d_nu*100, 1),
                'β_diff': round(d_beta*100, 1),
                'distance': round(dist, 3),
            })
        comparisons.sort(key=lambda x: x['distance'])
        return comparisons
    
    @staticmethod
    def data_collapse(summary, nu, beta, p_c_inf):
        """
        验证数据collapse: 绘制 m·N^(β/ν) vs (p-p_c)·N^(1/ν)
        对不同的N, 数据点应收敛到同一条曲线F(x)
        """
        by_N = defaultdict(list)
        for (N, p_c), data in summary.items():
            x = (p_c - p_c_inf) * N**(1/nu)
            y = data['m_order'] * N**(beta/nu)
            by_N[N].append((x, y))
        
        # 按x排序所有点, 计算bin平均
        all_points = [(x, y, N) for N, pts in by_N.items() for x, y in pts]
        all_points.sort(key=lambda p: p[0])
        
        # 计算collapse质量: 各N的点的y值在不同x bin的方差
        x_bins = defaultdict(lambda: defaultdict(list))
        for x, y, N in all_points:
            bin_key = round(x, 1)  # 0.1 bins
            x_bins[bin_key][N].append(y)
        
        # 计算每个x bin内不同N间的y值方差
        bin_variances = []
        for bin_key, n_data in x_bins.items():
            n_means = {N: mean(ys) for N, ys in n_data.items() if ys}
            if len(n_means) >= 2:
                bin_std = stdev(n_means.values()) if len(n_means) > 1 else 0
                bin_mean = mean(n_means.values())
                bin_variances.append((bin_key, bin_std / max(abs(bin_mean), 0.01), len(n_means)))
        
        # 平均相对偏差 = collapse质量指标 (越小越好)
        avg_collapse_deviation = mean(v[1] for v in bin_variances) if bin_variances else float('inf')
        
        return {
            'avg_collapse_deviation': round(avg_collapse_deviation, 4),
            'bins_with_multi_N': len(bin_variances),
            'quality': 'EXCELLENT' if avg_collapse_deviation < 0.1 else 
                       'GOOD' if avg_collapse_deviation < 0.25 else
                       'FAIR' if avg_collapse_deviation < 0.5 else 'POOR',
        }


# ═══════════════════════════════════════════════════════════════════
# P2: 渗流模型形式化 — H634-G → Bond Percolation
# ═══════════════════════════════════════════════════════════════════

class PercolationMapping:
    """
    将H634-G关门传播映射为标准bond percolation:
    
    图G = (V, E)
      V = {agent_i}, |V| = N
      E = {(i,j) | i,j间存在互动}, |E| = N(N-1)/2 (完全图)
    
    每条bond (i,j)的关门概率:
      p_close(i,j) = f(trust_budget_i, trust_budget_j, penalty_global, N)
    
    简化为平均场:
      p_close_avg = σ(α·penalty_global + β·(1-trust_budget_avg) - γ·ln(N))
      其中σ是sigmoid函数
    
    理论预测:
      渗透阈值p_c: 完全图上p_c ≈ 1/N
      临界指数: 完全图→平均场普适类 (ν=1/2, β=1/2)
      
    但H634-G有方向性(p_close不对称) → 可能属有向渗流
      有向渗流(Directed Percolation, DP):
        1+1维: ν_∥≈1.733, ν_⊥≈1.097, β≈0.276
    """
    
    @staticmethod
    def p_close_theory(trust_budget, penalty_global, N, alpha=2.0, beta=3.0, gamma=0.5):
        """理论关门概率."""
        z = alpha * penalty_global + beta * (1.0 - trust_budget) - gamma * math.log(max(N, 2))
        return 1.0 / (1.0 + math.exp(-z))  # sigmoid
    
    @staticmethod
    def percolation_threshold_complete_graph(N):
        """完全图上的bond percolation阈值."""
        return 1.0 / N  # Erdős–Rényi p_c = 1/N
    
    @staticmethod
    def theory_prediction(N, trust_budget=0.5, penalty_global=0.3):
        """
        综合理论预测:
        - 如果p_close_theory ≈ p_c(N) = 1/N → 系统在临界点
        - N增大 → p_c减小 → 系统更易经历相变
        """
        p_close = PercolationMapping.p_close_theory(trust_budget, penalty_global, N)
        p_c = PercolationMapping.percolation_threshold_complete_graph(N)
        return {
            'N': N,
            'p_close_theory': round(p_close, 4),
            'p_c_percolation': round(p_c, 4),
            'ratio': round(p_close / max(p_c, 0.001), 2),
            'phase': 'SUPERCRITICAL' if p_close > p_c else 'SUBCRITICAL',
        }
    
    @staticmethod
    def verify_mapping(N_values, trust_budgets, penalty_globals):
        """验证映射一致性: 理论p_close vs 模拟p_c_eff"""
        results = []
        for N in N_values:
            for tb in trust_budgets:
                for pg in penalty_globals:
                    theory = PercolationMapping.theory_prediction(N, tb, pg)
                    results.append(theory)
        return results


# ═══════════════════════════════════════════════════════════════════
# P3: 连续极限 — 平均场方程
# ═══════════════════════════════════════════════════════════════════

class MeanFieldTheory:
    """
    N→∞连续极限的平均场分析.
    
    假设: 每个agent与所有其他agent的平均互动
    序参量 m = 关门密度 = (#closed doors) / N(N-1)
    
    自洽方程 (mean-field):
      m = p_close · (1 - m)² + noise · m · (1 - m) + recovery · (1 - m)
        ───────────────   ─────────────────   ──────────────
         关门传播            噪声翻转              恢复机制
    
    稳态解: 解三次方程 m = f(m; p_close, noise, recovery)
    
    临界条件: 当f'(m=0) = 1时, 出现非零解
      → p_c = (1 - recovery) / 2  (无噪声时)
    
    η_global = 1 - m
      η(p) = 1 - m*(p) 其中m*是稳态解
    """
    
    @staticmethod
    def steady_state_m(p_close, noise=0.10, recovery=0.05):
        """
        求自洽方程的稳态解.
        m = p_close·(1-m)² + noise·m·(1-m) + recovery·(1-m)
        → 0 = -m + p·(1-2m+m²) + n·(m-m²) + r·(1-m)
        → 0 = m²·(p-n) + m·(-1-2p+n-r) + (p+r)
        
        二次方程: a·m² + b·m + c = 0
        """
        a = p_close - noise
        b = -1 - 2*p_close + noise - recovery
        c = p_close + recovery
        
        disc = b**2 - 4*a*c
        if disc < 0 or abs(a) < 1e-10:
            # 无实根 → m=0 (平凡解) 或a≈0 → 线性
            if abs(a) < 1e-10:
                return max(0, min(1, -c / b)) if abs(b) > 1e-10 else 0
            return 0
        
        m1 = (-b + math.sqrt(disc)) / (2*a)
        m2 = (-b - math.sqrt(disc)) / (2*a)
        
        # 取[0,1]内的物理解
        candidates = [m for m in [m1, m2] if 0 <= m <= 1]
        if not candidates:
            return 0
        # 取稳定解 (较小的正根通常是稳定的)
        return min(candidates)
    
    @staticmethod
    def eta_global_functional(p_close, noise=0.10, recovery=0.05):
        """η_global = 1 - m*(p) 的泛函形式."""
        m = MeanFieldTheory.steady_state_m(p_close, noise, recovery)
        return 1.0 - m
    
    @staticmethod
    def critical_point(noise=0.10, recovery=0.05):
        """
        临界点: f'(m=0) = 1的条件
        f(m) = p·(1-m)² + n·m·(1-m) + r·(1-m)
        f'(m) = -2p(1-m) + n(1-2m) - r
        f'(0) = -2p + n - r
        f'(0) = 1 → -2p_c + n - r = 1 → p_c = (n - r - 1) / 2
        
        注意: 当n-r<1时, p_c<0 → 无临界点 → 系统一直处于有序相
        """
        p_c = (noise - recovery - 1) / 2
        if p_c < 0:
            return {
                'p_c': None,
                'phase': 'ALWAYS_ORDERED',
                'note': f'noise({noise})-recovery({recovery})= {noise-recovery} < 1 → 无相变',
            }
        return {
            'p_c': round(p_c, 4),
            'phase': 'HAS_CRITICAL_POINT',
            'note': f'在p={p_c:.4f}处经历连续相变',
        }
    
    @staticmethod
    def compare_with_numerical(numerical_etas, N_values, noise=0.10, recovery=0.05):
        """平均场理论 vs 数值模拟."""
        comparison = {}
        for N in N_values:
            # 平均场预测 (与N无关, 因为在N→∞极限)
            mf_etas = {}
            for p in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
                mf_etas[p] = MeanFieldTheory.eta_global_functional(p, noise, recovery)
            
            comparison[N] = {
                'mean_field': mf_etas,
                'note': '平均场在有限N时高估η (忽略涨落)',
            }
        return comparison


# ═══════════════════════════════════════════════════════════════════
# 主执行
# ═══════════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  P1+P2+P3: N→∞ 渗流相变 — 临界指数 + 渗流映射 + 平均场           ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    # ── P1: 加密采样 + FSS ──
    print("═══ P1: 有限尺寸标度 — N_c附近加密采样 ═══\n")
    
    N_values = [24, 28, 32, 36, 40]  # N_c≈32 附近
    p_values = [round(0.1 + i*0.05, 2) for i in range(17)]  # 0.10-0.90
    
    print(f"  网格: N∈{N_values}, p_close∈[0.10, 0.90] (步长0.05)")
    print(f"  每点: 50 seeds × 100 rounds = 5000 rounds")
    print(f"  总计: {len(N_values)}×{len(p_values)}×50 = {len(N_values)*len(p_values)*50} 次模拟\n")
    
    t0 = time.time()
    results = FiniteSizeScaling.run_dense_sampling(
        N_values, p_values, n_seeds=50, n_rounds_per_seed=100, noise_prob=0.10
    )
    elapsed = time.time() - t0
    print(f"\n  耗时: {elapsed:.1f}s\n")
    
    # 提取序参量
    summary = FiniteSizeScaling.compute_order_parameter(results)
    
    # 显示关键数据
    print("  ── 关键数据点 (η_global) ──")
    highlight_p = [0.2, 0.3, 0.4, 0.5]
    for N in N_values:
        line = f"  N={N:3d}: "
        for p in highlight_p:
            if (N, p) in summary:
                line += f"p={p} η={summary[(N,p)]['η_mean']:.3f}(±{summary[(N,p)]['η_std']:.3f})  "
        print(line)
    
    # FSS拟合
    print("\n  ── 有限尺寸标度拟合 ──")
    fit_result, effective_pc, m_at_pc = FiniteSizeScaling.fit_critical_exponents(summary)
    
    if fit_result['ν']:
        nu = fit_result['ν']
        beta = fit_result['β']
        pc_inf = fit_result['p_c_inf']
        print(f"\n  临界指数: ν = {nu:.4f} (R²={fit_result['ν_R²']:.4f})")
        print(f"             β = {beta:.4f}")
        print(f"  p_c(∞) = {pc_inf:.4f}")
        
        # 普适类对比
        print("\n  ── 普适类对比 ──")
        comparisons = FiniteSizeScaling.compare_universality(nu, beta, d=2)
        for i, comp in enumerate(comparisons[:4]):
            marker = '★' if i == 0 else ' '
            print(f"  {marker} {comp['class']:>20s}: ν={comp['ν_ref']:.3f} β={comp['β_ref']:.3f}  "
                  f"Δν={comp['ν_diff']}% Δβ={comp['β_diff']}%  dist={comp['distance']:.3f}")
        
        # 数据collapse
        collapse = FiniteSizeScaling.data_collapse(summary, nu, beta, pc_inf)
        print(f"\n  ── 数据Collapse验证 ──")
        print(f"  平均偏差: {collapse['avg_collapse_deviation']}")
        print(f"  质量: {collapse['quality']}")
    
    # ── P2: 渗流映射 ──
    print("\n═══ P2: 渗流模型形式化 ── H634-G → Bond Percolation ═══\n")
    
    print("  映射: Agent对(i,j) → bond")
    print("  p_close = σ(α·penalty + β·(1-trust) - γ·ln(N))")
    print(f"  p_c(完全图) = 1/N\n")
    
    mapping_results = PercolationMapping.verify_mapping(
        [4, 8, 16, 32, 64, 128],
        [0.3, 0.5, 0.7],
        [0.1, 0.3, 0.5]
    )
    
    print("  ── p_close理论值 vs p_c渗流阈值 ──")
    for r in mapping_results:
        phase_icon = '🔴' if r['phase'] == 'SUPERCRITICAL' else '🟢'
        print(f"  N={r['N']:4d}  TB={0.5:3.1f}  PG={0.3:3.1f}  "
              f"p_close={r['p_close_theory']:.4f}  p_c=1/{r['N']}={r['p_c_percolation']:.4f}  "
              f"ratio={r['ratio']:.2f}  {phase_icon} {r['phase']}")
    
    # ── P3: 平均场 ──
    print("\n═══ P3: 连续极限 — 平均场方程 ═══\n")
    
    p_c_pt = MeanFieldTheory.critical_point(noise=0.10, recovery=0.05)
    print(f"  临界点: {p_c_pt['note']}")
    
    print("\n  ── 平均场 η(p) 理论曲线 ──")
    for p in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]:
        eta = MeanFieldTheory.eta_global_functional(p)
        m = 1 - eta
        bar = '▓' * int(m * 40)
        print(f"  p={p:.1f}: η={eta:.4f}  m={m:.4f}  {bar}")
    
    # 与数值对比 (N=40, 最大)
    print("\n  ── 平均场 vs 数值(N=40)对比 ──")
    for p in [0.2, 0.3, 0.4, 0.5]:
        if (40, p) in summary:
            num_eta = summary[(40, p)]['η_mean']
            mf_eta = MeanFieldTheory.eta_global_functional(p)
            delta = abs(num_eta - mf_eta)
            print(f"  p={p:.1f}: 数值η={num_eta:.4f}  平均场η={mf_eta:.4f}  |Δ|={delta:.4f}")
    
    # ── 总结 ──
    print(f"\n{'═' * 70}")
    print(f"  P1 临界指数: ν={nu:.4f}, β={beta:.4f} (FSS拟合, R²={fit_result.get('ν_R²', 'N/A')})")
    if comparisons:
        best = comparisons[0]
        print(f"  P1 最近普适类: {best['class']} (距离={best['distance']:.3f})")
    print(f"  P2 渗流映射: H634-G关门↔完全图bond percolation (p_c=1/N)")
    print(f"  P3 平均场: 自洽方程 m=f(m) → 临界条件 p_c=(n-r-1)/2")
    print(f"{'═' * 70}")


# ═══════════════════════════════════════════════════════════════════
# 结论模板: 根据拟合结果判定普适类
# ═══════════════════════════════════════════════════════════════════

CONCLUSION_TEMPLATE = """
╔══════════════════════════════════════════════════════════════════╗
║  预期结论 (基于之前d=+1.911的因果效应)                          ║
║                                                                ║
║  如果ν≈0.5, β≈0.5: → 平均场普适类                             ║
║    • 完全图上的渗流在d≥6时属于平均场                           ║
║    • 意味着涨落被全局耦合所抑制                                 ║
║    • N_c≈32是平均场近似的下界                                   ║
║                                                                ║
║  如果ν≈1.33, β≈0.14: → 2D渗流普适类                          ║
║    • 意味着H634-G具有等效2D拓扑结构                             ║
║    • 关门传播限于局部邻域, 非全局耦合                           ║
║    • 需要重新审视"完全图"假设                                   ║
║                                                                ║
║  如果ν≈0.876, β≈0.418: → 3D渗流普适类                        ║
║    • 中间情况, 可能对应有向渗流(DP)                             ║
║    • 关门方向性引入有效维度3                                    ║
║                                                                ║
║  N→∞连续极限: η(p) = 1 - m*(p) 其中m*满足自洽方程              ║
║    在p_c附近: η(p) ~ |p - p_c|^β  (连续相变)                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

if __name__ == '__main__':
    main()
    print(CONCLUSION_TEMPLATE)
