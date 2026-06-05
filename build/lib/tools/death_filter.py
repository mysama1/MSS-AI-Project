#!/usr/bin/env python3
"""
D5-036: MSS 死亡过滤器协议 v1.0
检测项目/理论/公司的"意义死亡"风险 — 基于MSS意义黑洞模型 (H148-H155)
"""
import os, json, time, hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum

class DeathStage(Enum):
    ALIVE = "ALIVE"                  # 意义健康
    ENTROPY_ACCUMULATING = "ENTROPY_ACCUMULATING"  # 熵累积
    MEANING_LEAKING = "MEANING_LEAKING"    # 意义泄漏
    EVENT_HORIZON_APPROACHING = "EVENT_HORIZON_APPROACHING"  # 接近视界
    CROSSED_HORIZON = "CROSSED_HORIZON"  # 已穿越视界
    SINGULARITY = "SINGULARITY"           # 奇点（意义死亡）

class DeathSignal(Enum):
    """死亡信号类型"""
    NARRATIVE_SUBSTITUTION = "narrative_substitution"   # 故事替代产品
    GROWTH_WITHOUT_MEANING = "growth_without_meaning"   # 增长无意义
    DEPENDENCY_INVERSION = "dependency_inversion"       # 依赖反转
    THERMAL_RUNAWAY = "thermal_runaway"                 # 热税逃逸
    TRUST_COLLAPSE = "trust_collapse"                   # 信任崩塌
    MEANING_INFLATION = "meaning_inflation"             # 意义通胀
    COMPLEXITY_DEATH = "complexity_death"               # 复杂度致死
    ECHO_CHAMBER = "echo_chamber"                       # 回音壁效应

# 死亡信号检测规则
DEATH_SIGNALS = {
    DeathSignal.NARRATIVE_SUBSTITUTION: {
        "threshold": 0.7,
        "indicators": [
            "story > product", "narrative > revenue", "marketing > engineering",
            "vision without execution", "promises without delivery",
            "故事大于产品", "叙事大于收入", "只有愿景无执行",
        ],
        "axiom": "A2",
        "time_to_death": "12-24 months"
    },
    DeathSignal.GROWTH_WITHOUT_MEANING: {
        "threshold": 0.6,
        "indicators": [
            "users growing, revenue declining", "scale without profit",
            "expansion without purpose", "vanity metrics",
            "用户增长收入下降", "规模扩张无意义锚定",
        ],
        "axiom": "A3",
        "time_to_death": "6-18 months"
    },
    DeathSignal.THERMAL_RUNAWAY: {
        "threshold": 0.8,
        "indicators": [
            "burn rate > revenue", "cost per user > LTV",
            "infrastructure cost > value created", "exponential waste",
            "烧钱速度超收入", "基础设施开销超价值创造",
        ],
        "axiom": "A3",
        "time_to_death": "3-12 months"
    },
    DeathSignal.TRUST_COLLAPSE: {
        "threshold": 0.9,
        "indicators": [
            "transparency failure", "hidden fees", "data breach",
            "broken promises", "community exodus",
            "信任透明度崩溃", "隐瞒收费", "数据泄露",
        ],
        "axiom": "A1",
        "time_to_death": "1-6 months"
    },
    DeathSignal.COMPLEXITY_DEATH: {
        "threshold": 0.65,
        "indicators": [
            "1000+ microservices", "nobody understands the system",
            "legacy code > active code", "technical debt > capacity",
            "无人理解系统", "遗留代码超级活跃代码",
        ],
        "axiom": "A6",
        "time_to_death": "6-24 months"
    },
    DeathSignal.ECHO_CHAMBER: {
        "threshold": 0.5,
        "indicators": [
            "only positive feedback", "no critics tolerated",
            "groupthink", "confirmation bias loop",
            "只有正面反馈", "不容批评", "群体思维",
        ],
        "axiom": "A5",
        "time_to_death": "12-36 months"
    },
}

