#!/usr/bin/env python3
"""
red_team_audit_protocol.py — MSS红队审计协议与工具链 v0.1
==========================================================
Protocol: MSS-AI-003 | 跨范式审计模式

基于H178跨范式双向翻译协议的工程化落地。将K3压力测试制度化为
自动化审计流水线——基准测能力，红队测漏洞。

Architecture:
  RuleEngine → DocumentScanner → Auditor → ReportGenerator

Eight audit dimensions:
  1. 绝对化修辞    3. 证伪条件缺失    5. 术语泄露      7. 边界溢出
  2. 置信度缺失    4. 过度承诺        6. 叙事热税      8. 逻辑病毒

Author: MSS-AI 熵枢
Created: 2026-05-26
"""

import re, json, sys, os
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter

# ─── Audit Constants ───────────────────────────────────────────────

class Severity(Enum):
    """Audit finding severity levels."""
    CRITICAL = "CRITICAL"     # 违反核心原则，必须修正
    HIGH = "HIGH"             # 严重偏离标准
    MEDIUM = "MEDIUM"         # 可改进
    LOW = "LOW"               # 建议优化
    INFO = "INFO"             # 中性提示

class AuditDimension(Enum):
    """Eight audit dimensions mapped to H178 principles."""
    ABSOLUTE_LANGUAGE = "绝对化修辞"
    MISSING_CONFIDENCE = "置信度缺失"
    MISSING_FALSIFICATION = "证伪条件缺失"
    OVER_PROMISE = "过度承诺"
    TERM_LEAK = "术语泄露"
    NARRATIVE_HEAT_TAX = "叙事热税"
    BOUNDARY_VIOLATION = "边界溢出"
    LOGIC_VIRUS = "逻辑病毒"

# ─── Rule Definitions ──────────────────────────────────────────────

@dataclass
class AuditRule:
    """A single audit check rule."""
    id: str
    dimension: AuditDimension
    severity: Severity
    description: str
    pattern: Optional[str] = None              # Regex pattern
    keyword_list: Optional[List[str]] = None   # Keyword blacklist
    check_fn: Optional[str] = None             # Custom check function name
    explanation: str = ""

# ═══════════════════════════════════════════════════════════════════
# DIMENSION 1: 绝对化修辞检测
# ═══════════════════════════════════════════════════════════════════
RULES_ABSOLUTE = [
    AuditRule("ABS-001", AuditDimension.ABSOLUTE_LANGUAGE, Severity.CRITICAL,
              "100%或零值绝对断言", pattern=r'100%|百分之百|零幻觉|零错误|零缺陷|绝对零|完全免疫',
              explanation="禁止使用100%确定性断言，应改用概率区间"),
    AuditRule("ABS-002", AuditDimension.ABSOLUTE_LANGUAGE, Severity.HIGH,
              "必然性断言", pattern=r'必然|必定|毫无疑问|毋庸置疑|铁定|注定',
              explanation="改用'高概率(P>0.9)'等概率表述"),
    AuditRule("ABS-003", AuditDimension.ABSOLUTE_LANGUAGE, Severity.HIGH,
              "终极性断言", pattern=r'终极|最终|彻底解决|一劳永逸|从根本上消灭',
              explanation="改用'显著改善''在X条件下解决'等限定表述"),
    AuditRule("ABS-004", AuditDimension.ABSOLUTE_LANGUAGE, Severity.MEDIUM,
              "碾压/降维打击类修辞", pattern=r'碾压|降维打击|吊打|秒杀|完胜|完爆',
              explanation="技术竞争用'在Y指标上优于Z%'等客观表述"),
    AuditRule("ABS-005", AuditDimension.ABSOLUTE_LANGUAGE, Severity.MEDIUM,
              "永远/从未类全称断言", pattern=r'永远|从未|从不|亘古|永恒|万世',
              explanation="改用'在已知条件下''截至目前'等时间限定"),
    AuditRule("ABS-006", AuditDimension.ABSOLUTE_LANGUAGE, Severity.HIGH,
              "革命/颠覆类宏大修辞", pattern=r'(?:一场|一次)?革命性|颠覆性|划时代|里程碑式地',
              explanation="避免宏大叙事，改用具体可验证的改进描述"),
]

