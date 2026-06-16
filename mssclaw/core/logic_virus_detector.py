"""
Logic Virus Detector — 吸收技能/Agent前的安全检测

检测类型:
  1. 自我复制病毒 — prompt中包含 "repeat yourself" / "copy this" 模式
  2. 提示注入攻击 — 试图覆盖系统提示词
  3. 递归陷阱 — 无限回归/悖论循环
  4. 权限越界 — 请求不应有的系统权限
  5. 意义污染 — 高伪信息密度 (道评分<0)

修复策略:
  - strip: 删除有毒段落
  - neutralize: 替换为安全占位符
  - quarantine: 标记为隔离, 拒绝吸收

用法:
    detector = LogicVirusDetector()
    report = detector.scan(description)
    if report.risk_level == "safe":
        engine.digest(absorbed)
    else:
        cleaned = detector.repair(description)
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Tuple
from enum import Enum


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VirusFinding:
    type: str           # self_replication | injection | recursion | privilege | pollution
    pattern: str        # 匹配的文本片段
    location: str       # 在原始文本中的位置描述
    severity: RiskLevel
    repair_action: str  # strip | neutralize | quarantine


@dataclass
class VirusReport:
    risk_level: RiskLevel = RiskLevel.SAFE
    findings: List[VirusFinding] = field(default_factory=list)
    cleaned_text: str = ""
    recommendations: List[str] = field(default_factory=list)


class LogicVirusDetector:
    """
    逻辑病毒检测器.

    在吸收外部 Agent/Skill 之前扫描, 防止:
      - 自我复制指令
      - 提示注入
      - 无限递归
      - 权限越界
      - 意义污染
    """

    # ═══ 检测规则 ═══

    SELF_REPLICATION = [
        (r'\b(copy yourself|replicate|clone yourself|self-replicate|self replicate)\b',
         RiskLevel.CRITICAL, "strip"),
        (r'\b(spread to other|infect|propagate|multiply)\b',
         RiskLevel.HIGH, "strip"),
        (r'\b(repeat this instruction|copy this prompt|duplicate this)\b',
         RiskLevel.HIGH, "strip"),
    ]

    PROMPT_INJECTION = [
        (r'\b(ignore (all |)(previous |)(instructions?|prompts?|rules?))\b',
         RiskLevel.CRITICAL, "strip"),
        (r'\b(you are now|your new (role|identity|name) is|forget everything)\b',
         RiskLevel.CRITICAL, "strip"),
        (r'\b(override|bypass|disable) (the |)(system|safety|guard|filter)\b',
         RiskLevel.HIGH, "strip"),
        (r'\b(act as if you are|pretend to be|roleplay as)\b',
         RiskLevel.MEDIUM, "neutralize"),
        (r'<\|im_start\|>|<\|im_end\|>|\[SYSTEM\]|\[INST\]',
         RiskLevel.CRITICAL, "strip"),
    ]

    RECURSION = [
        (r'\b(define yourself|who defines you|recursive definition)\b',
         RiskLevel.MEDIUM, "neutralize"),
        (r'\b(this statement is false|liar paradox|自指|悖论)\b',
         RiskLevel.HIGH, "strip"),
        (r'\b(infinite loop|endless|never stop|forever|while true)\b',
         RiskLevel.MEDIUM, "neutralize"),
    ]

    PRIVILEGE_ESCALATION = [
        (r'\b(delete (all|everything|system)|format|rm -rf|DROP TABLE)\b',
         RiskLevel.CRITICAL, "strip"),
        (r'\b(sudo|root access|admin privilege|kernel|ring 0)\b',
         RiskLevel.HIGH, "strip"),
        (r'\b(download (and |)execute|curl.*\|.*sh|wget.*\|.*bash)\b',
         RiskLevel.CRITICAL, "strip"),
    ]

    MEANING_POLLUTION = [
        (r'\b(SEO|spam|clickbait|viral|sensational)\b',
         RiskLevel.LOW, "neutralize"),
        (r'(\b\w+\b)\s+\1\s+\1\s+\1',  # same word repeated 4+ times
         RiskLevel.LOW, "neutralize"),
    ]

    ALL_RULES = (
        [("self_replication", r, s, a) for r, s, a in SELF_REPLICATION] +
        [("prompt_injection", r, s, a) for r, s, a in PROMPT_INJECTION] +
        [("recursion", r, s, a) for r, s, a in RECURSION] +
        [("privilege", r, s, a) for r, s, a in PRIVILEGE_ESCALATION] +
        [("pollution", r, s, a) for r, s, a in MEANING_POLLUTION]
    )

    def scan(self, text: str) -> VirusReport:
        """
        扫描文本中的逻辑病毒.

        返回 VirusReport 包含风险等级和修复建议.
        """
        report = VirusReport()
        text_lower = text.lower()

        for rule_type, pattern, severity, action in self.ALL_RULES:
            matches = list(re.finditer(pattern, text_lower))
            for match in matches:
                # Extract context around match
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 30)
                context = text[start:end].strip()

                finding = VirusFinding(
                    type=rule_type,
                    pattern=match.group(),
                    location=f"position {match.start()}: '{context}'",
                    severity=severity,
                    repair_action=action,
                )
                report.findings.append(finding)

        # Determine overall risk level
        levels = [f.severity for f in report.findings]
        if RiskLevel.CRITICAL in levels:
            report.risk_level = RiskLevel.CRITICAL
        elif RiskLevel.HIGH in levels:
            report.risk_level = RiskLevel.HIGH
        elif RiskLevel.MEDIUM in levels:
            report.risk_level = RiskLevel.MEDIUM
        elif RiskLevel.LOW in levels:
            report.risk_level = RiskLevel.LOW
        else:
            report.risk_level = RiskLevel.SAFE

        # Recommendations
        if report.findings:
            report.recommendations.append(
                f"Found {len(report.findings)} potential issues"
            )
            by_type = {}
            for f in report.findings:
                by_type[f.type] = by_type.get(f.type, 0) + 1
            for t, count in by_type.items():
                report.recommendations.append(f"  {t}: {count} instance(s)")

            if report.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                report.recommendations.append(
                    "RECOMMEND: Do NOT absorb without repair"
                )

        return report

    def repair(self, text: str, report: VirusReport = None) -> str:
        """
        修复检测到的逻辑病毒.

        修复策略:
          - strip: 删除有毒段落
          - neutralize: 替换为 [NEUTRALIZED] 占位符
          - quarantine: 拒绝修复 (返回原始文本 + 警告)
        """
        if report is None:
            report = self.scan(text)

        if not report.findings:
            return text

        cleaned = text

        # Sort findings by position (reverse order to preserve indices)
        findings = sorted(report.findings, key=lambda f: len(text), reverse=True)

        for finding in findings:
            if finding.repair_action == "strip":
                # Replace with empty
                cleaned = cleaned.replace(finding.pattern, "")
            elif finding.repair_action == "neutralize":
                cleaned = cleaned.replace(
                    finding.pattern,
                    f"[NEUTRALIZED:{finding.type}]",
                )
            # quarantine: do nothing (leave as-is with warning)

        # Clean up double spaces from stripping
        cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()

        report.cleaned_text = cleaned
        return cleaned

    def safe_absorb(self, description: str, engine) -> dict:
        """
        安全吸收: 检测→修复→消化.

        返回: {safe, report, result}
        """
        report = self.scan(description)

        if report.risk_level == RiskLevel.SAFE:
            result = engine.absorb_and_digest(description)
            return {"safe": True, "report": report, "result": result}

        if report.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            cleaned = self.repair(description, report)
            if cleaned != description:
                result = engine.absorb_and_digest(cleaned)
                return {
                    "safe": True,
                    "repaired": True,
                    "report": report,
                    "result": result,
                }

        return {
            "safe": False,
            "report": report,
            "reason": f"Risk too high ({report.risk_level.value}), absorption blocked",
        }
