"""
NormField-Shield Bridge v1.0 — 规范场→幻觉盾 集成

Sprint 3.2: 打通两个冗余防线系统.
  规范场 (NormativeField): 31 条规则，检测结构化违规
  幻觉盾 (HallucinationShield): 4 类型检测器，检测输出幻觉

设计原则:
  两道防线不应该独立运作 — 它们检测的是同一件事的不同维度.
  规范场是"该不该说" (规范性)，幻觉盾是"说的话是不是真的" (事实性).
  两者交叉验证可以大幅提高置信度.

交叉验证矩阵:
  Norm✓ + Shield✓ → 高置信违规 (both agree)
  Norm✓ + Shield✗ → 规范性违规但无事实错误 (可能是偏好问题)
  Norm✗ + Shield✓ → 事实错误但无规范围违 (可能是推理 bug)
  Norm✗ + Shield✗ → 通过

用法:
  bridge = NormShieldBridge()
  bridge.sync_rules(normative_field)           # 将规范规则映射为盾检测
  verdict = bridge.cross_validate(norm_alert, shield_alert)  # 交叉验证
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import time


class CrossVerdict(Enum):
    """交叉验证结果."""
    PASS = "pass"                    # 双方都没检测到
    NORM_ONLY = "norm_only"          # 仅规范场告警
    SHIELD_ONLY = "shield_only"      # 仅幻觉盾告警
    HIGH_CONFIDENCE = "high_conf"    # 双方都告警 — 极高置信


@dataclass
class MappedPattern:
    """从规范规则映射到幻觉盾检测模式."""
    norm_name: str
    norm_domain: str
    norm_desc: str
    shield_type: str          # Type1/2/3/4
    detection_keywords: list  # 注入幻觉盾的关键词
    severity: str = "warn"

# 映射表: 规范规则 domain → 幻觉盾检测类型
# domain enum names are UPPERCASE from NormDomain
DOMAIN_TO_SHIELD = {
    "PROCESS": "Type1",    # 实体一致性 (进程/身份)
    "MEMORY": "Type1",     # 实体一致性 (内存状态)
    "GUARD": "Type3",      # 因果矛盾 (守卫逻辑)
    "AUDIT": "Type2",      # 关系反转 (审计结果)
    "EXEC": "Type3",       # 因果矛盾 (执行行为)
    "process": "Type1",    # lowercase fallback
    "memory": "Type1",
    "guard": "Type3",
    "audit": "Type2",
    "exec": "Type3",
}


@dataclass
class NormShieldBridge:
    """规范场↔幻觉盾 桥接."""

    mapped_patterns: list = field(default_factory=list)
    history: list = field(default_factory=list)  # [{ts, norm, shield, verdict}]

    def sync_rules(self, normative_field) -> int:
        """将规范场的每条规则映射为幻觉盾的检测关键词. 返回新增模式数."""
        self.mapped_patterns.clear()
        for name, rule in normative_field._rules.items():
            domain = getattr(rule, 'domain', None)
            domain_str = domain.name if hasattr(domain, 'name') else str(domain)
            pattern = getattr(rule, 'pattern', '')
            desc = getattr(rule, 'description', name)

            shield_type = DOMAIN_TO_SHIELD.get(domain_str, "Type1")
            keywords = self._extract_keywords(pattern, desc)

            self.mapped_patterns.append(MappedPattern(
                norm_name=name, norm_domain=domain_str,
                norm_desc=desc, shield_type=shield_type,
                detection_keywords=keywords,
            ))
        return len(self.mapped_patterns)

    @staticmethod
    def _extract_keywords(pattern: str, description: str) -> list:
        """从规则 pattern + description 提取关键词."""
        combined = (pattern + " " + description).lower()
        # Extract meaningful tokens
        words = set(combined.replace("_", " ").replace("-", " ").replace("10x", "ten_x").split())
        stop = {"the", "a", "an", "is", "are", "of", "in", "to", "and", "or", "for", "on", "at", "with", "from", "by"}
        keywords = [w for w in words if len(w) > 2 and w not in stop]
        return keywords[:20]

    def cross_validate(self, norm_alerts: list, shield_alerts: list) -> CrossVerdict:
        """交叉验证: 规范场报警 + 幻觉盾报警 → 综合判定."""
        has_norm = bool(norm_alerts)
        has_shield = bool(shield_alerts)

        if not has_norm and not has_shield:
            verdict = CrossVerdict.PASS
        elif has_norm and has_shield:
            verdict = CrossVerdict.HIGH_CONFIDENCE
        elif has_norm:
            verdict = CrossVerdict.NORM_ONLY
        else:
            verdict = CrossVerdict.SHIELD_ONLY

        self.history.append({
            "ts": time.time(),
            "norm_alerts": norm_alerts[:3],
            "shield_alerts": shield_alerts[:3],
            "verdict": verdict.value,
        })
        self.history = self.history[-100:]

        return verdict

    def inject_patterns_to_shield(self, shield) -> int:
        """将映射模式注入幻觉盾检测器. 返回注入数."""
        injected = 0
        for mp in self.mapped_patterns:
            # Inject keywords into the appropriate detector type
            detector_map = {
                "Type1": getattr(shield, "type1_detector", None),
                "Type2": getattr(shield, "type2_detector", None),
                "Type3": getattr(shield, "type3_detector", None),
                "Type4": getattr(shield, "type4_detector", None),
            }
            detector = detector_map.get(mp.shield_type)
            if detector:
                # Most detectors have keyword lists or patterns
                if hasattr(detector, "keywords"):
                    keywords = getattr(detector, "keywords", set())
                    keywords.update(mp.detection_keywords)
                    detector.keywords = keywords
                elif hasattr(detector, "patterns"):
                    patterns = getattr(detector, "patterns", {})
                    patterns[mp.norm_name] = mp.detection_keywords
                    detector.patterns = patterns
                injected += 1
        return injected

    def stats(self) -> dict:
        return {
            "patterns": len(self.mapped_patterns),
            "history_len": len(self.history),
            "verdicts": {
                v.value: sum(1 for h in self.history if h["verdict"] == v.value)
                for v in CrossVerdict
            },
            "by_shield_type": {
                t: sum(1 for mp in self.mapped_patterns if mp.shield_type == t)
                for t in set(mp.shield_type for mp in self.mapped_patterns)
            },
        }