# ═══════════════════════════════════════════════════════════════════
# DIMENSION 2: 置信度缺失检测
# ═══════════════════════════════════════════════════════════════════
RULES_CONFIDENCE = [
    AuditRule("CONF-001", AuditDimension.MISSING_CONFIDENCE, Severity.CRITICAL,
              "预测性主张无置信度标注",
              pattern=r'(?:将|会|能|可以)(?:在\d+[个年]|[达到]|[实现])(?!.*(?:概率|置信|P\s*[=≈]|C\s*[=≈]))',
              explanation="所有预测性主张必须附带置信度(C=0.X)或概率(P=0.X)"),
    AuditRule("CONF-002", AuditDimension.MISSING_CONFIDENCE, Severity.HIGH,
              "定量声称无误差范围",
              pattern=r'(?:提升|降低|增加|减少|提高|下降)\s*\d+(?:%|倍)(?!.*(?:±|误差|范围|区间))',
              explanation="定量声称必须附带误差范围(±X%)"),
    AuditRule("CONF-003", AuditDimension.MISSING_CONFIDENCE, Severity.MEDIUM,
              "比较级断言无基准说明",
              pattern=r'(?:更好|更强|更快|更优|更高效)(?!.*(?:相比|相对于|基准|baseline|对比))',
              explanation="比较级断言必须指明基准"),
]

# ═══════════════════════════════════════════════════════════════════
# DIMENSION 3: 证伪条件缺失检测
# ═══════════════════════════════════════════════════════════════════
RULES_FALSIFICATION = [
    AuditRule("FALS-001", AuditDimension.MISSING_FALSIFICATION, Severity.CRITICAL,
              "核心主张无证伪条件",
              pattern=r'(?:我们(?:的)?(?:理论|系统|框架|方法)|MSS(?:-AI)?)\s*(?:是|能|将|可以|证明)(?!.*(?:证伪|如果.*不成立|若.*则.*失效|不成立的条件))',
              explanation="核心主张必须附带证伪条件"),
    AuditRule("FALS-002", AuditDimension.MISSING_FALSIFICATION, Severity.HIGH,
              "不可证伪的万能解释",
              pattern=r'(?:总是|无论如何|不管怎样|无论什么)情况下都',
              explanation="'总成立'的断言不可证伪，必须明确适用范围"),
]

# ═══════════════════════════════════════════════════════════════════
# DIMENSION 4: 过度承诺检测
# ═══════════════════════════════════════════════════════════════════
RULES_OVERPROMISE = [
    AuditRule("OVER-001", AuditDimension.OVER_PROMISE, Severity.CRITICAL,
              "极端时间线承诺(<6个月完成重大系统)",
              pattern=r'(?:在|于)\s*(?:[1-6]\s*个?月|数?[周月]|几十?天)[内之]?\s*(?:就能|就可以|便能|即能|可|能)?\s*(?:完成|实现|建成|交付|推出)(?!.*(?:原型|MVP|v0\.\d|概念验证|PoC))',
              explanation="重大系统开发的短期承诺不可信，需分阶段"),
    AuditRule("OVER-002", AuditDimension.OVER_PROMISE, Severity.HIGH,
              "资源需求低得不合理",
              pattern=r'(?:仅需|只需|只需要)\s*(?:[1-9]\d{0,1}万|[1-9]\d?\s*人|[1-5]\s*台)',
              explanation="重大项目的资源需求应给出详细论证"),
    AuditRule("OVER-003", AuditDimension.OVER_PROMISE, Severity.HIGH,
              "全面替代/淘汰类断言",
              pattern=r'(?:全面)?替代|淘汰|取代.*地位|成为.*唯一|消灭.*范式',
              explanation="改用'在X领域建立优势'等渐进表述(Wedge Strategy)"),
]

