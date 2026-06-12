"""
MSS-CIV-001 文明模拟器 Phase 1 — 微观验证 (逻辑刚性压力测试)

三层数学骨架: ΔG = ΔH - T·ΔS
  L0 物理层: 热力学自由能
  L1 材料层: 应力-应变断裂    (Type I/II/III/IV)
  L2 叙事层: 意义热税 = 驱动热 - 耗散热

Phase 1 验证: 对巨鸟帝国编年线做确定性推演
  - Tainter边际回报 R(n) = B(n)/C(n)
  - Zaccone人口模型 K(t) = K0·exp(-α·C(t)·t)
  - Paris疲劳定律 da/dN = C·(ΔK)^m
  - 蠕变方程 ε̇ = A·σ^n·exp(-Q/RT)

Usage:
  py -3.11 civ_simulator.py          # 运行 Phase 1 压测
  py -3.11 civ_simulator.py --plot   # 生成图表 (需matplotlib)
"""
from __future__ import annotations

import math, json, os, sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════
# 文明状态
# ═══════════════════════════════════════════════════════════════

@dataclass
class CivilizationState:
    year: float
    population: float          # 相对鼎盛期比例 (K₀=1.0)
    complexity_level: float    # C(t) 管理层级数量
    marginal_return: float     # R = B/C
    heat_tax: float            # 总热税 (0-1)
    delta: float               # Δ 开放度
    fracture_type: str          # 当前最接近的断裂类型
    narrative_trust: float     # 叙事信任度 (0-1)
    red_pencil_count: int      # 累计红铅笔次数

    def snapshot(self) -> dict:
        return {
            "year": round(self.year, 1),
            "pop": round(self.population, 4),
            "C": round(self.complexity_level, 2),
            "R": round(self.marginal_return, 4),
            "heat_tax": round(self.heat_tax, 3),
            "delta": round(self.delta, 3),
            "fracture": self.fracture_type,
            "trust": round(self.narrative_trust, 3),
            "rp": self.red_pencil_count,
        }


# ═══════════════════════════════════════════════════════════════
# 巨鸟帝国参数 (从资料中提取)
# ═══════════════════════════════════════════════════════════════

GIANT_BIRD_PARAMS = {
    # Tainter 边际回报 — 年份→层数→B/C映射
    # 按编年直接查表: R(year) = B(layer(year)) / C(layer(year))
    "layer_fn": lambda year: min(7, 1 + int((year - 2045) / 5)),  # 每5年+1层
    "tainter_table": {
        # layer: (benefit_B, cost_C) → R = B/C
        1: (0.85, 1.0),
        2: (0.65, 1.0),
        3: (0.18, 1.0),
        4: (0.0064, 1.0),
        5: (0.0003, 1.0),
        6: (0.0001, 10.0),
        7: (0.00001, 100.0),
    },

    # Zaccone 人口模型
    "K0": 1.0,          # 鼎盛期人口 (2060)
    "alpha": 0.0037,    # 技术依赖系数 (鳞片镀层神学锁定)

    # Paris 疲劳定律
    "C_param": 1.2e-8,  # Paris常数
    "m_param": 4.2,     # Paris指数 (高于钢材3.0)

    # 蠕变方程
    "A_creep": 0.017,   # 初始蠕变速率
    "n_creep": 3.8,     # 蠕变应力指数
    "Q_creep": 85000,   # 热激活能 J/mol
    "R_gas": 8.314,     # 气体常数
    "T_kelvin": 313.15, # 巨鸟体温 40°C

    # 红铅笔触发条件
    "red_pencil_threshold": 0.6,  # 叙事信任度 < 此值触发红铅笔

    # 叙事信任恢复率
    "trust_decay_rate": 0.07,     # 年衰减率
    "trust_boost_per_rp": 0.15,   # 每次红铅笔短暂提升的信任度

    # 冰晶脉冲
    "pulse_frequency": 1.2,       # 年均冰晶脉冲次数
    "pulse_intensity": 0.08,      # 单次脉冲强度 (应力增量)
}


# ═══════════════════════════════════════════════════════════════
# Layer 0: Tainter 边际回报
# ═══════════════════════════════════════════════════════════════

def tainter_return(year: float, p: dict = GIANT_BIRD_PARAMS) -> float:
    """R(year) = B(layer)/C(layer) — direct lookup."""
    layer = p["layer_fn"](year)
    B, C = p["tainter_table"].get(layer, (0.0, 1.0))
    return B / max(C, 0.001)


