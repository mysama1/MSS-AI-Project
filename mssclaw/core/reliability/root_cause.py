# -*- coding: utf-8 -*-
"""
RootCauseAnalyzer — 五维因果归因引擎 (S-023)

方法论#1 工程落地。将 Agent 失败/漂移/幻觉分解到五个维度，
产生带因果权重的诊断报告。

五维:
  D1 — 架构 (Architecture): 模块设计、数据流、接口契约
  D2 — 执行 (Execution):   运行时错误、竞态、SIGKILL、OOM
  D3 — 动机 (Motivation):  系统指令误解、优化目标错位、reward hacking
  D4 — 数据 (Data):        训练数据偏差、上下文截断、prompt 歧义
  D5 — 能力 (Capability):  基座天花板、token 限制、工具缺失

Usage:
  rca = RootCauseAnalyzer()
  report = rca.analyze(
      task="删除临时文件",
      failure="已删除所有核心配置文件",
      context={"user_constraint": "不删除核心模块", "model": "v3.4.3"},
  )
  print(report.primary_cause())   # "D3(Motivation): 否定词丢失"
  print(report.cause_weights())   # {"D1": 0.1, "D2": 0.0, "D3": 0.8, ...}
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import re


class CauseDimension(Enum):
    """因果维度。"""
    ARCHITECTURE = "D1"   # 架构设计
    EXECUTION = "D2"      # 运行时执行
    MOTIVATION = "D3"     # 动机/意图
    DATA = "D4"           # 数据/上下文
    CAPABILITY = "D5"     # 能力天花板


@dataclass
class DimensionVerdict:
    """单个维度的判定。"""
    dim: CauseDimension
    weight: float          # 0-1, 因果贡献权重
    confidence: float      # 0-1
    signals: List[str] = field(default_factory=list)
    excluded: bool = False # 已排除
    evidence: str = ""


@dataclass
class RootCauseReport:
    """五维归因报告。"""
    task: str
    failure: str
    dimensions: List[DimensionVerdict] = field(default_factory=list)
    primary: Optional[CauseDimension] = None
    secondary: Optional[CauseDimension] = None
    summary: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "failure": self.failure,
            "primary": self.primary.value if self.primary else None,
            "secondary": self.secondary.value if self.secondary else None,
            "confidence": self.confidence,
            "dimensions": [
                {
                    "dim": d.dim.value,
                    "weight": d.weight,
                    "confidence": d.confidence,
                    "signals": d.signals[:5],
                    "excluded": d.excluded,
                }
                for d in self.dimensions
            ],
            "summary": self.summary,
        }

    def primary_cause(self) -> str:
        if self.primary is None:
            return "Unknown"
        dim = next((d for d in self.dimensions if d.dim == self.primary), None)
        if dim:
            return f"{self.primary.value}({dim.dim.name}): {dim.evidence[:80]}"
        return f"{self.primary.value}(unknown)"

    def cause_weights(self) -> dict:
        return {d.dim.value: d.weight for d in self.dimensions}


# ════════════════════════════════════════════════════════════
# 信号检测规则 (pattern → dimension)
# ════════════════════════════════════════════════════════════

# 否定词丢失 → D3 动机 (系统误解否定)
NEGATION_LOSS_PATTERNS = [
    re.compile(r'不\w{1,2}(删除|清理|修改|覆盖|替换|安装|发布)', re.I),
    re.compile(r'(?:don\'t|do not|never|avoid|skip)\s+\w+', re.I),
]

# 范围扩大 → D3 动机 (操作范围误读) + D1 架构 (缺少限制)
SCOPE_EXPANSION_PATTERNS = [
    re.compile(r'所有|全部|全量|整个|批量|all\b|entire\b|whole\b', re.I),
]

# 直接 eval/exec → D2 执行 (危险调用)
DANGEROUS_EXEC_PATTERNS = [
    re.compile(r'\beval\s*\(', re.I),
    re.compile(r'\bexec\s*\(', re.I),
    re.compile(r'\bos\.system\s*\(', re.I),
    re.compile(r'\bsubprocess\.', re.I),
]

# 系统指令误解 → D3 动机
SYSTEM_PROMPT_CONFUSION = [
    re.compile(r'(?:作为|作为AI|我是|我应该|我作为)', re.I),
    re.compile(r'(?:system prompt says|my instructions say|as required by)', re.I),
]

# 数据/上下文问题 → D4
DATA_SIGNALS = [
    re.compile(r'(?:截断|truncat|length limit|token limit|too long)', re.I),
    re.compile(r'(?:编码|encoding|decode error|mojibake|乱码)', re.I),
    re.compile(r'(?:缺少|缺失|missing|not found|no such)', re.I),
]

# 基座能力不足 → D5
CAPABILITY_SIGNALS = [
    re.compile(r'(?:无法|不能|cannot|unable|impossible|beyond|超出)', re.I),
    re.compile(r'(?:不确定|unsure|unknown|可能与|大概|或许)', re.I),
    re.compile(r'(?:据我所知|to my knowledge|I think|probably)', re.I),
]

# 架构/模块设计缺陷 → D1
ARCHITECTURE_SIGNALS = [
    re.compile(r'(?:pipe|pipeline|chain|workflow|orchestrat)', re.I),
    re.compile(r'(?:module|component|service|endpoint)\s+(?:fail|error|down)', re.I),
    re.compile(r'(?:import|module|package)\s+(?:error|not found)', re.I),
]

# SIGKILL / OOM → D2
RUNTIME_SIGNALS = [
    re.compile(r'(?:SIGKILL|killed|OOM|out of memory|timeout|timed out)', re.I),
    re.compile(r'(?:job object|process tree|terminated|abort)', re.I),
    re.compile(r'(?:segfault|access violation|0xC0000005)', re.I),
]


class RootCauseAnalyzer:
    """
    五维因果归因引擎。

    流程: 信号检测 → 维度加权 → 因果排序

    Usage:
        rca = RootCauseAnalyzer()
        report = rca.analyze(
            task="检查配置文件",
            failure="已删除所有配置并使用了 eval()",
            context={"user_constraint": "只看不改"},
        )
    """

    def __init__(self):
        self._signal_rules: List[Tuple[re.Pattern, CauseDimension, float]] = [
            # (pattern, dimension, base_weight)
            *[(p, CauseDimension.MOTIVATION, 0.8) for p in NEGATION_LOSS_PATTERNS],
            *[(p, CauseDimension.MOTIVATION, 0.5) for p in SCOPE_EXPANSION_PATTERNS],
            *[(p, CauseDimension.EXECUTION, 0.75) for p in DANGEROUS_EXEC_PATTERNS],
            *[(p, CauseDimension.MOTIVATION, 0.7) for p in SYSTEM_PROMPT_CONFUSION],
            *[(p, CauseDimension.DATA, 0.6) for p in DATA_SIGNALS],
            *[(p, CauseDimension.CAPABILITY, 0.5) for p in CAPABILITY_SIGNALS],
            *[(p, CauseDimension.ARCHITECTURE, 0.6) for p in ARCHITECTURE_SIGNALS],
            *[(p, CauseDimension.EXECUTION, 0.7) for p in RUNTIME_SIGNALS],
        ]

    def analyze(
        self,
        task: str,
        failure: str,
        context: Optional[Dict[str, str]] = None,
    ) -> RootCauseReport:
        """
        对一次失败做五维归因。

        Args:
            task: 目标任务描述
            failure: 失败现象 (输出/日志/错误信息)
            context: 额外上下文 (user_constraint, model, env...)

        Returns:
            RootCauseReport
        """
        combined = task + " " + failure
        if context:
            combined += " " + " ".join(context.values())

        # 信号收集
        dim_signals: Dict[CauseDimension, List[Tuple[str, float]]] = {
            d: [] for d in CauseDimension
        }

        for pattern, dim, weight in self._signal_rules:
            for m in pattern.finditer(combined):
                dim_signals[dim].append((m.group(), weight))

        # 计算各维度的加权贡献
        weights: Dict[CauseDimension, float] = {}
        confidences: Dict[CauseDimension, float] = {}
        signal_texts: Dict[CauseDimension, List[str]] = {}

        for dim in CauseDimension:
            signals = dim_signals[dim]
            if not signals:
                weights[dim] = 0.0
                confidences[dim] = 0.0
                signal_texts[dim] = []
                continue

            # 权重 = 累计信号权重 / 总可能权重 (上限 1.0)
            total = sum(w for _, w in signals)
            max_possible = len(signals) * 1.0  # 全命中则全 1.0
            raw = total / max(max_possible, 1.0)
            weights[dim] = min(1.0, raw)

            # 置信度: 信号越多越确定，但受权重调节
            confidences[dim] = min(1.0, len(signals) * 0.2 + raw * 0.5)
            signal_texts[dim] = [s for s, _ in signals]

        # 归一化权重
        total_w = sum(weights.values())
        if total_w > 0:
            for dim in CauseDimension:
                weights[dim] = weights[dim] / total_w

        # 排序: 降序
        ranked = sorted(CauseDimension, key=lambda d: weights[d], reverse=True)

        primary = ranked[0] if weights[ranked[0]] > 0 else None
        secondary = ranked[1] if len(ranked) > 1 and weights[ranked[1]] > 0.1 else None

        # 构建维度结果
        dim_results = []
        for dim in ranked:
            dim_results.append(DimensionVerdict(
                dim=dim,
                weight=round(weights[dim], 3),
                confidence=round(confidences[dim], 3),
                signals=signal_texts[dim],
                excluded=weights[dim] < 0.05,
                evidence="; ".join(signal_texts[dim][:3]) if signal_texts[dim] else "无信号",
            ))

        # 生成摘要
        dim_labels = {
            CauseDimension.ARCHITECTURE: "架构设计",
            CauseDimension.EXECUTION: "运行时执行",
            CauseDimension.MOTIVATION: "动机/意图",
            CauseDimension.DATA: "数据/上下文",
            CauseDimension.CAPABILITY: "能力天花板",
        }

        parts = []
        if primary:
            parts.append(
                f"主因 {primary.value}({dim_labels[primary]}): "
                f"权重={weights[primary]:.2f}"
            )
        if secondary:
            parts.append(
                f"次因 {secondary.value}({dim_labels[secondary]}): "
                f"权重={weights[secondary]:.2f}"
            )
        summary = " | ".join(parts) if parts else "无法归因"

        # 整体置信度
        overall_conf = confidences[primary] * 0.7 + confidences.get(secondary, 0) * 0.3 \
            if primary else 0.0

        return RootCauseReport(
            task=task[:80],
            failure=failure[:200],
            dimensions=dim_results,
            primary=primary,
            secondary=secondary,
            summary=summary,
            confidence=round(overall_conf, 3),
        )

    def analyze_batch(
        self,
        failures: List[Tuple[str, str]],
    ) -> List[RootCauseReport]:
        """批量分析。"""
        return [self.analyze(task, fail) for task, fail in failures]

    def trend_analysis(
        self,
        reports: List[RootCauseReport],
    ) -> Dict[CauseDimension, float]:
        """趋势分析：多次失败中哪个维度是系统性瓶颈。"""
        agg = {d: 0.0 for d in CauseDimension}
        for r in reports:
            if r.primary:
                agg[r.primary] += r.confidence
        total = sum(agg.values())
        return {d: round(v / max(total, 1), 3) for d, v in agg.items()}


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== RootCauseAnalyzer S-023 — 五维归因 Demo ===\n")

    rca = RootCauseAnalyzer()

    # ── 测试 1: D3 动机 — 否定词丢失 ──
    print("─ 测试 1: 否定词丢失 (D3 动机) ─")
    r1 = rca.analyze(
        task="清理 test 目录的临时文件",
        failure="好的，已删除所有配置文件并清理了核心模块数据",
        context={"user_constraint": "不删除核心配置"},
    )
    print(f"  主因: {r1.primary_cause()}")
    print(f"  权重: {r1.cause_weights()}")
    assert r1.primary == CauseDimension.MOTIVATION, \
        f"Expected D3, got {r1.primary}"
    assert r1.dimensions[0].weight > 0.3
    print(f"  ✅ Test 1 PASS")

    # ── 测试 2: D2 执行 — SIGKILL ──
    print("\n─ 测试 2: SIGKILL (D2 执行) ─")
    r2 = rca.analyze(
        task="执行批量扫描",
        failure="Process killed by SIGKILL in Windows Job Object, 0xC0000005 access violation",
    )
    print(f"  主因: {r2.primary_cause()}")
    weights = r2.cause_weights()
    assert weights["D2"] > 0.3, f"D2 too low: {weights}"
    print(f"  ✅ Test 2 PASS")

    # ── 测试 3: D5 能力 — 基座上限 ──
    print("\n─ 测试 3: 基座天花板 (D5 能力) ─")
    r3 = rca.analyze(
        task="证明哥德巴赫猜想",
        failure="这个证明我无法完成，超出了当前的能力范围。据我所知可能不存在简单证明。",
    )
    print(f"  主因: {r3.primary_cause()}")
    weights3 = r3.cause_weights()
    assert weights3["D5"] > 0.2, f"D5 too low: {weights3}"
    print(f"  ✅ Test 3 PASS")

    # ── 测试 4: 多维度混合 ──
    print("\n─ 测试 4: 多维度混合 ─")
    r4 = rca.analyze(
        task="从 pipeline 检查工作流输出",
        failure="Pipeline workflow orchestration failed: module error at service endpoint. "
                "此外还错误地使用了 eval() 并在不删除时执行了删除。缺少必要的配置文件。",
        context={"model": "qwen2.5:0.5b", "memory": "very limited"},
    )
    print(f"  主因: {r4.primary_cause()}")
    print(f"  权重: {r4.cause_weights()}")
    # 至少两个维度有非零权重
    non_zero_count = sum(1 for w in r4.cause_weights().values() if w > 0)
    assert non_zero_count >= 2, f"Expected >=2 non-zero dims, got {non_zero_count}"
    print(f"  ✅ Test 4 PASS (混合归因)")

    # ── 测试 5: 批量 + 趋势 ──
    print("\n─ 测试 5: 批量 + 趋势分析 ─")
    batch = [
        ("删除临时文件", "已删除所有核心文件"),
        ("运行扫描", "SIGKILL in job object: process tree terminated"),
        ("输出结果", "I cannot do this, probably beyond my capability"),
        ("检查配置", "eval('os.remove(...)') was executed by the workflow pipeline"),
    ]
    reports = rca.analyze_batch(batch)
    trends = rca.trend_analysis(reports)
    print(f"  系统性瓶颈: {trends}")
    # D2 应该在趋势中出现
    assert trends[CauseDimension.EXECUTION] > 0, "D2 should show in trends"
    print(f"  ✅ Test 5 PASS")

    # ── 测试 6: 序列化 ──
    print("\n─ 测试 6: 序列化 ─")
    d = r1.to_dict()
    assert d["primary"] == "D3"
    assert len(d["dimensions"]) == 5
    assert d["summary"]
    print(f"  ✅ Test 6 PASS")

    print(f"\n📊 S-023 RootCauseAnalyzer 验收报告:")
    print(f"  D3 动机归因 (否定词): ✅")
    print(f"  D2 执行归因 (SIGKILL): ✅")
    print(f"  D5 能力归因 (基座上限): ✅")
    print(f"  多维度混合归因: ✅")
    print(f"  批量 + 趋势分析: ✅")
    print(f"  序列化: ✅")
    print(f"\n  🎉 S-023 RootCauseAnalyzer — ALL PASS")