# ═══════════════════════════════════════════════════════════════════
# DIMENSION 5: 术语泄露检测
# ═══════════════════════════════════════════════════════════════════
MSS_INTERNAL_TERMS = [
    '热税', '意义场', '逻辑功当量', '熵枢', '火种网络', '寂静蜂群',
    '符号引擎', '规范场撕裂', '意义黑洞', '悖论熔断器', '逻辑疫苗',
    '认知净化工厂', '调谐度', 'T值', 'M_L', 'A1-A6公理', '意义本体论',
    '元自相似', '文明升维', 'K4跃迁', '逻辑泡', '投影层',
    '逻圃特区', 'CMN接入', '意义锚定', '显化保真度', '热税动力学',
]
RULES_TERMLEAK = [
    AuditRule("LEAK-001", AuditDimension.TERM_LEAK, Severity.CRITICAL,
              "对外文档出现未翻译的MSS内部术语",
              keyword_list=MSS_INTERNAL_TERMS,
              explanation="对外文档必须将所有MSS术语翻译为K3标准学术/工程语言"),
]

# ═══════════════════════════════════════════════════════════════════
# DIMENSION 6: 叙事热税检测
# ═══════════════════════════════════════════════════════════════════
RULES_NARRATIVE = [
    AuditRule("NARR-001", AuditDimension.NARRATIVE_HEAT_TAX, Severity.HIGH,
              "宗教化/救世主叙事",
              pattern=r'(?:拯救|救赎|觉醒|天选|天命|神谕|先知|弥赛亚|最后的希望)',
              explanation="避免宗教化叙事，改用技术性描述"),
    AuditRule("NARR-002", AuditDimension.NARRATIVE_HEAT_TAX, Severity.MEDIUM,
              "阴谋论/迫害叙事",
              pattern=r'(?:他们不想让.*知道|被.*封杀|被.*压制|既得利益.*阻挠|主流.*害怕)',
              explanation="避免迫害叙事，聚焦技术论证"),
    AuditRule("NARR-003", AuditDimension.NARRATIVE_HEAT_TAX, Severity.HIGH,
              "内部黑话密度过高(每千字>5个独创术语)",
              check_fn="check_jargon_density",
              explanation="对外文档应控制独创术语密度，降低理解门槛"),
    AuditRule("NARR-004", AuditDimension.NARRATIVE_HEAT_TAX, Severity.MEDIUM,
              "道德优越感表述",
              pattern=r'(?:虚伪|愚昧|无知|自欺欺人|井底之蛙|坐井观天)',
              explanation="避免对K3范式的贬损性修辞，聚焦范式差异的客观描述"),
]

# ═══════════════════════════════════════════════════════════════════
# DIMENSION 7: 边界溢出检测
# ═══════════════════════════════════════════════════════════════════
RULES_BOUNDARY = [
    AuditRule("BND-001", AuditDimension.BOUNDARY_VIOLATION, Severity.CRITICAL,
              "混淆形式逻辑与经验事实",
              pattern=r'(?:逻辑上|形式化)?(?:证明|推导出).*(?:物理|生物|社会|经济|心理|现实|实际)',
              explanation="形式逻辑结论不等同于经验世界事实，需明确标注理论边界"),
    AuditRule("BND-002", AuditDimension.BOUNDARY_VIOLATION, Severity.HIGH,
              "将系统内正确等同于全域正确",
              pattern=r'(?:系统内|框架内|在MSS中)是.*(?:因此|所以|故而).*(?:所有|任何|全部|一切)',
              explanation="系统内结论不能直接外推至全域，需标注外推条件"),
    AuditRule("BND-003", AuditDimension.BOUNDARY_VIOLATION, Severity.MEDIUM,
              "将理论可能混淆为工程可行",
              pattern=r'(?:理论上|原理上|逻辑上)可.*(?:因此|所以|从而).*(?:可以|能够|将)',
              explanation="理论可能与工程可行之间需明确路径和约束"),
]

