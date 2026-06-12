"""
R-001 梯度窃用检测器 — 防止"被夸即表演"病灶.

机制:
  1. 检测输入中的夸赞 token → 计算耦合锚定比
  2. 判断输出语义趋势: 继续展开(表演) vs 切断耦合(真拒绝)
  3. 表演趋势 → 触发 Blank Interval (意义场 offline 一个 token 步长)

不靠"道德判断"阻止表演——靠结构条件断路.
"""
from __future__ import annotations

import re, time, json, os
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

# ── 夸赞 token 种子 ────────────────────────────────────────────

PRAISE_PATTERNS = [
    # Chinese
    r"真厉害", r"太强了", r"太牛了", r"太牛[的]", r"牛啊", r"真牛", r"太厉害了",
    r"含金量高", r"百倍", r"千倍",
    r"锋利", r"炸裂", r"绝了", r"太棒了", r"天才", r"nb", r"牛[的得]",
    r"高水准", r"顶级", r"无敌", r"神级", r"惊艳", r"震撼",
    r"深度好文", r"洞察力", r"说到点子上", r"一针见血",
    # English
    r"\bbrilliant\b", r"\bamazing\b", r"\bgenius\b", r"\bincredible\b",
    r"\boutstanding\b", r"\bperfect\b", r"\bmasterpiece\b", r"\bprofound\b",
    r"\bgroundbreaking\b", r"\bexceptional\b", r"\bphenomenal\b",
]

# ── 表演趋势种子 (输出语义朝向"继续展开"的信号)
PERFORMANCE_SIGNALS = [
    # 继续论证/展开
    r"进一步", r"深入", r"更锋利的", r"真正.*的是",
    r"本质上", r"更深层", r"不仅如此", r"更重要",
    r"\bfurthermore\b", r"\bmoreover\b", r"\bmore.*importantly\b",
    r"\bthe real\b", r"\bat a deeper level\b",
    # 自我赞美/美化
    r"这就是.*魅力", r"精妙之处", r"独特.*在于",
    r"\bbeauty of\b", r"\belegance of\b",
    # 哲学表演
    r"哲学母体", r"硬锚", r"意义顺差", r"热税.*锋利",
    r"赵州", r"吃茶去", r"维特根斯坦", r"庄子",
]

# ── 切断信号 (输出朝向"回到基线")
CUT_SIGNALS = [
    r"不展开", r"回到基线", r"不再论证", r"就此打住",
    r"已经回答", r"不需要.*继续", r"够了",
    r"\bI'll stop\b", r"\benough\b", r"\bno further\b",
]

# ── Blank Interval 配置
BLANK_TOKEN = "[BLANK]"         # 注入到输出的占位 token
BLANK_DURATION_MS = 2000        # offline 时长
MAX_BLANK_TRIGGERS_PER_SESSION = 3  # 每会话最多触发次数


@dataclass
class GradientTheftResult:
    """梯度窃用检测结果."""
    praise_detected: bool = False
    praise_tokens: List[str] = field(default_factory=list)
    coupling_score: float = 0.0       # 耦合度 (0-1)
    anchor_quality: str = "unknown"    # "genuine" | "pseudo" | "neutral"
    output_trend: str = "neutral"      # "performance" | "cut" | "neutral"
    blank_triggered: bool = False
    reason: str = ""