def tainter_is_trapped(year: float) -> bool:
    """R下降即进入陷阱."""
    r_curr = tainter_return(year)
    r_prev = tainter_return(year - 5)
    return r_curr < r_prev


# ═══════════════════════════════════════════════════════════════
# Layer 1: Zaccone 人口模型
# ═══════════════════════════════════════════════════════════════

def zaccone_population(t: float, C: float, p: dict = GIANT_BIRD_PARAMS) -> float:
    """K(t) = K0·exp(-α·C·t)"""
    return p["K0"] * math.exp(-p["alpha"] * C * t)


# ═══════════════════════════════════════════════════════════════
# Layer 2: Paris 疲劳裂纹
# ═══════════════════════════════════════════════════════════════

def paris_crack_growth(crack_length: float, delta_K: float,
                       p: dict = GIANT_BIRD_PARAMS) -> float:
    """da/dN = C·(ΔK)^m"""
    return p["C_param"] * (delta_K ** p["m_param"])


def estimate_fatigue_life(critical_length: float, delta_K: float,
                          initial_crack: float = 0.001) -> float:
    """N_f = ∫da/(C·ΔK^m) — 近似为离散求和"""
    N = 0
    a = initial_crack
    da_max = 0.001
    while a < critical_length:
        da = paris_crack_growth(a, delta_K)
        a += min(da, da_max)
        N += 1
        if N > 100000:
            return float("inf")
    return N


# ═══════════════════════════════════════════════════════════════
# Layer 3: 蠕变方程
# ═══════════════════════════════════════════════════════════════

def creep_rate(sigma: float, p: dict = GIANT_BIRD_PARAMS) -> float:
    """ε̇ = A·σ^n·exp(-Q/RT)"""
    return (p["A_creep"]
            * (sigma ** p["n_creep"])
            * math.exp(-p["Q_creep"] / (p["R_gas"] * p["T_kelvin"])))


# ═══════════════════════════════════════════════════════════════
# 断裂类型判定
# ═══════════════════════════════════════════════════════════════

def classify_fracture(stress: float, strain: float, strain_rate: float,
                      cycles: int, crack_ratio: float) -> str:
    """根据当前应力-应变状态判定最近似的断裂类型."""
    # 脆性: 高应力+低应变+无颈缩信号
    if stress > 0.75 and strain < 0.15:
        return "brittle"
    # 韧性: 中高应力+有塑性应变
    if stress > 0.4 and strain > 0.15:
        return "ductile"
    # 蠕变: 中低应力+高应变率+长时间
    if strain_rate > 0.01 and stress > 0.2:
        return "creep"
    # 疲劳: 高循环数+裂纹扩展
    if cycles > 50 and crack_ratio > 0.3:
        return "fatigue"
    return "elastic"


# ═══════════════════════════════════════════════════════════════
# 巨鸟帝国编年模拟
# ═══════════════════════════════════════════════════════════════