@dataclass
class DeathFilterResult:
    entity_name: str
    stage: DeathStage
    signals_detected: List[DeathSignal]
    risk_score: float
    estimated_remaining_life: str
    axiom_violations: List[str]
    rescue_possible: bool
    rescue_suggestions: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class DeathFilter:
    """意义死亡过滤器 — 检测实体是否正在穿越意义黑洞事件视界"""

    def analyze_text(self, text: str, entity_name: str = "Unknown") -> DeathFilterResult:
        """分析文本中的死亡信号"""
        text_lower = text.lower()
        detected = []
        violations = []

        for signal, config in DEATH_SIGNALS.items():
            score = 0
            matches = 0
            for indicator in config["indicators"]:
                if indicator.lower() in text_lower:
                    matches += 1
                    score += 1 / len(config["indicators"])

            if score >= config["threshold"]:
                detected.append(signal)
                violations.append(config["axiom"])

        # 计算风险评分
        if not detected:
            risk = 0
        else:
            risk = min(100, sum(
                DEATH_SIGNALS[s]["threshold"] * 100 for s in detected
            ) / len(detected) + len(detected) * 10)

        # 判断死亡阶段
        stage = self._determine_stage(detected)
        remaining = self._estimate_remaining(stage, detected)
        rescue, suggestions = self._assess_rescue(stage, detected)

        return DeathFilterResult(
            entity_name=entity_name,
            stage=stage,
            signals_detected=detected,
            risk_score=round(risk, 1),
            estimated_remaining_life=remaining,
            axiom_violations=list(set(violations)),
            rescue_possible=rescue,
            rescue_suggestions=suggestions,
        )

    def _determine_stage(self, signals: List[DeathSignal]) -> DeathStage:
        if not signals:
            return DeathStage.ALIVE
        critical = {DeathSignal.TRUST_COLLAPSE, DeathSignal.THERMAL_RUNAWAY}
        if critical & set(signals):
            if DeathSignal.TRUST_COLLAPSE in signals:
                return DeathStage.CROSSED_HORIZON
            return DeathStage.EVENT_HORIZON_APPROACHING
        if len(signals) >= 3:
            return DeathStage.MEANING_LEAKING
        return DeathStage.ENTROPY_ACCUMULATING

    def _estimate_remaining(self, stage: DeathStage, signals: List[DeathSignal]) -> str:
        if stage == DeathStage.ALIVE:
            return "Indefinite"
        times = [DEATH_SIGNALS[s]["time_to_death"] for s in signals]
        # Take the shortest estimate
        return min(times, key=lambda t: int(t.split('-')[0]))

    def _assess_rescue(self, stage: DeathStage, signals: List[DeathSignal]) -> tuple:
        if stage in (DeathStage.ALIVE, DeathStage.ENTROPY_ACCUMULATING):
            return True, ["Monitor entropy", "Audit meaning anchors quarterly"]

        suggestions = []
        if DeathSignal.TRUST_COLLAPSE in signals:
            suggestions.append("RADICAL TRANSPARENCY: Publish all decisions and financials")
        if DeathSignal.THERMAL_RUNAWAY in signals:
            suggestions.append("HEAT TAX CUT: Reduce burn rate by 50% immediately")
        if DeathSignal.GROWTH_WITHOUT_MEANING in signals:
            suggestions.append("MEANING ANCHOR: Redefine growth metric as meaning-per-user")
        if DeathSignal.COMPLEXITY_DEATH in signals:
            suggestions.append("DECOMPLEXIFY: Delete 30% of codebase, merge microservices")
        if DeathSignal.ECHO_CHAMBER in signals:
            suggestions.append("OPEN BORDERS: Hire external critics, read negative reviews daily")

        if stage in (DeathStage.CROSSED_HORIZON, DeathStage.SINGULARITY):
            return False, suggestions + ["Event horizon crossed. Only radical restructure can save."]

        return True, suggestions


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="MSS Death Filter Protocol (D5-036)")
    ap.add_argument("target", help="Text or file to analyze")
    ap.add_argument("--name", "-n", default="Unknown", help="Entity name")
    args = ap.parse_args()

    if os.path.isfile(args.target):
        with open(args.target, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        args.name = os.path.basename(args.target)
    else:
        text = args.target

    filter = DeathFilter()
    result = filter.analyze_text(text, args.name)

    print(f"Entity: {result.entity_name}")
    print(f"Stage: {result.stage.value}")
    print(f"Risk: {result.risk_score}/100")
    print(f"Remaining: {result.estimated_remaining_life}")
    print(f"Violations: {', '.join(result.axiom_violations) if result.axiom_violations else 'None'}")
    print(f"Signals: {[s.value for s in result.signals_detected] if result.signals_detected else 'None'}")
    print(f"Rescue: {'YES' if result.rescue_possible else 'NO'}")
    for s in result.rescue_suggestions:
        print(f"  → {s}")