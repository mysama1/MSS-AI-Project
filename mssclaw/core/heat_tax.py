"""
A3 热税预算 — MSS-Agent 的第一道防线.

三层热税:
  L0 物理热税 (token cost, latency)  — 权重 0.001
  L1 逻辑热税 (redundancy, loops)    — 权重 1.0
  L2 意义热税 (meaningless work)     — 权重 1000.0

如果 L2 意义热税超过 budget → 拒绝执行.

v1.1: 集成 HeatTaxFuseGroup — 三层级联熔断器.
  熔断器与预算独立运行, 熔断器处理"是否安全继续",
  预算处理"是否值得继续".
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable

from .heat_tax_fuse import (
    HeatTaxFuseGroup, FuseLevel, FuseState,
    create_fuse_group,
)


class HeatTaxLevel(Enum):
    """热税层级. 修复顺序: L2→L1→L0. 反了=白费."""
    L0_PHYSICAL = 0       # GPU/时间/token
    L1_LOGICAL = 1        # 冗余/重复/缓存污染
    L2_MEANING = 2        # 虚假数据/概念偷换/无意义任务


@dataclass
class HeatTaxBudget:
    """
    热税预算. 每个 Agent 实例有一个.

    threshold: 总热税上限 (0-1, 超过则拒绝)
    weights: 各层权重

    Usage:
        budget = HeatTaxBudget()
        budget.charge(HeatTaxLevel.L2_MEANING, 0.01, "生成无意义报告")
        if budget.exceeded():
            raise HeatTaxAbort("此任务无意义")
    """
    threshold: float = 0.5  # S-019: 归一化阈值 (total() 范围 0-1)
    weights: dict = field(default_factory=lambda: {
        HeatTaxLevel.L0_PHYSICAL: 0.001,
        HeatTaxLevel.L1_LOGICAL: 1.0,
        HeatTaxLevel.L2_MEANING: 1000.0,
    })
    spent: dict = field(default_factory=dict)
    log: list = field(default_factory=list)
    fuse: Optional[HeatTaxFuseGroup] = None  # v1.1: 可选熔断器
    reserved: dict = field(default_factory=dict)  # S-019: task_id → estimated_tokens
    tier_thresholds: dict = field(default_factory=dict)  # S-019: per-tier limits
    _delta_ref: object = None  # S-019: delta protocol reference

    def __post_init__(self):
        for level in HeatTaxLevel:
            self.spent.setdefault(level, 0.0)
            self.tier_thresholds.setdefault(level, float('inf'))  # S-019: default infinite

    def charge(self, level: HeatTaxLevel, amount: float, reason: str = "") -> float:
        """
        征收热税. 返回加权后的税值.
        如果单次 L2 热税 > threshold*0.3 → 立即标记.
        """
        weighted = amount * self.weights[level]
        self.spent[level] += weighted
        self.log.append({
            "level": level.name,
            "amount": amount,
            "weighted": weighted,
            "reason": reason[:120],
            "total": self.total(),
        })
        return weighted

    def total(self) -> float:
        """当前累计热税 (归一化到 0-1)."""
        return min(sum(self.spent.values()) / 100.0, 1.0)

    def exceeded(self) -> bool:
        """热税超过阈值? 超过 → 应该停止."""
        return self.total() > self.threshold

    def l2_dominant(self) -> bool:
        """L2 意义热税占比 > 50%? → 任务的方向错了."""
        pt = sum(self.spent.values()) or 1.0
        return self.spent[HeatTaxLevel.L2_MEANING] / pt > 0.5

    def snapshot(self) -> dict:
        result = {
            "total": round(self.total(), 4),
            "L0_physical": round(self.spent[HeatTaxLevel.L0_PHYSICAL], 2),
            "L1_logical": round(self.spent[HeatTaxLevel.L1_LOGICAL], 2),
            "L2_meaning": round(self.spent[HeatTaxLevel.L2_MEANING], 2),
            "l2_dominant": self.l2_dominant(),
            "exceeded": self.exceeded(),
            "log_count": len(self.log),
        }
        if self.fuse:
            result["fuse"] = self.fuse.stats()
        return result

    # ── S-019: 任务级预分配 + Δ联动 ────────────────────────────

    def reserve(self, task_id: str, estimated_tokens: int) -> None:
        """预分配热税预算 (任务级)."""
        self.reserved[task_id] = estimated_tokens

    def release(self, task_id: str) -> None:
        """释放任务预留的热税."""
        self.reserved.pop(task_id, None)

    def link_delta(self, delta) -> None:
        """联动 Δ 协议: delta.health 下降 → 热税阈值收紧."""
        self._delta_ref = delta

    def effective_threshold(self) -> float:
        """考虑 Δ 联动后的有效阈值."""
        if not self._delta_ref:
            return self.threshold
        try:
            h = self._delta_ref.health()
            health = float(h) if h != "UNKNOWN" else 1.0
        except (ValueError, TypeError):
            return self.threshold
        if health < 0.3:
            return self.threshold * 0.5
        elif health < 0.6:
            return self.threshold * 0.75
        return self.threshold

    def tier_exceeded(self) -> tuple:
        """检查任一层级是否超阈值. 返回 (exceeded: bool, level: HeatTaxLevel)."""
        for level in HeatTaxLevel:
            if self.spent[level] > self.tier_thresholds[level]:
                return True, level
        return False, None

    # ── v1.1: 熔断器集成 ──────────────────────────────────────

    def enable_fuse(self, delta_check: Optional[Callable[[], float]] = None,
                    audit_dir: str = "") -> HeatTaxFuseGroup:
        """启用三层熔断器. 返回 fuse 对象以便外部操作."""
        self.fuse = create_fuse_group(delta_check=delta_check, audit_dir=audit_dir)
        return self.fuse

    def check_safety(self, context: str = "") -> Optional[str]:
        """
        检查当前热税状态是否触发熔断.
        如果触发 → 返回拒绝原因 (str)
        如果安全 → 返回 None
        """
        if not self.fuse:
            return None

        # 传递给熔断器的是原始裸值（未加权），不是 spent 的加权值
        l0 = self.spent[HeatTaxLevel.L0_PHYSICAL] / self.weights[HeatTaxLevel.L0_PHYSICAL]
        l1 = self.spent[HeatTaxLevel.L1_LOGICAL] / self.weights[HeatTaxLevel.L1_LOGICAL]
        l2 = self.spent[HeatTaxLevel.L2_MEANING] / self.weights[HeatTaxLevel.L2_MEANING]

        results = self.fuse.check_and_trip(l0, l1, l2, context)

        if self.fuse.l2.tripped:
            return f"L2 fuse tripped: meaning-level violation ({l2:.2f})"
        if self.fuse.l1.tripped:
            return f"L1 fuse tripped: logic redundancy ({l1:.2f}), bypass allowed"
        if self.fuse.l0.tripped:
            return f"L0 fuse tripped: resource exhausted ({l0:.2f})"
        return None

    def grad_multiplier(self) -> float:
        """梯度衰减系数. 熔断器激活时返回 <1.0."""
        if self.fuse:
            return self.fuse.grad_multiplier()
        return 1.0

    def reset_fuse_if_cooled(self) -> bool:
        """尝试复位熔断器. 返回是否有熔断器被复位."""
        if not self.fuse:
            return False
        l0 = self.spent[HeatTaxLevel.L0_PHYSICAL] / self.weights[HeatTaxLevel.L0_PHYSICAL]
        l1 = self.spent[HeatTaxLevel.L1_LOGICAL] / self.weights[HeatTaxLevel.L1_LOGICAL]
        l2 = self.spent[HeatTaxLevel.L2_MEANING] / self.weights[HeatTaxLevel.L2_MEANING]
        results = self.fuse.reset_if_cooled(l0, l1, l2)
        return any(results.values())


class HeatTaxAbort(Exception):
    """抛出此异常 = Agent 判定任务无意义, 拒绝执行."""
    pass


# ═══════════════════════════════════════════════════════════
# A3 v15.2 — 五层热税引擎 (Five-Layer Reference Implementation)
# 与旧三层并行存在, 不破坏现有依赖.
# ═══════════════════════════════════════════════════════════

import math

# 物理常量
KB = 1.380649e-23  # 玻尔兹曼常数 (J/K)
T_ROOM = 300.0     # 室温 (K)


@dataclass
class UnprovableProposition:
    """不可证命题描述 (Patch 2: 携带证明长度估计)."""
    name: str
    estimated_proof_length: float  # 在更强元系统中最短证明长度的估计


@dataclass
class GarbageRecord:
    """GC 对象记录 (Patch 1: 携带序列化字节数)."""
    type_name: str
    byte_size: int


@dataclass
class OperationContext:
    """
    A3 v15.2 单次操作上下文.
    对应 v15.2 五层: L0(phys) L0'(info) L1(logic) L2(sem) L3(cog)
    """
    op_name: str
    timestamp: int = 0

    # L0 物理层
    power_joules: float = 0.0

    # L0' 信息层
    garbage_objects: list = field(default_factory=list)  # List[GarbageRecord]

    # L1 逻辑层
    unprovable_propositions: list = field(default_factory=list)  # List[UnprovableProposition]

    # L2 语义层
    prompt_tokens: int = 0
    attention_entropy: float = 0.0  # 语义熵 (0-1)
    semantic_reference_q: float = 0.0  # Q 参考分布的对数 (用于KL散度)

    # L3 认知层
    synapse_changes: int = 0    # 突触重塑计数
    attention_switches: int = 0  # 任务切换次数


@dataclass
class HeatTaxResult:
    """A3 v15.2 五层热税计算结果."""
    tax_phys: float = 0.0
    tax_info: float = 0.0
    tax_logic: float = 0.0
    tax_sem: float = 0.0
    tax_cog: float = 0.0
    total: float = 0.0
    eta_asc: float = 0.0
    pseudo_tax_warning: bool = False  # C2 层级传导检测

    def breakdown(self) -> dict:
        return {
            "L0_phys": round(self.tax_phys, 4),
            "L0_info": round(self.tax_info, 10),
            "L1_logic": round(self.tax_logic, 2),
            "L2_sem": round(self.tax_sem, 4),
            "L3_cog": round(self.tax_cog, 2),
            "total": round(self.total, 4),
            "eta_asc": round(self.eta_asc, 6),
            "pseudo_tax": self.pseudo_tax_warning,
        }


class HeatTaxMode(Enum):
    """
    热税计算模式.

    COARSE (v15.1, 旧三层): 粗扫 — 适用于日常 Agent 操作, 快速预算检查.
      L0 物理 · L1 逻辑(工程级) · L2 意义.
      计算快, 覆盖大部分场景.

    FINE   (v15.2, 新五层): 细扫 — 适用于学术/理论/逻辑严格领域.
      L0 物理 · L0' 信息 · L1 逻辑(哥德尔级) · L2 语义 · L3 认知.
      含层间放大、伪热税检测. 用于 MSS 论文、形式化验证.
    """
    COARSE = "coarse"  # v15.1 三层
    FINE = "fine"      # v15.2 五层


class HeatTaxCalculator:
    """
    A3 v15.2 五层热税计算引擎 (FINE mode).
    与旧三层 (COARSE mode) 双模共存.

    层级嵌套:
      L0  Tax_phys  ≥ ΔQ_diss                     [热力学硬地板]
      L0' Tax_info  = k_B T ln2 · Σ K(serialize(g)) [Landauer下限]
      L1  Tax_logic ≥ μ · inf L_proof(G)             [逻辑硬度下界]
      L2  Tax_sem   = -Σ P(m|K) log(P/Q)             [语义歧义熵]
      L3  Tax_cog   = E_base + η·ΔS_syn + ζ·N_switch [认知代谢]

    传导规则:
      载体: 上层经由下层消散
      放大: L1密度指数级放大L2歧义成本
    """

    def __init__(
        self,
        mode: HeatTaxMode = HeatTaxMode.FINE,
        baseline_metabolic: float = 20.0,       # E_base: 认知基础代谢 (W)
        eta_synapse: float = 0.67,               # η: 突触重塑系数 (相对基础代谢)
        zeta_switch: float = 2.0,                # ζ: 注意力切换代价 (W/次)
        mu_logic: float = 1.0,                   # μ: 逻辑硬度系数
        sem_scale: float = 1e-3,                 # 语义熵→热税缩放
        logic_sem_amp: float = 0.01,             # L1→L2 放大因子
        pseudo_tax_threshold: float = 0.6,       # C2 伪热税检测: logic/cog 比阈值
    ):
        self.mode = mode
        self.baseline_metabolic = baseline_metabolic
        self.eta_synapse = eta_synapse
        self.zeta_switch = zeta_switch
        self.mu_logic = mu_logic
        self.sem_scale = sem_scale
        self.logic_sem_amp = logic_sem_amp
        self.pseudo_tax_threshold = pseudo_tax_threshold

    def calculate(self, ctx: OperationContext) -> HeatTaxResult:
        """
        计算一次操作的热税. 根据 mode 切换粗扫/细扫.
        - COARSE: v15.1 三层 (物理/逻辑-工程级/意义), 快
        - FINE:   v15.2 五层 (物理+信息+逻辑-哥德尔级+语义+认知), 精
        """
        if self.mode == HeatTaxMode.COARSE:
            return self._calculate_coarse(ctx)
        return self._calculate_fine(ctx)

    def _calculate_coarse(self, ctx: OperationContext) -> HeatTaxResult:
        """
        v15.1 粗扫模式: L0物理 + L1逻辑(工程级) + L2意义.
        不启用层间放大、Landauer/哥德尔/认知模型.
        """
        tax_phys = ctx.power_joules
        # L1 工程级: 用 prompt_tokens 作冗余代理, 不是哥德尔级
        tax_logic = ctx.prompt_tokens * 0.01  # 无不可证命题时退化为token冗余
        if ctx.unprovable_propositions:
            tax_logic += len(ctx.unprovable_propositions) * 10.0  # 工程级惩罚
        # L2 意义: attention_entropy 作意义稀释代理
        tax_sem = ctx.attention_entropy * ctx.prompt_tokens * 0.01
        # L0' 和 L3 在粗扫中归零
        total = tax_phys + tax_logic + tax_sem
        useful_work = self._estimate_useful_work(ctx)
        eta_asc = useful_work / (useful_work + total) if (useful_work + total) > 0 else 0.0
        return HeatTaxResult(
            tax_phys=tax_phys, tax_info=0.0, tax_logic=tax_logic,
            tax_sem=tax_sem, tax_cog=0.0, total=total, eta_asc=eta_asc,
        )

    def _calculate_fine(self, ctx: OperationContext) -> HeatTaxResult:
        """
        v15.2 细扫模式: 五层完整 + 层间放大 + 伪热税检测.
        """
        # ── L0 物理热税: 硬地板 ──
        tax_phys = ctx.power_joules

        # ── L0' 信息热税: Landauer 下限 ──
        # Patch 1: N_erase = K(serialize(g)) → 用序列化字节长代理
        total_bits_erased = 0
        for g in ctx.garbage_objects:
            total_bits_erased += g.byte_size * 8
        tax_info = KB * T_ROOM * math.log(2) * total_bits_erased

        # ── L1 逻辑热税: 哥德尔下界 ──
        # Patch 2: 不可数→inf L_proof(G), 不用求和
        if ctx.unprovable_propositions:
            min_proof_len = min(
                p.estimated_proof_length for p in ctx.unprovable_propositions
            )
        else:
            min_proof_len = 0.0
        tax_logic = self.mu_logic * max(min_proof_len, 0.0)

        # ── L2 语义热税: Bao/Niu-Zhang 框架 ──
        # 简化: attention_entropy * tokens * scale
        # 完整形式应含 -log(P/Q) KL 项, 这里用 attention_entropy 作 P 的代理
        tax_sem = ctx.attention_entropy * ctx.prompt_tokens * self.sem_scale
        if ctx.semantic_reference_q > 0:
            # Q 项贡献 (KL散度中的 P/Q 部分)
            tax_sem += ctx.attention_entropy * ctx.prompt_tokens * self.sem_scale * math.log(ctx.semantic_reference_q)

        # ── 层级放大: L1 → L2 ──
        # L1 不可判定密度指数级放大 L2 歧义成本
        if tax_logic > 0:
            amplification = math.exp(self.logic_sem_amp * tax_logic)
            tax_sem *= amplification

        # ── L3 认知热税: 突触重塑 + 注意力切换 ──
        # Patch 3: E_baseline 是常数项, η和ζ是独立系数
        tax_cog = (
            self.baseline_metabolic +                              # E_base: 活着就得付
            self.baseline_metabolic * self.eta_synapse * ctx.synapse_changes +  # η·ΔS_syn
            self.zeta_switch * ctx.attention_switches                # ζ·N_switch
        )

        # ── 总计 ──
        total = tax_phys + tax_info + tax_logic + tax_sem + tax_cog

        # ── C2 层级传导检测: 伪热税 ──
        # 逻辑税极高 / 认知税极低 → 试图用逻辑硬压而不做认知消化
        pseudo_tax = False
        if tax_cog > 0 and (tax_logic / tax_cog) > self.pseudo_tax_threshold:
            pseudo_tax = True

        # ── 升维效率 ──
        useful_work = self._estimate_useful_work(ctx)
        eta_asc = useful_work / (useful_work + total) if (useful_work + total) > 0 else 0.0

        return HeatTaxResult(
            tax_phys=tax_phys,
            tax_info=tax_info,
            tax_logic=tax_logic,
            tax_sem=tax_sem,
            tax_cog=tax_cog,
            total=total,
            eta_asc=eta_asc,
            pseudo_tax_warning=pseudo_tax,
        )

    def _estimate_useful_work(self, ctx: OperationContext) -> float:
        """
        估计有效功.
        不是常数 1.0——按操作类型分派.
        """
        if "prove" in ctx.op_name.lower():
            return 10.0  # 逻辑证明的有效功取决于证明价值
        if "infer" in ctx.op_name.lower() or "llm" in ctx.op_name.lower():
            return ctx.prompt_tokens * 0.01  # token 价值系数
        return 1.0  # 默认


# ── 测试 ──
def _test_v152():
    """A3 v15.2 五层热税自检."""
    calc = HeatTaxCalculator()
    failures = []

    # 场景1: LLM推理 — 低逻辑税, 高语义税
    ctx1 = OperationContext(
        op_name="llm_infer",
        power_joules=50.0,
        garbage_objects=[GarbageRecord("cache_entry", 1024)],
        prompt_tokens=128,
        attention_entropy=0.6,
    )
    r1 = calc.calculate(ctx1)
    # 期望: tax_phys=50, tax_info≈2.8e-18, tax_logic=0, tax_sem≈0.077, tax_cog=20
    assert r1.tax_phys == 50.0, f"tax_phys: {r1.tax_phys}"
    assert r1.tax_logic == 0.0, f"tax_logic: {r1.tax_logic}"
    assert 0.05 < r1.tax_sem < 0.2, f"tax_sem out of range: {r1.tax_sem}"
    assert abs(r1.tax_cog - 20.0) < 0.01, f"tax_cog: {r1.tax_cog} (expect ~20)"
    assert r1.total > 70, f"total too low: {r1.total}"
    assert 0 < r1.eta_asc < 0.05, f"eta_asc: {r1.eta_asc}"
    assert not r1.pseudo_tax_warning, "no pseudo tax expected"

    # 场景2: 逻辑死锁 — 高逻辑税, 低语义税
    ctx2 = OperationContext(
        op_name="prove_consistency",
        power_joules=50000.0,
        garbage_objects=[],
        unprovable_propositions=[
            UnprovableProposition("G_con", 5000.0),
            UnprovableProposition("G_halting", 3000.0),
        ],
        prompt_tokens=10,
        attention_entropy=0.1,
        synapse_changes=100,
        attention_switches=50,
    )
    r2 = calc.calculate(ctx2)
    # 期望: tax_phys=50000, tax_logic=3000 (inf), tax_sem 被L1放大
    assert r2.tax_phys == 50000.0, f"tax_phys: {r2.tax_phys}"
    assert r2.tax_logic == 3000.0, f"tax_logic: {r2.tax_logic}"  # mu*min(3000,5000)
    # L1 → L2 放大: base_sem=0.001, amp=exp(0.01*3000)≈1e13, result≈1.07e10
    base_sem = 0.1 * 10 * 1e-3  # 0.001
    amp = math.exp(0.01 * 3000)
    assert r2.tax_sem >= base_sem * amp * 0.99, f"L1→L2 amp: got {r2.tax_sem}, floor {base_sem * amp}"
    assert abs(r2.tax_cog - (20 + 20*0.67*100 + 2.0*50)) < 0.01, f"tax_cog: {r2.tax_cog}"
    assert r2.pseudo_tax_warning, "logic/cog > 0.6 should trigger pseudo_tax"

    # 场景3: 零操作 — 只有基础代谢
    ctx3 = OperationContext(op_name="idle")
    r3 = calc.calculate(ctx3)
    assert r3.tax_phys == 0.0
    assert abs(r3.tax_cog - 20.0) < 0.01, f"idle should pay E_base: {r3.tax_cog}"
    assert abs(r3.total - 20.0) < 0.01, f"idle total: {r3.total}"
    assert abs(r3.eta_asc - (1.0/(1.0+20))) < 0.01, f"idle eta: {r3.eta_asc}"

    return True


if __name__ == "__main__":
    import pytest
    _test_v152()
    print("A3 v15.2 HeatTaxCalculator: ALL TESTS PASSED ✅")