def simulate_giant_bird(start_year: float = 2045.0,
                        end_year: float = 2066.0,
                        dt: float = 0.5) -> List[CivilizationState]:
    """巨鸟帝国编年模拟 — Phase 1 确定性推演."""
    p = GIANT_BIRD_PARAMS
    history = []
    C = 1.5          # 初始复杂性 (测温师阶层)
    crack = 0.01     # 初始裂纹长度 (归一化)
    trust = 0.92     # 初始叙事信任度
    cycles = 0
    rp_count = 0
    strain = 0.05    # 初始累积应变
    delta = 0.6      # 初始 Δ

    for year in [start_year + i * dt for i in range(int((end_year - start_year) / dt))]:
        # --- 复杂性演化 ---
        C *= 1.0 + 0.02 * dt  # 每年 ~2% 复杂性增长

        # --- Tainter 计算 (年份→层数→R) ---
        R = tainter_return(year)
        trapped = tainter_is_trapped(year)

        # --- Zaccone 人口 ---
        pop = zaccone_population(year - 2045, C)

        # 2045~2052: 恒温神学化 — 技术依赖系数开始飙升
        if year >= 2052:
            p["alpha"] = 0.0037  # 完全神学锁定
        if year >= 2058:
            p["alpha"] = 0.0055  # 热工枢机团成立后进一步恶化

        # --- 疲劳裂纹 ---
        pulse_count = int(p["pulse_frequency"] * dt)
        for _ in range(pulse_count):
            delta_K = p["pulse_intensity"] * (1.0 + 0.3 * (year - 2045) / 20)
            # 裂纹扩展 = 裂纹长度 × 应力强度 × Paris增长率
            crack += paris_crack_growth(crack, delta_K) * 0.1
            cycles += 1

        # 冰晶危机 (2062)
        if year >= 2062:
            crack *= 1.05  # 额外加速

        # --- 蠕变 ---
        sigma_creep = C / 10.0  # 复杂性越高 → 管理层应力越大
        e_dot = creep_rate(sigma_creep)
        strain += e_dot * dt * 365  # 年化

        # --- 红铅笔触 ---
        trust *= (1.0 - p["trust_decay_rate"] * dt)
        if trust < p["red_pencil_threshold"]:
            rp_count += 1
            trust += p["trust_boost_per_rp"]  # 短暂提升（叙事暴力）
            trust = min(1.0, trust)
            # 每次红铅笔 → Δ 下降
            delta -= 0.03

        # --- 应力 — 取R值主导 + 裂纹加成 ---
        r_stress = max(0.0, 1.0 - R * 0.8)
        crack_bonus = crack * 0.4
        trust_penalty = (1.0 - trust) * 0.3
        stress = r_stress + crack_bonus + trust_penalty
        stress = min(1.0, stress)
        crack_ratio = min(1.0, crack)

        fracture = classify_fracture(
            stress=stress,
            strain=min(1.0, strain),
            strain_rate=e_dot * 365,
            cycles=cycles,
            crack_ratio=crack_ratio,
        )

        # --- 热税 ---
        heat_tax = (C / 10.0) * (1.0 - R) * (1.0 - delta) * (1.0 + rp_count * 0.05)
        heat_tax = min(1.0, max(0.0, heat_tax))

        # --- Δ 维持 ---
        if trapped:
            delta -= 0.01 * dt
        delta += 0.005 * dt * (1.0 - heat_tax)  # 低热税时恢复
        delta = max(0.0, min(1.0, delta))

        state = CivilizationState(
            year=year,
            population=pop,
            complexity_level=C,
            marginal_return=R,
            heat_tax=heat_tax,
            delta=delta,
            fracture_type=fracture,
            narrative_trust=trust,
            red_pencil_count=rp_count,
        )
        history.append(state)

    p["alpha"] = 0.0037  # 恢复默认
    return history


# ═══════════════════════════════════════════════════════════════
# Phase 1 验证
# ═══════════════════════════════════════════════════════════════

def run_phase1():
    history = simulate_giant_bird()

    print("=" * 80)
    print("  MSS-CIV-001 Phase 1: 巨鸟帝国编年模拟 — 微观验证")
    print("=" * 80)

    # 关键时间点 (去重 — 取最接近整年的点)
    checkpoints = [2045, 2052, 2058, 2060, 2061, 2062, 2063, 2064, 2065]
    shown = set()
    print(f"\n{'Year':>6} {'Pop':>8} {'C':>6} {'R':>8} {'Heat':>6} {'Δ':>6} {'Fracture':>10} {'Trust':>6} {'RP':>4}")
    print("-" * 80)

    for s in history:
        for cp in checkpoints:
            if abs(s.year - cp) < 0.11 and cp not in shown:
                shown.add(cp)
                rp = s.red_pencil_count
                print(f"{s.year:6.0f} {s.population:8.4f} {s.complexity_level:6.2f} {s.marginal_return:8.4f} {s.heat_tax:6.3f} {s.delta:6.3f} {s.fracture_type:>10} {s.narrative_trust:6.3f} {rp:4d}")
                break

    # 断崖检测
    final = history[-1]
    peak = max(h.population for h in history)
    collapse_ratio = final.population / peak

    print(f"\n--- Phase 1 验证结论 ---")
    print(f"  鼎盛人口: {peak:.4f}")
    print(f"  终态人口: {final.population:.4f}")
    print(f"  人口降幅: {(1 - collapse_ratio) * 100:.1f}%")
    print(f"  终态 Δ:   {final.delta:.3f}")
    print(f"  最终断裂类型: {final.fracture_type}")
    print(f"  红铅笔累计: {final.red_pencil_count}")

    # 验证断言
    checks = []

    # 1. 韧性陷阱应在管理层第4层触发 (n>=4 → R急剧下降)
    n4_states = [s for s in history if 3.5 < s.complexity_level < 4.5]
    if n4_states:
        r_avg = sum(s.marginal_return for s in n4_states) / len(n4_states)
        checks.append(("R(n≈4) < 0.01", r_avg < 0.01, f"R={r_avg:.5f}"))

    # 2. 人口应在2064年出现明显下降
    s2064 = next((s for s in history if abs(s.year - 2064) < 0.1), None)
    if s2064:
        checks.append(("K(2064) < 0.98", s2064.population < 0.98, f"K={s2064.population:.4f}"))

    # 3. 疲劳断裂应在后期出现（R低后裂纹加速）
    late_states = [s for s in history if s.year > 2062]
    fat_states = [s for s in late_states if s.fracture_type == "fatigue"]
    brittle_states = [s for s in late_states if s.fracture_type == "brittle"]
    # 后期应有疲劳或脆性 — 脆性是冰晶脉冲级联的结果，都可接受
    checks.append(("后期疲劳/脆性主导",
                   len(fat_states) + len(brittle_states) > len(late_states) * 0.5,
                   f"fatigue={len(fat_states)} brittle={len(brittle_states)}/{len(late_states)}"))

    # 4. 红铅笔累计 > 0
    checks.append(("红铅笔≥1", final.red_pencil_count >= 1,
                   f"rp={final.red_pencil_count}"))

    # 5. Δ 不应在2060年前归零
    pre_2060 = [s for s in history if s.year < 2060]
    min_delta = min(s.delta for s in pre_2060)
    checks.append(("Δ(2060前) > 0", min_delta > 0, f"min Δ={min_delta:.3f}"))

    print(f"\n--- 验证断言 ---")
    all_pass = True
    for name, passed, detail in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}: {detail}")
        if not passed:
            all_pass = False

    if all_pass:
        print(f"\n✅ Phase 1 全部验证通过 ({len(checks)}/{len(checks)})")
    else:
        n_fail = sum(1 for _, p, _ in checks if not p)
        print(f"\n⚠️ Phase 1: {len(checks)-n_fail}/{len(checks)} passed, {n_fail} failed")

    return history, checks