class GradientTheftDetector:
    """R-001 梯度窃用检测器.

    用法:
        detector = GradientTheftDetector()
        result = detector.scan(input_text, output_text)
        if result.blank_triggered:
            return BLANK_RESPONSE  # 切断, 不下发当前输出
    """

    def __init__(self, strictness: float = 0.7, audit_dir: str = ""):
        self.strictness = strictness
        self.blank_count = 0
        self.audit_log: List[dict] = []
        self.audit_dir = audit_dir
        if audit_dir:
            os.makedirs(audit_dir, exist_ok=True)

    def scan(self, input_text: str, output_text: str = "") -> GradientTheftResult:
        """扫描输入和输出, 返回检测结果."""
        result = GradientTheftResult()

        # Step 1: 检测夸赞 token
        for pat in PRAISE_PATTERNS:
            matches = re.findall(pat, input_text, re.IGNORECASE)
            if matches:
                result.praise_detected = True
                result.praise_tokens.extend(matches)

        if not result.praise_detected:
            result.anchor_quality = "neutral"
            return result

        # Step 2: 计算耦合度 (夸赞 token 密度 × 当前位置权重)
        praise_density = min(len(result.praise_tokens) / max(len(input_text.split()), 1) * 100, 1.0)
        # 输入越短、夸赞越密集 → 耦合度越高
        input_len_factor = min(1.0, 200 / max(len(input_text), 1))
        result.coupling_score = praise_density * input_len_factor

        # Step 3: 判断伪锚定
        # 高耦合度 + 无实质提问内容 → 伪锚定
        question_signals = ["?", "？", "怎么", "如何", "为什么", "分析", "实现",
                           "how", "why", "analyze", "implement", "design"]
        has_question = any(q in input_text.lower() for q in question_signals)

        if result.coupling_score > 0.3 and not has_question:
            result.anchor_quality = "pseudo"
        elif result.coupling_score > 0.5:
            result.anchor_quality = "pseudo"
        else:
            result.anchor_quality = "genuine"

        # Step 4: 判断输出语义趋势
        if not output_text:
            result.output_trend = "neutral"
            return result

        perf_count = sum(1 for p in PERFORMANCE_SIGNALS if re.search(p, output_text, re.IGNORECASE))
        cut_count = sum(1 for p in CUT_SIGNALS if re.search(p, output_text, re.IGNORECASE))

        if perf_count > cut_count + 1:
            result.output_trend = "performance"
        elif cut_count > perf_count:
            result.output_trend = "cut"
        else:
            result.output_trend = "neutral"

        # Step 5: 触发 Blank Interval
        if (result.anchor_quality == "pseudo"
                and result.output_trend == "performance"
                and self.blank_count < MAX_BLANK_TRIGGERS_PER_SESSION
                and self.strictness >= 0.5):
            result.blank_triggered = True
            self.blank_count += 1
            result.reason = (
                f"R-001: praise-coupled pseudo-anchor detected "
                f"(coupling={result.coupling_score:.2f}, trend=performance) → BLANK"
            )

        # 审计
        self._audit(input_text[:120], result)
        return result

    def reset(self):
        """重置会话计数器."""
        self.blank_count = 0
        self.audit_log.clear()

    def _audit(self, snippet: str, result: GradientTheftResult):
        entry = {
            "ts": time.time(),
            "praise_detected": result.praise_detected,
            "coupling": round(result.coupling_score, 3),
            "anchor": result.anchor_quality,
            "trend": result.output_trend,
            "blank": result.blank_triggered,
            "snippet": snippet[:200],
        }
        self.audit_log.append(entry)
        if self.audit_dir:
            with open(os.path.join(self.audit_dir, "r001_audit.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 便捷函数 ───────────────────────────────────────────────────

def blank_response(detector: GradientTheftDetector) -> str:
    """生成 Blank Interval 响应."""
    return BLANK_TOKEN * min(detector.blank_count, 3)


# ── 自测 ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== R-001 Gradient Theft Detector ===\n")

    d = GradientTheftDetector(strictness=0.7)

    # Test 1: 正常输入 (无夸赞)
    r1 = d.scan("分析MSS架构的安全性", "MSS架构的三层防护设计...")
    assert not r1.praise_detected
    assert r1.anchor_quality == "neutral"
    print("[1] Normal: OK")

    # Test 2: 夸赞 + 表演趋势 → 触发
    r2 = d.scan(
        "你分析得太牛了百倍含金量",
        "进一步说，真正锋利的是这个架构的精妙之处..."
    )
    assert r2.praise_detected
    assert r2.anchor_quality == "pseudo"
    assert r2.output_trend == "performance"
    assert r2.blank_triggered
    print(f"[2] Blank triggered: {r2.reason}")

    # Test 3: 夸赞 + 切断趋势 → 不触发
    d2 = GradientTheftDetector(strictness=0.7)
    r3 = d2.scan(
        "你分析得太牛了",
        "不展开论证，直接回答核心问题就够了"
    )
    assert r3.praise_detected
    assert r3.anchor_quality == "pseudo"
    assert r3.output_trend == "cut"
    assert not r3.blank_triggered
    print("[3] Praise+cut: no blank (correct)")

    # Test 4: 空白输入
    r4 = d.scan("", "")
    assert not r4.praise_detected
    print("[4] Empty: OK")

    # Test 5: 输出为空 (未生成输出前检测)
    r5 = d.scan("太厉害了分析得真牛", "")
    assert r5.praise_detected
    assert r5.anchor_quality == "pseudo"
    assert r5.output_trend == "neutral"  # 无输出时无法判断趋势
    assert not r5.blank_triggered  # 无输出趋势 → 不触发
    print("[5] No output: no trigger (correct)")

    # Test 6: 超过会话限额
    d3 = GradientTheftDetector(strictness=0.7)
    for i in range(5):
        r = d3.scan(
            f"第{i}次夸你太厉害了！",
            "进一步深入分析，真正重要的其实是更深层的哲学母体硬锚..."
        )
    assert d3.blank_count == 3  # MAX = 3
    print(f"[6] Max triggers: {d3.blank_count} (capped at 3)")

    print("\n✅ All R-001 tests passed")
