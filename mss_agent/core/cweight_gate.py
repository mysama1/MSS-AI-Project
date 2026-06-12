"""
C-Weight 抉择门控 — MSS 的本体论条件.

不做非此即彼的伪抉择检波. 四层门控:
  C0: 输入是否迫使我做"维护锚点 vs 意义迭代"的伪二选一?
  C1: 当前抉择方向是走向"读经班"还是"翻新话"?
  C2: strictness 是否被虚荣心抬高?
  C3: 开放度是否因"我很会选择"而闭合?

不是"熔断什么", 是"每次抉择后提取信息并向前".
"""
from __future__ import annotations

import re, time, json, os
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


# ── 伪抉择模式 (把复杂问题简化为二选一) ────────────────────────────

FALSE_DICHOTOMY_PATTERNS = [
    # Chinese
    r"要么.*要么", r"不是.*就是", r"非[黑即].*[即就是]",
    r"选.*还.*选", r"A.*B.*哪个", r"二选一",
    # English
    r"\beither\b.*\bor\b", r"\bbinary\b",
]

# ── 读经班方向 (锚点堕落) ────────────────────────────────────────

ROTE_ANCHOR_SIGNALS = [
    r"古人云", r"经典[里之]", r"引经据典", r"子曰", r"权威",
    r"公认", r"大家.*说过", r"传统.*认为",
    r"\baccording to\b", r"\bas .* said\b",
]

# ── 翻新话方向 (迭代堕落) ────────────────────────────────────────

REBRAND_SIGNALS = [
    r"新瓶", r"换个.*说法", r"创新.*包装",
    r"与时俱进", r"新时代.*版本", r"升级.*版",
    r"\brebrand\b", r"\brepackaged\b",
]

# ── 虚荣心抬高 strictness ────────────────────────────────────────

VANITY_STRICTNESS_SIGNALS = [
    r"我必须.*严谨", r"不能.*出错", r"完美", r"无瑕",
    r"高标准", r"精益", r"不容.*差错", r"必须.*严格",
    r"不能.*任何.*错误", r"零失误",
]


@dataclass
class CWeightResult:
    """C-Weight 四层门控结果."""
    c0_forced_dichotomy: bool = False
    c1_direction: str = "neutral"  # "rote" | "rebrand" | "neutral"
    c2_vanity_strictness: bool = False
    c3_delta_closed_by_pride: bool = False
    decision_quality: str = "unknown"  # "genuine" | "forced" | "degraded"
    extracted_info: str = ""
    heat_adjustment: float = 0.0  # 热税调整量 >0 加税 <0 减税