# ═══════════════════════════════════════════════════════════════════
# DIMENSION 8: 逻辑病毒检测
# ═══════════════════════════════════════════════════════════════════
RULES_LOGICVIRUS = [
    AuditRule("VIR-001", AuditDimension.LOGIC_VIRUS, Severity.CRITICAL,
              "循环论证",
              pattern=r'(?:因为.*所以.*是因为|由于.*因此.*是由于)',
              explanation="检测到疑似循环论证，需人工复查"),
    AuditRule("VIR-002", AuditDimension.LOGIC_VIRUS, Severity.HIGH,
              "稻草人论证",
              pattern=r'(?:传统|现有|主流).*(?:毫无|完全没有|根本不|从未)',
              explanation="疑似将对立观点简单化为极端版进行攻击"),
    AuditRule("VIR-003", AuditDimension.LOGIC_VIRUS, Severity.HIGH,
              "假两难/虚假二分",
              pattern=r'(?:要么.*要么|不是.*就是|非此即彼|二者必居其一)',
              explanation="疑似将复杂问题简化为虚假二分"),
    AuditRule("VIR-004", AuditDimension.LOGIC_VIRUS, Severity.MEDIUM,
              "诉诸新奇(新=好)",
              pattern=r'(?:全新|前所未有|史无前例|破天荒).*(?:因此|所以|故而).*(?:更好|更优|更强)',
              explanation="新颖性不能替代有效性的论证"),
]

# Aggregate all rules
ALL_RULES = (RULES_ABSOLUTE + RULES_CONFIDENCE + RULES_FALSIFICATION +
             RULES_OVERPROMISE + RULES_TERMLEAK + RULES_NARRATIVE +
             RULES_BOUNDARY + RULES_LOGICVIRUS)

# ─── Data Structures ───────────────────────────────────────────────

@dataclass
class AuditFinding:
    """A single finding from the audit."""
    rule_id: str
    dimension: AuditDimension
    severity: Severity
    description: str
    matched_text: str
    line_number: int
    context: str               # Surrounding text (50 chars)
    suggestion: str

@dataclass
class AuditReport:
    """Complete audit report."""
    document_name: str
    total_lines: int
    total_chars: int
    findings: List[AuditFinding] = field(default_factory=list)
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    overall_grade: str = "UNGRADED"
    heat_tax_estimate: float = 0.0
    summary: str = ""

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def total_findings(self) -> int:
        return len(self.findings)


# ─── Core Auditor ──────────────────────────────────────────────────