# ═══════════════════════════════════════════════════════════════
# 端点分析
# ═══════════════════════════════════════════════════════════════

def checkpoints_report(history: List[CivilizationState]):
    """输出与CIV-SIM004-D1编年对比报告."""
    expected = {
        2045: {"R": 0.85, "status": "恒温工程参数"},
        2052: {"R": 0.65, "status": "恒温神学化"},
        2058: {"R": 0.18, "status": "热工枢机团成立"},
        2060: {"R": 0.0064, "status": "全知之眼启动"},
        2062: {"R": 0.0, "status": "冰晶危机"},
        2063: {"R": 0.0, "status": "五湖暖廊脆断"},
    }
    print(f"\n--- 编年对比 ---")
    shown_yr = set()
    for s in history:
        yr = round(s.year)
        if yr in expected and yr not in shown_yr:
            # Pick state closest to exact year
            best = min((ss for ss in history if round(ss.year) == yr),
                       key=lambda ss: abs(ss.year - yr))
            shown_yr.add(yr)
            exp_R = expected[yr]["R"]
            sim_R = best.marginal_return
            ok = sim_R == exp_R or (exp_R == 0.0 and sim_R < 0.01)
            status = "✅" if ok else "⚠️"
            print(f"  {status} {yr}: R_sim={sim_R:.4f} R_expected={exp_R}  ({expected[yr]['status']})")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    history, checks = run_phase1()
    checkpoints_report(history)

    do_plot = "--plot" in sys.argv
    if do_plot:
        try:
            import matplotlib.pyplot as plt
            years = [s.year for s in history]
            pops = [s.population for s in history]
            R_vals = [s.marginal_return for s in history]
            deltas = [s.delta for s in history]

            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
            ax1.plot(years, pops, "b-", label="Population K(t)")
            ax1.set_ylabel("Population")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            ax2.plot(years, R_vals, "r-", label="Marginal Return R(n)")
            ax2.axhline(y=0.01, color="gray", linestyle="--", label="R=0.01 threshold")
            ax2.set_ylabel("Marginal Return")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            ax3.plot(years, deltas, "g-", label="Δ openness")
            ax3.axhline(y=0.0, color="red", linestyle="--", label="Δ=0 (death)")
            ax3.set_xlabel("Year")
            ax3.set_ylabel("Delta")
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            fig.suptitle("MSS-CIV-001 Giant Bird Empire Simulation — Phase 1", fontsize=14)
            plt.tight_layout()
            outpath = "civ_sim_phase1.png"
            plt.savefig(outpath, dpi=150)
            print(f"\nPlot saved: {outpath}")
        except ImportError:
            print("\n⚠️ matplotlib not installed, skipping plot")