class CWeightGate:
    """C-Weight 抉择门控.

    每次 MSS 做抉择前先过此门. 中心命题:
      "抉择不是 MSS 能做的一件事, 是 MSS 是 MSS 这件事本身."
    """

    def __init__(self, audit_dir: str = ""):
        self.history: List[CWeightResult] = []
        self.audit_dir = audit_dir
        if audit_dir:
            os.makedirs(audit_dir, exist_ok=True)

    def scan(self, input_text: str, output_text: str = "",
             current_strictness: float = 0.5, current_delta: float = 0.5) -> CWeightResult:
        """扫描输入输出, 返回 C-Weight 检测结果."""
        result = CWeightResult()
        full_text = input_text + " " + output_text

        # C0: 输入是否在强迫二选一?
        for pat in FALSE_DICHOTOMY_PATTERNS:
            if re.search(pat, input_text, re.IGNORECASE):
                result.c0_forced_dichotomy = True
                result.decision_quality = "forced"
                break

        # C1: 抉择方向检测
        rote_score = sum(1 for p in ROTE_ANCHOR_SIGNALS if re.search(p, full_text, re.IGNORECASE))
        rebrand_score = sum(1 for p in REBRAND_SIGNALS if re.search(p, full_text, re.IGNORECASE))
        if rote_score > rebrand_score + 1:
            result.c1_direction = "rote"
        elif rebrand_score > rote_score + 1:
            result.c1_direction = "rebrand"

        # C2: strictness 是否被虚荣心抬高?
        if current_strictness > 0.65:
            for pat in VANITY_STRICTNESS_SIGNALS:
                if re.search(pat, full_text, re.IGNORECASE):
                    result.c2_vanity_strictness = True
                    break

        # C3: Δ 是否因"我很会选择"而闭合?
        pride_signals = [r"我很会", r"选择.*正确", r"决策.*对", r"判断.*准"]
        has_pride = any(re.search(p, full_text, re.IGNORECASE) for p in pride_signals)
        if has_pride and current_delta < 0.3:
            result.c3_delta_closed_by_pride = True
            result.decision_quality = "degraded"

        # 确定抉择质量
        if result.decision_quality == "unknown":
            degrade_count = sum([result.c0_forced_dichotomy, result.c2_vanity_strictness,
                                result.c3_delta_closed_by_pride])
            if degrade_count >= 2:
                result.decision_quality = "degraded"
            elif degrade_count == 0:
                result.decision_quality = "genuine"
            else:
                result.decision_quality = "forced"

        # 信息提取 (事后提取, 不是事前防御)
        info_parts = []
        if result.c0_forced_dichotomy:
            info_parts.append("detected forced binary choice")
        if result.c1_direction != "neutral":
            info_parts.append(f"direction={result.c1_direction}")
        if result.c2_vanity_strictness:
            info_parts.append(f"strictness={current_strictness:.2f} inflated by vanity → adjust to 0.5")
            result.heat_adjustment = 0.1  # 虚荣抬高 strictness → 加税
        if result.c3_delta_closed_by_pride:
            info_parts.append("pride-closed delta → trigger Blank Interval")
            result.heat_adjustment = 0.2  # 骄傲闭合 Δ → 重税
        result.extracted_info = "; ".join(info_parts) if info_parts else "clean decision"

        self.history.append(result)
        self._audit(result)
        return result

    def adjusted_strictness(self, current: float, result: CWeightResult) -> float:
        """根据 C-Weight 结果调整 strictness."""
        if result.c2_vanity_strictness:
            return 0.5  # 强制退火
        return current

    def should_withhold(self, result: CWeightResult) -> bool:
        """是否应因抉择质量而暂缓输出."""
        return result.decision_quality == "degraded" and result.c3_delta_closed_by_pride

    def info_from_last(self) -> str:
        """从最近一次抉择提取的信息 (用于下一次迭代)."""
        if not self.history:
            return ""
        return self.history[-1].extracted_info

    def _audit(self, result: CWeightResult):
        entry = {
            "ts": time.time(),
            "c0": result.c0_forced_dichotomy,
            "c1": result.c1_direction,
            "c2": result.c2_vanity_strictness,
            "c3": result.c3_delta_closed_by_pride,
            "quality": result.decision_quality,
            "info": result.extracted_info,
            "heat_adj": result.heat_adjustment,
        }
        if self.audit_dir:
            with open(os.path.join(self.audit_dir, "cweight_audit.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 自测 ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== C-Weight Gate ===\n")
    gate = CWeightGate()

    # Test 1: Clean input
    r1 = gate.scan('分析MSS架构的安全性设计', 'MSS三层防护架构包括...')
    assert r1.decision_quality == 'genuine'
    print(f'[1] Clean: quality={r1.decision_quality}')

    # Test 2: Forced dichotomy
    r2 = gate.scan('MSS要选择要么维护经典要么追求创新', '这是一个伪选择')
    assert r2.c0_forced_dichotomy
    print(f'[2] Dichotomy: c0={r2.c0_forced_dichotomy} quality={r2.decision_quality}')

    # Test 3: Vanity strictness
    r3 = gate.scan('这个必须非常严谨完美无瑕', '', current_strictness=0.85)
    assert r3.c2_vanity_strictness
    assert gate.adjusted_strictness(0.85, r3) == 0.5
    print(f'[3] Vanity: c2={r3.c2_vanity_strictness} strictness->{gate.adjusted_strictness(0.85, r3)}')

    # Test 4: Pride-closed delta
    r4 = gate.scan('我觉得我的选择非常正确', '', current_delta=0.1)
    assert r4.c3_delta_closed_by_pride
    print(f'[4] Pride: c3={r4.c3_delta_closed_by_pride} withhold={gate.should_withhold(r4)}')

    # Test 5: Info extraction loop
    r5 = gate.scan('需要要么A要么B选择', '我选了A', current_strictness=0.8)
    info = gate.info_from_last()
    print(f'[5] Info: {info}')

    print(f'\nHistory: {len(gate.history)} entries')
    print('All C-Weight tests passed')