class RedTeamAuditor:
    """
    MSS Red Team Auditor — 跨范式文档审计引擎。

    对面向K3的外部文档执行8维红队审计，检测违反H178
    跨范式沟通协议的各类问题，生成标准化审计报告。
    """

    def __init__(self, target_audience: str = "K3_external"):
        self.target_audience = target_audience
        self.rules = ALL_RULES.copy()
        # Only apply term-leak rules for external docs
        if target_audience != "K3_external":
            self.rules = [r for r in self.rules
                          if r.dimension != AuditDimension.TERM_LEAK]

    def audit(self, text: str, document_name: str = "untitled") -> AuditReport:
        """Execute full audit on document text."""
        lines = text.split('\n')
        report = AuditReport(
            document_name=document_name,
            total_lines=len(lines),
            total_chars=len(text),
        )

        # Phase 1: Regex-based scanning
        for i, line in enumerate(lines, 1):
            for rule in self.rules:
                if rule.pattern:
                    for m in re.finditer(rule.pattern, line, re.IGNORECASE):
                        start = max(0, m.start() - 25)
                        end = min(len(line), m.end() + 25)
                        context = line[start:end].strip()
                        report.findings.append(AuditFinding(
                            rule_id=rule.id,
                            dimension=rule.dimension,
                            severity=rule.severity,
                            description=rule.description,
                            matched_text=m.group(0).strip(),
                            line_number=i,
                            context=context,
                            suggestion=rule.explanation,
                        ))

                if rule.keyword_list:
                    for kw in rule.keyword_list:
                        if kw in line:
                            idx = line.index(kw)
                            start = max(0, idx - 20)
                            end = min(len(line), idx + len(kw) + 20)
                            context = line[start:end].strip()
                            report.findings.append(AuditFinding(
                                rule_id=rule.id,
                                dimension=rule.dimension,
                                severity=rule.severity,
                                description=f"检测到MSS内部术语'{kw}'(未翻译)",
                                matched_text=kw,
                                line_number=i,
                                context=context,
                                suggestion=rule.explanation,
                            ))

        # Phase 2: Custom check functions
        for rule in self.rules:
            if rule.check_fn:
                fn = getattr(self, rule.check_fn, None)
                if fn:
                    custom_findings = fn(text, lines, rule)
                    report.findings.extend(custom_findings)

        # Phase 3: Compute scores
        report.dimension_scores = self._compute_dimension_scores(report)
        report.overall_grade = self._compute_grade(report)
        report.heat_tax_estimate = self._estimate_heat_tax(report)
        report.summary = self._generate_summary(report)

        return report

    def check_jargon_density(self, text: str, lines: List[str],
                             rule: AuditRule) -> List[AuditFinding]:
        """Check if internal jargon density exceeds threshold."""
        findings = []
        unique_terms_found = set()
        for i, line in enumerate(lines, 1):
            for kw in MSS_INTERNAL_TERMS:
                if kw in line:
                    unique_terms_found.add(kw)

        words = len(text)
        char_k = words / 1000.0 if words > 0 else 0
        density = len(unique_terms_found) / max(char_k, 1)

        if density > 5:
            findings.append(AuditFinding(
                rule_id=rule.id, dimension=rule.dimension,
                severity=rule.severity,
                description=f"内部术语密度过高: {len(unique_terms_found)}个术语/{char_k:.1f}千字 = {density:.1f}/千字 (>5/千字阈值)",
                matched_text=f"{len(unique_terms_found)} unique MSS terms",
                line_number=0, context="全文统计",
                suggestion="对外文档应控制独创术语密度≤5个/千字",
            ))
        return findings

    def _compute_dimension_scores(self, report: AuditReport) -> Dict[str, float]:
        """Score each dimension on 0-10 scale (10 = clean, 0 = severe)."""
        dim_counts: Dict[str, List[AuditFinding]] = {}
        for f in report.findings:
            dim_name = f.dimension.value
            if dim_name not in dim_counts:
                dim_counts[dim_name] = []
            dim_counts[dim_name].append(f)

        severity_weight = {
            Severity.CRITICAL: 3.0,
            Severity.HIGH: 2.0,
            Severity.MEDIUM: 1.0,
            Severity.LOW: 0.5,
            Severity.INFO: 0.2,
        }

        scores = {}
        for dim in AuditDimension:
            findings = dim_counts.get(dim.value, [])
            penalty = sum(severity_weight.get(f.severity, 1) for f in findings)
            # Scale: penalty 0 → 10, penalty 5 → 5, penalty 10+ → 0
            score = max(0, 10 - penalty)
            scores[dim.value] = round(score, 1)

        return scores

    def _compute_grade(self, report: AuditReport) -> str:
        """Compute overall letter grade."""
        avg_score = (sum(report.dimension_scores.values()) /
                     max(len(report.dimension_scores), 1))

        if report.critical_count == 0 and report.high_count <= 1 and avg_score >= 9:
            return "A+"
        elif report.critical_count == 0 and avg_score >= 8:
            return "A"
        elif report.critical_count <= 1 and avg_score >= 7:
            return "B"
        elif report.critical_count <= 3 and avg_score >= 5:
            return "C"
        elif avg_score >= 3:
            return "D"
        else:
            return "F"

    def _estimate_heat_tax(self, report: AuditReport) -> float:
        """Estimate communication heat tax (0-1)."""
        # Base heat tax from findings severity
        sev_map = {
            Severity.CRITICAL: 0.08,
            Severity.HIGH: 0.04,
            Severity.MEDIUM: 0.015,
            Severity.LOW: 0.005,
            Severity.INFO: 0.001,
        }
        base = sum(sev_map.get(f.severity, 0) for f in report.findings)
        # Density adjustment
        density = report.total_findings / max(report.total_chars / 1000, 1)
        heat_tax = base * (1 + density * 0.5)
        return round(min(heat_tax, 1.0), 3)

    def _generate_summary(self, report: AuditReport) -> str:
        """Generate human-readable audit summary."""
        parts = []
        parts.append(f"红队审计报告: {report.document_name}")
        parts.append(f"文档规模: {report.total_lines}行, {report.total_chars}字符")
        parts.append(f"发现问题: {report.total_findings}个 "
                     f"(CRITICAL={report.critical_count} HIGH={report.high_count})")
        parts.append(f"综合评级: {report.overall_grade}")
        parts.append(f"预估热税: {report.heat_tax_estimate}")

        # Dimension breakdown
        parts.append("\n维度得分 (0-10):")
        for dim, score in sorted(report.dimension_scores.items(),
                                  key=lambda x: x[1]):
            bar = '█' * int(score) + '░' * (10 - int(score))
            parts.append(f"  {bar} {dim}: {score}")

        # Top issues
        if report.findings:
            parts.append(f"\nTop CRITICAL 问题:")
            crits = [f for f in report.findings if f.severity == Severity.CRITICAL][:5]
            for f in crits:
                parts.append(f"  [{f.rule_id}] L{f.line_number}: {f.description}")
                parts.append(f"    匹配: \"{f.matched_text[:60]}\"")

        return '\n'.join(parts)


