#!/usr/bin/env python3
"""
MSS Dialog Fork — A6 contradiction elevation engine.

Architecture inspired by LLLM's Dialog.fork() (branch exploration),
extended with MSS A6: when branches contradict, elevate rather than choose.

Usage:
    df = DialogFork(base_prompt="分析 {target} 的架构问题")
    df.fork("安全视角", "从安全角度分析 {target}")
    df.fork("性能视角", "从性能角度分析 {target}")
    results, contradiction = df.resolve_with_elevation(
        "安全视角: 需要更多权限检查",
        "性能视角: 减少检查以降低延迟",
    )
    if contradiction:
        print(f"矛盾检测! 升维结果: {contradiction['elevated']}")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import re


@dataclass
class ForkBranch:
    """A single forked reasoning path."""
    name: str
    prompt: str
    result: Optional[str] = None
    delta: float = 0.0
    heat_tax: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContradictionDetection:
    """Result of contradiction analysis between two branches."""
    is_contradiction: bool
    confidence: float            # 0.0 = probably compatible, 1.0 = definitely contradictory
    domain: str                  # the dimension of the contradiction
    branch_a_summary: str
    branch_b_summary: str

    @property
    def severity(self) -> str:
        if self.confidence >= 0.8:
            return "high"
        if self.confidence >= 0.5:
            return "medium"
        return "low"


class DialogFork:
    """
    Fork exploration with A6 elevation.

    LLLM pattern: fork → explore → switch back → choose best
    MSS extension: fork → explore → detect contradiction → elevate → merge
    """

    def __init__(self, base_prompt: str):
        self.base_prompt = base_prompt
        self.branches: Dict[str, ForkBranch] = {}

    def fork(self, name: str, prompt: str) -> ForkBranch:
        """Create a fork branch for exploration. (LLLM-compatible: dialog.fork())"""
        branch = ForkBranch(name=name, prompt=prompt)
        self.branches[name] = branch
        return branch

    def set_result(self, name: str, result: str, delta: float = 0.0,
                   heat_tax: float = 0.0, **metadata):
        """Record a branch's result."""
        if name not in self.branches:
            raise KeyError(f"Branch '{name}' not found. Use fork() first.")
        b = self.branches[name]
        b.result = result
        b.delta = delta
        b.heat_tax = heat_tax
        b.metadata = metadata

    def detect_contradiction(self, branch_a: str, branch_b: str) -> ContradictionDetection:
        """
        H633: Detect if two branches contradict.

        Uses keyword-based contradiction detection as a lightweight proxy.
        For full meaning-field contradiction detection, use ollama+MSS model.
        """
        a = self.branches.get(branch_a)
        b = self.branches.get(branch_b)
        if not a or not b or not a.result or not b.result:
            return ContradictionDetection(
                is_contradiction=False, confidence=0.0,
                domain="unknown",
                branch_a_summary=a.result if a else "N/A",
                branch_b_summary=b.result if b else "N/A",
            )

        # ─── Contradiction signal detection ───────────────────
        # Opposing keywords
        oppose_pairs = [
            (r"增加|更多|更大|提高|加强", r"减少|更少|降低|减弱|去掉"),
            (r"安全|权限|检查|验证|审计", r"性能|速度|延迟|优化|跳过"),
            (r"保守|严格|限制|阻止", r"激进|宽松|放开|允许"),
            (r"必须|绝对|不可", r"可以|可选|不必要"),
            (r"集中|统一|合并|聚合", r"分散|独立|拆分|解耦"),
            (r"保持|维持|保留", r"改变|移除|删除|重构"),
        ]

        contradiction_score = 0.0
        detected_domains = []

        for i, (pattern_a, pattern_b) in enumerate(oppose_pairs):
            in_a = bool(re.search(pattern_a, a.result))
            in_b = bool(re.search(pattern_b, b.result))
            # Check cross: a's pattern in B, b's pattern in A
            cross_a = bool(re.search(pattern_b, a.result))
            cross_b = bool(re.search(pattern_a, b.result))

            if in_a and in_b:
                contradiction_score += 0.3
                domains = ["安全vs性能", "保守vs激进", "强制vs可选", "集中vs分散", "保持vs改变"]
                if i < len(domains):
                    detected_domains.append(domains[i])

            if cross_a and cross_b:
                contradiction_score += 0.2

        confidence = min(1.0, contradiction_score)

        return ContradictionDetection(
            is_contradiction=confidence >= 0.5,
            confidence=confidence,
            domain=", ".join(detected_domains) if detected_domains else "general",
            branch_a_summary=a.result[:100],
            branch_b_summary=b.result[:100],
        )

    def elevate(self, branch_a: str, branch_b: str) -> Dict[str, Any]:
        """
        A6: When branches contradict, elevate to a higher-dimension framework
        rather than choosing between them.

        Returns a framework that contains both perspectives.
        """
        detection = self.detect_contradiction(branch_a, branch_b)

        if not detection.is_contradiction:
            return {
                "elevated": f"No contradiction detected (confidence={detection.confidence:.2f}). "
                           f"Both branches are compatible.",
                "contradiction": detection,
                "strategy": "merge",
            }

        # ─── Elevation strategies ─────────────────────────────
        a = self.branches[branch_a]
        b = self.branches[branch_b]

        elevated = (
            f"[A6 升维框架]\n"
            f"分支A ({branch_a}): {a.result[:80]}...\n"
            f"分支B ({branch_b}): {b.result[:80]}...\n"
            f"矛盾域: {detection.domain}\n"
            f"置信度: {detection.confidence:.2f}\n\n"
            f"不在A和B之间二选一。两个视角都是有效的，但作用于不同层次:\n"
            f"- A在 {detection.domain.split('vs')[0].strip() if 'vs' in detection.domain else '<未知>'} 层有效\n"
            f"- B在 {detection.domain.split('vs')[1].strip() if 'vs' in detection.domain else '<未知>'} 层有效\n"
            f"升维方案: 建立双层架构，根据场景在两层之间动态切换"
        )

        return {
            "elevated": elevated,
            "contradiction": detection,
            "strategy": "two_layer_switch",
        }

    def resolve_with_elevation(self, branch_a: str, branch_b: str) -> Tuple[Dict, bool]:
        """
        Full A6 resolution pipeline:
        fork A + B → detect contradiction → elevate if needed.

        Returns (resolution_dict, was_elevated).
        """
        detection = self.detect_contradiction(branch_a, branch_b)

        if not detection.is_contradiction:
            return {
                "strategy": "merge",
                "result_a": self.branches[branch_a].result,
                "result_b": self.branches[branch_b].result,
                "summary": f"Both paths converge (confidence={detection.confidence:.2f})",
            }, False

        elevated = self.elevate(branch_a, branch_b)
        return elevated, True

    def all_delta_values(self) -> Dict[str, float]:
        """Get delta values for all branches."""
        return {name: b.delta for name, b in self.branches.items()}

    def total_heat_tax(self) -> float:
        """Sum heat tax across all branches."""
        return sum(b.heat_tax for b in self.branches.values())


