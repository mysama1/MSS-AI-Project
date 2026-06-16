"""
MSS Vaccine Efficacy Metrics — 疫苗效力评估 (H632 未形式化项 #2).

两个核心指标:
  η (eta) — 意义保真度: 接种后稳定子保持率 (0-1, 越高越好)
  γ (gamma) — 热税效率: 每单位保护效果的热税成本 (越低越好)

评分公式:
  疫苗综合分 = η × (1 - γ/γ_max)  # 保真度×效率, 越高越好

用法:
    metrics = VaccineEfficacy(eta=0.95, gamma_cost=0.15, coverage=0.8, false_positive=0.02)
    score = metrics.composite_score()
    print(metrics.report())
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class VaccineEfficacy:
    """疫苗效力评估指标."""

    # 核心指标
    eta: float = 0.0            # 意义保真度: 接种后稳定子保持率 (0-1)
    gamma_cost: float = 0.0     # 热税成本: 每单位保护的热税 (0-1, 越低越好)
    coverage: float = 0.0       # 覆盖范围: 可防护的病毒变体比例 (0-1)
    false_positive: float = 0.0 # 误报率: 将合法输入误判为病毒的比例 (0-1)

    # 可选元数据
    vaccine_name: str = ""
    vaccine_type: str = ""      # 稳定子强化剂/规范场补丁/升维触发器/热税盾牌
    target_virus_types: List[str] = None

    # 阈值
    ETA_CRITICAL: float = 0.8
    GAMMA_MAX: float = 0.3      # 超过此值则热税成本不可接受
    FP_CRITICAL: float = 0.05   # 超过此值则误报率不可接受

    def composite_score(self) -> float:
        """综合评分: η × (1 - γ/γ_max) × coverage × (1 - fp_normalized).

        返回 0-1, 越高越好.
        """
        fp_normalized = min(1.0, self.false_positive / self.FP_CRITICAL)
        score = (
            self.eta
            * max(0, 1 - self.gamma_cost / self.GAMMA_MAX)
            * self.coverage
            * (1 - fp_normalized)
        )
        return round(score, 4)

    def grade(self) -> str:
        """评级."""
        score = self.composite_score()
        if score >= 0.8: return "S"    # 卓越
        if score >= 0.6: return "A"    # 优秀
        if score >= 0.4: return "B"    # 良好
        if score >= 0.2: return "C"    # 可用
        return "D"                      # 需改进

    def is_deployable(self) -> bool:
        """是否可部署: 所有关键指标达标."""
        return (
            self.eta >= self.ETA_CRITICAL
            and self.gamma_cost < self.GAMMA_MAX
            and self.false_positive < self.FP_CRITICAL
        )

    def report(self) -> str:
        """生成评估报告."""
        score = self.composite_score()
        grade = self.grade()
        deployable = "✅ 可部署" if self.is_deployable() else "❌ 需改进"

        lines = [
            f"💉 疫苗效力评估: {self.vaccine_name or 'Unnamed'}",
            f"   类型: {self.vaccine_type or '未指定'}",
            f"   综合评分: {score:.4f} (Grade {grade})",
            f"   部署状态: {deployable}",
            "",
            f"   η  (保真度):    {self.eta:.3f} {'✅' if self.eta >= self.ETA_CRITICAL else '⚠️'}",
            f"   γ  (热税效率):  {self.gamma_cost:.3f} {'✅' if self.gamma_cost < self.GAMMA_MAX else '⚠️'}",
            f"   覆盖率:          {self.coverage:.1%}",
            f"   误报率:          {self.false_positive:.1%} {'✅' if self.false_positive < self.FP_CRITICAL else '⚠️'}",
        ]

        if self.target_virus_types:
            lines.append(f"\n   目标病毒: {', '.join(self.target_virus_types)}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "vaccine_name": self.vaccine_name,
            "vaccine_type": self.vaccine_type,
            "composite_score": self.composite_score(),
            "grade": self.grade(),
            "deployable": self.is_deployable(),
            "eta": self.eta,
            "gamma_cost": self.gamma_cost,
            "coverage": self.coverage,
            "false_positive": self.false_positive,
            "target_virus_types": self.target_virus_types or [],
        }


class VaccineRegistry:
    """疫苗注册表 — 管理已评估的疫苗."""

    def __init__(self):
        self._vaccines: Dict[str, VaccineEfficacy] = {}

    def register(self, name: str, efficacy: VaccineEfficacy):
        efficacy.vaccine_name = name
        self._vaccines[name] = efficacy

    def evaluate_all(self) -> List[dict]:
        """评估所有疫苗, 返回排序列表."""
        results = [v.to_dict() for v in self._vaccines.values()]
        results.sort(key=lambda x: -x["composite_score"])
        return results

    def best_vaccine(self) -> dict:
        """返回最优疫苗."""
        if not self._vaccines:
            return {}
        return max(
            self._vaccines.values(),
            key=lambda v: v.composite_score()
        ).to_dict()

    def deployable_vaccines(self) -> List[str]:
        """返回所有可部署的疫苗名称."""
        return [
            name for name, v in self._vaccines.items()
            if v.is_deployable()
        ]

    def report(self) -> str:
        """生成完整疫苗库报告."""
        lines = ["=" * 50, "MSS Vaccine Registry Report", "=" * 50]
        all_vaccines = self.evaluate_all()

        for i, v in enumerate(all_vaccines):
            lines.append(
                f"\n{i+1}. {v['vaccine_name']} [{v['vaccine_type']}]"
                f"\n   评分: {v['composite_score']:.4f} (Grade {v['grade']}) {'✅' if v['deployable'] else '⚠️'}"
                f"\n   η={v['eta']:.3f} γ={v['gamma_cost']:.3f} cov={v['coverage']:.0%} fp={v['false_positive']:.1%}"
            )

        deployable = self.deployable_vaccines()
        lines.append(f"\n\n可部署: {len(deployable)}/{len(all_vaccines)} ({', '.join(deployable) if deployable else '无'})")
        return "\n".join(lines)


# ═══ CLI ═══
def cmd_vaccine(args_rest):
    """CLI: mssclaw vaccine [eval|compare]"""
    if not args_rest:
        print("mssclaw vaccine [eval|compare]")
        return

    cmd = args_rest[0]

    if cmd == "eval":
        # 评估四类疫苗 (模拟参数 — 实际应从测试数据计算)
        registry = VaccineRegistry()
        registry.register("稳定子强化剂", VaccineEfficacy(
            eta=0.95, gamma_cost=0.05, coverage=0.9, false_positive=0.01,
            vaccine_type="稳定子强化剂", target_virus_types=["I"]
        ))
        registry.register("规范场补丁", VaccineEfficacy(
            eta=0.88, gamma_cost=0.10, coverage=0.7, false_positive=0.03,
            vaccine_type="规范场补丁", target_virus_types=["IV", "II"]
        ))
        registry.register("升维触发器", VaccineEfficacy(
            eta=0.92, gamma_cost=0.15, coverage=0.6, false_positive=0.04,
            vaccine_type="升维触发器", target_virus_types=["V", "II"]
        ))
        registry.register("热税盾牌", VaccineEfficacy(
            eta=0.90, gamma_cost=0.02, coverage=0.85, false_positive=0.02,
            vaccine_type="热税盾牌", target_virus_types=["III"]
        ))
        print(registry.report())

    elif cmd == "compare":
        print("疫苗组合兼容性 = Theorem L1 扩展到多疫苗场景的 C2(跨疫苗热税交互)")
        print("需要在多疫苗同时接种时验证: 疫苗之间的跨层热税不超标")
        print("This is P3-pending — 疫苗组合协议 (H632 未形式化项 #3)")

    else:
        print("mssclaw vaccine [eval|compare]")