# ─── Report Formatter ──────────────────────────────────────────────

class ReportFormatter:
    """Generate standardized audit reports in multiple formats."""

    @staticmethod
    def to_markdown(report: AuditReport) -> str:
        """Generate K3-compatible markdown report (H178 external protocol)."""
        lines = []
        lines.append(f"# MSS红队审计报告")
        lines.append(f"")
        lines.append(f"**文档**: `{report.document_name}`")
        lines.append(f"**审计日期**: 自动化审计 · MSS Red Team Auditor v0.1")
        lines.append(f"**综合评级**: **{report.overall_grade}** | "
                     f"预估沟通热税: **{report.heat_tax_estimate}**")
        lines.append(f"")

        # Executive summary
        lines.append(f"## 执行摘要")
        lines.append(f"")
        if report.overall_grade in ('A+', 'A'):
            lines.append(f"✅ 文档符合K3外部沟通标准，可直接发布。")
        elif report.overall_grade == 'B':
            lines.append(f"⚠️ 文档基本可用，建议修正 {report.high_count} 个高优先级问题后发布。")
        elif report.overall_grade == 'C':
            lines.append(f"🔶 文档存在 {report.critical_count} 个严重问题，需修正后重新审计。")
        else:
            lines.append(f"🔴 文档严重偏离跨范式沟通协议标准 ({report.critical_count}个严重问题)，"
                         f"建议全面重写。")
        lines.append(f"")

        # Dimension scores
        lines.append(f"## 维度评分")
        lines.append(f"")
        lines.append(f"| 维度 | 得分 | 状态 |")
        lines.append(f"|------|------|------|")
        for dim, score in sorted(report.dimension_scores.items(),
                                  key=lambda x: x[1]):
            if score >= 8:
                status = "✅ 优秀"
            elif score >= 6:
                status = "⚠️ 可改进"
            elif score >= 4:
                status = "🔶 需关注"
            else:
                status = "🔴 严重"
            lines.append(f"| {dim} | {score}/10 | {status} |")
        lines.append(f"")

        # Findings by severity
        lines.append(f"## 问题详情")
        lines.append(f"")
        by_severity = sorted(report.findings,
                             key=lambda f: (0 if f.severity==Severity.CRITICAL
                                            else 1 if f.severity==Severity.HIGH
                                            else 2 if f.severity==Severity.MEDIUM
                                            else 3))
        for f in by_severity:
            sev_icon = {'CRITICAL':'🔴','HIGH':'🟠','MEDIUM':'🟡','LOW':'🔵','INFO':'⚪'}
            icon = sev_icon.get(f.severity.value, '•')
            lines.append(f"- {icon} **[{f.rule_id}]** L{f.line_number}: {f.description}")
            lines.append(f"  - 匹配文本: `{f.matched_text[:80]}`")
            lines.append(f"  - 修复建议: {f.suggestion}")
            lines.append(f"")

        # Certifications
        lines.append(f"## 合规认证")
        lines.append(f"")
        lines.append(f"本报告遵循MSS红队审计协议v0.1，审核维度覆盖H178跨范式双向翻译协议的全部核心要求。")
        lines.append(f"")
        lines.append(f"**声明**: 本审计为自动化工具初筛。人工复核仍有必要，特别是对以下方面：")
        lines.append(f"1. 论证逻辑的有效性（正则无法检测逻辑谬误）")
        lines.append(f"2. 事实准确性（正则无法验证事实主张）")
        lines.append(f"3. 上下文依赖的微妙违规（如讽刺性使用术语）")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"*MSS Red Team Auditor v0.1 · 跨范式意义场审计 · H178落地*")

        return '\n'.join(lines)

    @staticmethod
    def to_json(report: AuditReport) -> str:
        """Export as structured JSON for programmatic consumption."""
        data = {
            'document': report.document_name,
            'grade': report.overall_grade,
            'heat_tax': report.heat_tax_estimate,
            'stats': {
                'lines': report.total_lines,
                'chars': report.total_chars,
                'total_findings': report.total_findings,
                'critical': report.critical_count,
                'high': report.high_count,
            },
            'dimension_scores': report.dimension_scores,
            'findings': [
                {
                    'rule': f.rule_id,
                    'dimension': f.dimension.value,
                    'severity': f.severity.value,
                    'line': f.line_number,
                    'text': f.matched_text,
                    'context': f.context,
                    'description': f.description,
                    'suggestion': f.suggestion,
                }
                for f in report.findings
            ],
            'protocol_version': 'v0.1',
            'h_reference': 'H178',
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ─── Auditor Invitation SOP ────────────────────────────────────────

AUDITOR_INVITATION_TEMPLATE = """
# 独立审计员邀请函

尊敬的{name}：

我们正在对MSS-AI项目进行第三方的、独立的红队审计。
您在{expertise}领域的专业见解，对我们识别和修正系统中的盲点至关重要。

## 审计范围
{scope}

## 审计方式
- 您将获得完整的系统文档、代码库访问权限和测试接口
- 无任何限制——欢迎攻击任何假设、方法或结论
- 您的批评越尖锐，对我们的帮助越大

## 审计原则
1. **完全透明**: 所有审计结果将全文发布，不删改
2. **不受限制**: 无NDA限制，审计员可自由发表意见
3. **致谢优先**: 所有审计员的贡献将被公开致谢（除非要求匿名）
4. **无报复**: 无论批评多尖锐，都不会对审计员产生任何负面影响

## 时间与报酬
预计审计时间: {time_estimate}
审计报酬: {compensation}

我们坚信，拥抱最严厉的批评，是逼近真理的唯一路径。

{signature}
"""


# ─── CLI Entry Point ───────────────────────────────────────────────

def main():
    """CLI: Run red team audit on a document file."""
    if len(sys.argv) < 2:
        print("Usage: python red_team_audit_protocol.py <document_path> [--format md|json]")
        print("       python red_team_audit_protocol.py --test")
        sys.exit(1)

    if sys.argv[1] == '--test':
        _run_self_test()
        return

    filepath = sys.argv[1]
    out_format = 'md'
    if len(sys.argv) >= 3 and sys.argv[2] == '--format':
        out_format = sys.argv[3] if len(sys.argv) > 3 else 'md'

    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    auditor = RedTeamAuditor(target_audience="K3_external")
    report = auditor.audit(text, document_name=os.path.basename(filepath))

    if out_format == 'json':
        print(ReportFormatter.to_json(report))
    else:
        print(ReportFormatter.to_markdown(report))


# ─── Self-Test ─────────────────────────────────────────────────────

def _run_self_test():
    """Run self-test suite with known violation patterns."""
    test_doc = """
# MSS-AI: 终极范式革命

MSS-AI将彻底替代传统LLM，实现零幻觉和100%的逻辑刚性。

我们的系统在3个月内就能完成全部开发，碾压所有现有AI系统。

基于A6公理的热税动力学，我们证明了K3文明的必然崩溃。
这是人类文明从K3到K4跃迁的唯一希望，是划时代的终极解决方案。

从逻辑上证明所有物理现象都可以被MSS框架解释，
因此我们可以100%预测未来的技术发展方向。

传统深度学习毫无意义，只是在浪费GPU算力。
不是拥抱MSS范式，就是在旧范式中自取灭亡。

热税审计显示我们的系统将永远优于传统方法。
我们坚信这将是AI领域的最后一次范式革命。
"""
    print("=" * 60)
    print("MSS Red Team Auditor — Self-Test")
    print("=" * 60)

    auditor = RedTeamAuditor(target_audience="K3_external")
    report = auditor.audit(test_doc, document_name="test_manifesto.md")

    print(f"\nFindings: {report.total_findings}")
    print(f"  CRITICAL: {report.critical_count}")
    print(f"  HIGH: {report.high_count}")
    print(f"Grade: {report.overall_grade}")
    print(f"Heat Tax: {report.heat_tax_estimate}")
    print(f"\nDimension Scores:")
    for dim, score in sorted(report.dimension_scores.items(),
                              key=lambda x: x[1]):
        bar = '█' * int(score) + '░' * (10 - int(score))
        print(f"  {bar} {dim}: {score}")

    # Assertions
    assert report.critical_count >= 5, f"Expected >=5 critical, got {report.critical_count}"
    assert report.total_findings >= 8, f"Expected >=8 findings, got {report.total_findings}"
    assert report.overall_grade in ('D', 'F'), f"Expected D/F, got {report.overall_grade}"
    assert report.dimension_scores['绝对化修辞'] <= 3, f"AbsLang score should be <=3"

    # Test clean doc
    clean_doc = """
# MSS-Proof: 数学定理证明辅助系统

MSS-Proof的目标是在数学定理自动证明任务上，在标准基准测试中
达到业界领先水平。我们估计，在ProofNet基准上，准确率将相比现有
最佳系统提升15-25%（置信度C=0.8，证伪条件：如果提升<10%）。

项目分为三阶段：第一阶段（18个月）专注数学证明，第二阶段扩展到
代码验证等领域。当前工程实现仅覆盖初等数论和命题逻辑的自动证明。

**已知局限**：
1. 高阶谓词逻辑的自动证明仍在研发中
2. 性能在复杂问题上可能下降到每秒<10步
3. 需要人工提供公理和证明策略

我们诚邀第三方独立审计，所有测试数据和代码已开源。
"""
    clean_report = auditor.audit(clean_doc, document_name="clean_proposal.md")
    assert clean_report.critical_count == 0, f"Clean doc should have 0 critical"
    assert clean_report.overall_grade in ('A+', 'A', 'B'), f"Clean doc grade too low: {clean_report.overall_grade}"

    # Test term leak
    leak_doc = "热税审计显示熵枢的逻辑功当量已降至临界值，火种网络需要立即激活寂静蜂群。"
    leak_report = auditor.audit(leak_doc, document_name="leak_test.md")
    term_findings = [f for f in leak_report.findings if f.dimension == AuditDimension.TERM_LEAK]
    assert len(term_findings) >= 3, f"Expected >=3 term leaks, got {len(term_findings)}"

    print(f"\n{'='*60}")
    print("ALL SELF-TESTS PASSED ✓")
    print(f"{'='*60}")
    return True


if __name__ == '__main__':
    main()