# ─── Demo ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  MSS DialogFork — A6 Contradiction Elevation Demo")
    print("=" * 60)

    df = DialogFork(base_prompt="分析 {target} 的架构问题")

    # Fork two perspectives
    df.fork("安全视角", "从安全角度分析 {target}: 检查所有权限点")
    df.fork("性能视角", "从性能角度分析 {target}: 最小化检查延迟")

    # Simulate results (these WOULD come from LLM calls)
    df.set_result("安全视角",
        "需要增加更多的权限检查，每个关键操作必须验证。加强输入验证和安全审计日志。",
        delta=0.1, heat_tax=0.05)

    df.set_result("性能视角",
        "应该减少不必要的权限检查，降低每次调用的延迟。可以跳过非关键路径的验证。",
        delta=0.05, heat_tax=0.05)

    # Detect contradiction
    det = df.detect_contradiction("安全视角", "性能视角")
    print(f"\n  矛盾检测: {det.is_contradiction} (conf={det.confidence:.2f})")
    print(f"  矛盾域: {det.domain}")
    print(f"  严重度: {det.severity}")

    # Elevate!
    resolution, was_elevated = df.resolve_with_elevation("安全视角", "性能视角")
    print(f"\n  需要升维: {was_elevated}")
    print(f"  策略: {resolution['strategy']}")
    if was_elevated:
        print(f"\n  {resolution['elevated'][:300]}...")

    # Non-contradiction case
    print(f"\n{'─'*60}")
    print("  兼容案例: 两个不矛盾的视角")
    df2 = DialogFork(base_prompt="分析代码")
    df2.fork("代码风格", "遵循PEP8规范，使用black格式化")
    df2.fork("注释规范", "所有公共函数必须有docstring")
    df2.set_result("代码风格", "使用black格式化工具，配置line-length=100", delta=0.05, heat_tax=0.02)
    df2.set_result("注释规范", "使用docstring，遵循Google风格", delta=0.05, heat_tax=0.02)
    det2 = df2.detect_contradiction("代码风格", "注释规范")
    print(f"  矛盾: {det2.is_contradiction} (conf={det2.confidence:.2f}) — 两条建议互补，无需升维")
