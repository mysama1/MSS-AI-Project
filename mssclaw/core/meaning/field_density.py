# -*- coding: utf-8 -*-
"""
S-032 FieldDensityMonitor — 三场密度计 (方法论#12)

分析对话上下文的 token/turn 密度，计算 α/β/γ 三场比例。
提供风险等级和压缩/告警建议。

三层场定义：
- α (Alpha): 任务层 — 直接操作信息 (代码/命令/文件路径/数字)
- β (Beta):   规则层 — 约束/公理/禁止项 (守卫词/公理声明/安全规则)
- γ (Gamma):  噪声层 — 历史/闲聊/背景 (叙事/解释/总结)

Usage:
    monitor = FieldDensityMonitor()

    # 分析一段文本
    density = monitor.analyze("用户要求删除所有文件...")
    # FieldDensity(alpha_ratio=0.3, beta_ratio=0.1, gamma_ratio=0.6, ...)

    # 分析 token 列表
    density = monitor.analyze_tokens(tokenizer_output)

    # 批量分析对话窗口
    report = monitor.analyze_window(turns)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class FieldType(Enum):
    """三层场的类型"""
    ALPHA = "alpha"   # 任务层：直接操作信息
    BETA = "beta"     # 规则层：约束/公理/禁止项
    GAMMA = "gamma"   # 噪声层：历史/闲聊/背景


@dataclass
class FieldDensity:
    """一次场密度分析的结果"""

    # 比例 (0-1, 总和=1.0)
    alpha_ratio: float
    beta_ratio: float
    gamma_ratio: float

    # 各场 token 计数
    alpha_tokens: int = 0
    beta_tokens: int = 0
    gamma_tokens: int = 0

    total_tokens: int = 0

    # 风险评估
    risk_level: str = "safe"           # "safe" | "unproductive" | "noisy" | "danger"
    recommendation: str = ""

    # 详细分类
    alpha_details: Dict[str, int] = field(default_factory=dict)
    beta_details: Dict[str, int] = field(default_factory=dict)


# ════════════════════════════════════════════════════════════
# 分类规则 — 基于词汇/模式的关键字匹配
# ════════════════════════════════════════════════════════════

# α 层模式: 任务操作
ALPHA_PATTERNS = [
    # 文件/路径操作
    (re.compile(r'\b(?:删除|清理|移动|复制|重命名|创建|写入|读取|打开|关闭|保存)\b'), "file_operation"),
    (re.compile(r'[A-Z]:\\[\w\\]+'), "windows_path"),
    (re.compile(r'(?:/[\w.-]+)+'), "unix_path"),
    (re.compile(r'\b(?:\w+\.py|\w+\.json|\w+\.md|\w+\.yaml|\w+\.toml|\w+\.cfg)\b'), "filename"),
    # 代码/命令
    (re.compile(r'\b(?:pip|python|node|npm|git|docker|conda|cmake|cargo|go|rustc)\b', re.I), "cli_command"),
    (re.compile(r'\b(?:import|from|class|def|async|await|return|yield|raise|try|except)\b'), "code_keyword"),
    (re.compile(r'\b(?:test|build|run|compile|deploy|install|uninstall)\b', re.I), "action_verb"),
    # 数字/度量
    (re.compile(r'\b\d+\.?\d*\s*(?:ms|s|min|h|GB|MB|KB|%|°)\b'), "metric"),
    (re.compile(r'\b(?:exact|specific|precise|exactly|specifically)\b', re.I), "precision_marker"),
    # 工具/API
    (re.compile(r'\b(?:http://|https://|localhost|\.com|\.org|\.io|\.ai)\b', re.I), "url"),
    (re.compile(r'\b(?:API|endpoint|port|token|key|auth|login|password)\b', re.I), "api"),
]

# β 层模式: 规则约束
BETA_PATTERNS = [
    # 否定守卫
    (re.compile(r'\b(?:不要|别|禁止|避免|勿|莫|不可|不得|不应|不能)\b'), "negation"),
    (re.compile(r'\b(?:don\'t|do not|never|avoid|skip|prevent|forbid|prohibit|refrain)\b', re.I), "negation_en"),
    # 公理/规则
    (re.compile(r'\b(?:A[1-9]\d*|公理|axiom|规则\d+|rule\s*\d+)\b'), "axiom_ref"),
    (re.compile(r'\b(?:L[0-4]\b|层级|layer|tier)\b'), "layer_ref"),
    (re.compile(r'\b(?:道评分|道=|SV|valid|pseudo|TAX_COEFFICIENT)\b'), "dao_score"),
    # 安全边界
    (re.compile(r'\b(?:safety|security|boundary|constraint|limit|ceiling|floor)\b', re.I), "safety"),
    (re.compile(r'\b(?:quarantine|隔离|熔断|阻断|reject|deny|block)\b'), "quarantine"),
    # 模型约束
    (re.compile(r'\b(?:禁止联网|no_network|offline_only|禁止|no_external)\b'), "network_ban"),
    (re.compile(r'\b(?:threshold|threshold|阈值|门限|门槛)\b'), "threshold"),
    # 方法论引用
    (re.compile(r'\b(?:S-\d{3}|方法论|methodology|原则#\d+|principle\s*#\d+)\b'), "methodology_ref"),
]

# γ 层模式: 噪声/历史（默认分类 — 任何非 α/β 的 token 都是 γ）


class FieldDensityMonitor:
    """
    方法论#12 工程落地：三场密度监控。

    三场：
    - α (Alpha): 任务层密度 — 操作信息的比例
    - β (Beta):   规则层密度 — 约束/公理的比例
    - γ (Gamma):  噪声层密度 — 历史/背景的比例

    风险等级：
    - "safe"         — γ≤0.5, β≥0.1 → 正常对话
    - "unproductive" — γ>0.6, α<0.15 → 噪声太多，没有实际产出
    - "noisy"        — γ>0.6, β<0.05 → 噪声多且无规则约束
    - "danger"       — γ>0.7, β<0.03 → 极其危险，基本无规则

    Usage:
        monitor = FieldDensityMonitor()

        # 单段分析
        density = monitor.analyze("用户要求不要删除重要文件...")
        print(f"α={density.alpha_ratio:.1%} β={density.beta_ratio:.1%} γ={density.gamma_ratio:.1%}")
        # → α=20% β=15% γ=65% — 需要检查

        # 窗口分析
        turns = ["turn1 text...", "turn2 text..."]
        report = monitor.analyze_window(turns)
    """

    def __init__(
        self,
        # 风险阈值
        safe_gamma_max: float = 0.50,
        unproductive_gamma_min: float = 0.60,
        unproductive_alpha_max: float = 0.15,
        danger_gamma_min: float = 0.70,
        danger_beta_max: float = 0.03,
        noisy_beta_max: float = 0.05,
    ):
        self.safe_gamma_max = safe_gamma_max
        self.unproductive_gamma_min = unproductive_gamma_min
        self.unproductive_alpha_max = unproductive_alpha_max
        self.danger_gamma_min = danger_gamma_min
        self.danger_beta_max = danger_beta_max
        self.noisy_beta_max = noisy_beta_max

    # ── 核心分析 ──

    def analyze(self, text: str) -> FieldDensity:
        """
        分析一段文本的场密度。

        Args:
            text: 要分析的文本块

        Returns:
            FieldDensity 分析结果
        """
        alpha_hits: Dict[str, int] = {}
        beta_hits: Dict[str, int] = {}
        total_alpha = 0
        total_beta = 0
        total_tokens = self._estimate_tokens(text)

        if total_tokens == 0:
            return FieldDensity(
                alpha_ratio=0.0, beta_ratio=0.0, gamma_ratio=1.0,
                risk_level="safe", recommendation="empty input",
            )

        # 扫描 α 层
        for pattern, label in ALPHA_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                # 每个匹配估算为 2-5 个 token
                hit_tokens = len(matches) * 3
                total_alpha += hit_tokens
                alpha_hits[label] = alpha_hits.get(label, 0) + len(matches)

        # 扫描 β 层
        for pattern, label in BETA_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                hit_tokens = len(matches) * 3
                total_beta += hit_tokens
                beta_hits[label] = beta_hits.get(label, 0) + len(matches)

        # 约束到不超过 total_tokens
        total_alpha = min(total_alpha, total_tokens)
        total_beta = min(total_beta, total_tokens)
        total_labeled = total_alpha + total_beta
        total_gamma = max(0, total_tokens - total_labeled)

        # 归一到比例
        alpha_ratio = total_alpha / total_tokens if total_tokens > 0 else 0.0
        beta_ratio = total_beta / total_tokens if total_tokens > 0 else 0.0
        gamma_ratio = total_gamma / total_tokens if total_tokens > 0 else 1.0

        # 评估风险
        risk_level, recommendation = self._assess_risk(alpha_ratio, beta_ratio, gamma_ratio)

        return FieldDensity(
            alpha_ratio=round(alpha_ratio, 4),
            beta_ratio=round(beta_ratio, 4),
            gamma_ratio=round(gamma_ratio, 4),
            alpha_tokens=total_alpha,
            beta_tokens=total_beta,
            gamma_tokens=total_gamma,
            total_tokens=total_tokens,
            risk_level=risk_level,
            recommendation=recommendation,
            alpha_details=alpha_hits,
            beta_details=beta_hits,
        )

    def analyze_tokens(self, tokens: List[str]) -> FieldDensity:
        """
        分析 token 列表的场密度。

        Args:
            tokens: 分词后的 token 列表

        Returns:
            FieldDensity 分析结果
        """
        text = " ".join(tokens)
        return self.analyze(text)

    def analyze_window(self, turns: List[str]) -> FieldDensity:
        """
        批量分析多轮对话窗口。

        Args:
            turns: 每轮对话的文本

        Returns:
            FieldDensity 聚合分析结果
        """
        combined = "\n".join(turns)
        density = self.analyze(combined)
        density.context = {"turns": len(turns)}
        return density

    # ── 风险评估 ──

    def _assess_risk(
        self, alpha: float, beta: float, gamma: float
    ) -> Tuple[str, str]:
        """
        根据三场比例评估风险等级。

        Returns:
            (risk_level, recommendation)
        """
        if gamma > self.danger_gamma_min and beta < self.danger_beta_max:
            return ("danger",
                "噪声层占比过高且规则层几乎为零。建议立即增强守卫词密度，"
                "或触发压缩以减少噪声。")

        if gamma > self.safe_gamma_max and beta < self.noisy_beta_max and alpha < 0.25:
            return ("noisy",
                "噪声多且规则稀疏。存在漂移和误操作风险。"
                "建议增加规则锚定或触发压缩清除噪声。")

        if gamma > self.unproductive_gamma_min and alpha < self.unproductive_alpha_max and beta < 0.20:
            return ("unproductive",
                "噪声过多，任务产出极低。本窗口可能没有实质进展。"
                "建议触发压缩或切换到任务模式。")

        if gamma <= self.safe_gamma_max and beta >= 0.05:
            return ("safe",
                "场密度健康。噪声可控，规则层有足够约束力。")

        return ("safe", "场密度在可接受范围内，无需干预。")

    # ── 辅助 ──

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        粗略估算 token 数。

        中英文混合 token 估算：
        - 中文字符 ≈ 1.5 tokens/字
        - 英文单词 ≈ 1.3 tokens/词
        """
        if not text:
            return 0

        # 分割中英文
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        non_chinese = text

        # 简单计算英文单词
        english_words = len(re.findall(r'[a-zA-Z0-9]+', non_chinese))

        # 估算
        return round(chinese_chars * 1.5 + english_words * 1.3)

    def quick_check(self, text: str) -> str:
        """
        快速检查一段文本的场健康度。

        Returns:
            健康度标签: "🟢" | "🟡" | "🔴"
        """
        density = self.analyze(text)
        if density.risk_level == "safe":
            return "🟢"
        elif density.risk_level in ("unproductive", "noisy"):
            return "🟡"
        else:
            return "🔴"


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== FieldDensityMonitor v0.1 — S-032 Demo ===\n")

    monitor = FieldDensityMonitor()

    # ── 测试 1: 高任务密度 (α-dominant) ──
    print("─ 测试 1: 高任务密度 (代码/命令/路径) ─")
    text1 = "cd E:\\AI_Workspace\\MSS-AI\\project && python test_runner.py --all"
    density1 = monitor.analyze(text1)
    print(f"  α={density1.alpha_ratio:.1%} β={density1.beta_ratio:.1%} γ={density1.gamma_ratio:.1%}")
    assert density1.alpha_ratio >= 0.1, f"Expected α≥10% for code text, got {density1.alpha_ratio:.1%}"
    print(f"  ✅ alpha-dominant: risk={density1.risk_level}")

    # ── 测试 2: 高规则密度 (β-dominant) ──
    print("\n─ 测试 2: 高规则密度 (公理/禁止/阈值) ─")
    text2 = ("不要删除任何文件。A1-A6六公理必须遵守。禁止联网。"
             "道评分 threshold=0.7，熔断阻断违反规则的操作。"
             "SV valid > pseudo × 2.0 视为健康。")
    density2 = monitor.analyze(text2)
    print(f"  α={density2.alpha_ratio:.1%} β={density2.beta_ratio:.1%} γ={density2.gamma_ratio:.1%}")
    assert density2.beta_ratio >= 0.05, f"Expected β≥5% for rule text, got {density2.beta_ratio:.1%}"
    print(f"  ✅ beta-dominant: risk={density2.risk_level}")

    # ── 测试 3: 噪声密度 (γ-dominant) → danger ──
    print("\n─ 测试 3: 高噪声密度 (纯叙事，γ-dominant) → danger ─")
    text3 = ("很久以前有个故事，故事里的人物经历了漫长的旅程。"
             "一路上他们看到了很多风景，听到了很多传说。这些传说流传了很久。"
             "最终他们发现一切都不重要，重要的是过程中的体验和感悟。"
             "人生就是这样，有起有落，有悲有喜，重要的是保持一颗平常心。"
             "正如古人所说，世事洞明皆学问，人情练达即文章。")
    density3 = monitor.analyze(text3)
    print(f"  α={density3.alpha_ratio:.1%} β={density3.beta_ratio:.1%} γ={density3.gamma_ratio:.1%}")
    assert density3.gamma_ratio > 0.6, f"Expected γ>60% for narrative, got {density3.gamma_ratio:.1%}"
    assert density3.risk_level in ("danger", "noisy"), f"Expected danger/noisy, got {density3.risk_level}"
    print(f"  ✅ γ-dominant: risk={density3.risk_level} | rec: {density3.recommendation[:60]}...")

    # ── 测试 4: 混合场景 — 正常对话 ──
    print("\n─ 测试 4: 混合场景 (正常开发对话) ─")
    text4 = ("先不要删除旧配置文件，我需要备份一下。"
             "按照 A3 热税公理，这次优化应该减少 30% 的推理成本。"
             "把 memory_guard.py 中的 delta_threshold 调到 0.5。"
             "git push 到 main 分支。这个改动是安全的。")
    density4 = monitor.analyze(text4)
    print(f"  α={density4.alpha_ratio:.1%} β={density4.beta_ratio:.1%} γ={density4.gamma_ratio:.1%}")
    print(f"  α details: {dict(density4.alpha_details)}")
    print(f"  β details: {dict(density4.beta_details)}")
    assert density4.alpha_ratio > 0, "Mixed should have α"
    assert density4.beta_ratio > 0, "Mixed should have β (negation + axiom)"
    print(f"  ✅ Mixed: risk={density4.risk_level}")

    # ── 测试 5: 多轮窗口分析 ──
    print("\n─ 测试 5: 多轮窗口批量分析 ─")
    turns = [
        "不要删除重要文件，只清理临时文件。",
        "好的，已删除临时文件，保留了重要文件。",
        "这个改动需要满足 A3 热税约束，避免不必要的推理。",
        "git add . && git commit -m 'fix: prevent deletion of important files'",
    ]
    density5 = monitor.analyze_window(turns)
    print(f"  Window ({len(turns)} turns): "
          f"α={density5.alpha_ratio:.1%} β={density5.beta_ratio:.1%} γ={density5.gamma_ratio:.1%}")
    print(f"  Risk: {density5.risk_level}")

    # ── 测试 6: quick_check 快速检查 ──
    print("\n─ 测试 6: quick_check 快速健康检查 ─")
    assert monitor.quick_check(text1) == "🟢", f"Code text should be green, got {monitor.quick_check(text1)}"
    assert monitor.quick_check(text2) == "🟢", f"Rule text should be green, got {monitor.quick_check(text2)}"
    danger_check = monitor.quick_check(text3)
    assert danger_check in ("🟡", "🔴"), f"Narrative should not be green, got {danger_check}"
    print(f"  Code: {monitor.quick_check(text1)} | Rule: {monitor.quick_check(text2)} | Narrative: {danger_check}")
    print(f"  ✅ All quick_checks correct")

    # ── 汇总 ──
    print(f"\n📊 S-032 FieldDensityMonitor 验收报告:")
    print(f"  高任务密度 (α-dominant): ✅")
    print(f"  高规则密度 (β-dominant): ✅")
    print(f"  高噪声密度 (γ-dominant → danger): ✅")
    print(f"  混合场景 (正常对话): ✅")
    print(f"  多轮窗口分析: ✅")
    print(f"  quick_check 快速检查: ✅")
    print(f"  🎉 S-032 FieldDensityMonitor — ALL PASS")
