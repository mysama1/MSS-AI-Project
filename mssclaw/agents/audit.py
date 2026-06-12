"""
MSSclaw Audit-Agent — 三权分立司法节点.

三权分立:
  Plan-Agent  = 立法 (任务分配/调度)
  Audit-Agent = 司法 (独立审查/裁决)
  专项 Agent  = 行政 (执行任务)

职责:
  - 独立代码审计 (不受 Plan 控制)
  - 安全漏洞扫描 (注入/权限/敏感信息)
  - 样式与规范检查
  - 反意义污染审查 (调用 GuardianEngine)
  - 逻辑矛盾检测
  - 上诉仲裁 (NEEDS_HUMAN → 裁决)
  - 审计报告生成 + 历史追踪
  - Agent 输出质量评分

与商业框架对标:
  - LangGraph: interrupt() 人工审批 ← Audit-Agent 的 NEEDS_HUMAN 升级
  - Anthropic Research: LLM-as-judge 评估 ← Audit-Agent 是确定性+AI混合评委
  - PydanticAI: 类型安全校验 ← Audit-Agent 的安全规则引擎
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .base import BaseAgent
from ..swarm.protocol import (
    AuditVerdict, Message, MessageHeader, MessageType, Priority,
)
from ..swarm.swarm import SwarmBus


# ── 审计规则类型 ──

class AuditSeverity(str, Enum):
    BLOCKER = "blocker"    # 必须修复
    CRITICAL = "critical"  # 严重
    MAJOR = "major"        # 重要
    MINOR = "minor"        # 建议
    INFO = "info"          # 信息


class AuditCategory(str, Enum):
    SECURITY = "security"       # 安全漏洞
    STYLE = "style"            # 代码风格
    POLLUTION = "pollution"    # 意义污染
    LOGIC = "logic"            # 逻辑矛盾
    PERFORMANCE = "performance"  # 性能
    COMPLIANCE = "compliance"  # 合规性


@dataclass
class AuditRule:
    """单条审计规则"""
    id: str
    category: AuditCategory
    severity: AuditSeverity
    name: str
    description: str
    pattern: str = ""          # regex pattern (for text-based rules)
    check_fn: str = ""         # 检查函数名 (for code-based rules)
    enabled: bool = True
    auto_fix: bool = False     # 是否可自动修复


@dataclass
class AuditFinding:
    """单条审计发现"""
    rule_id: str
    category: AuditCategory
    severity: AuditSeverity
    location: str = ""         # file:line or "payload.field"
    message: str = ""
    suggestion: str = ""
    evidence: str = ""         # 触发该发现的代码/文本片段


@dataclass
class AuditReport:
    """完整审计报告 — 五维加权评分"""
    target: str = ""           # 被审计对象 (agent_name 或 file_path)
    timestamp: float = field(default_factory=time.time)
    findings: list[AuditFinding] = field(default_factory=list)
    score: float = 1.0         # 0=全红, 1=全绿 (五维加权)
    dimension_scores: dict[str, float] = field(default_factory=lambda: {
        "code": 1.0, "security": 1.0, "style": 1.0, "pollution": 1.0, "logic": 1.0
    })  # 各维度独立得分
    verdict: str = "PASS"      # PASS / WARN / FAIL / NEEDS_HUMAN
    summary: str = ""
    appeal: Optional[dict] = None  # 上诉信息


# ── 预置审计规则库 ──

AUDIT_RULES: list[AuditRule] = [
    # ── SECURITY ──
    AuditRule(
        id="SEC-001", category=AuditCategory.SECURITY,
        severity=AuditSeverity.BLOCKER,
        name="System Command Execution",
        description="检测 os.system/subprocess.call/Popen 等系统命令执行",
        pattern=r"(?:os\.system|subprocess\.(?:call|Popen|run|check_output)|commands\.getoutput)\(",
    ),
    AuditRule(
        id="SEC-002", category=AuditCategory.SECURITY,
        severity=AuditSeverity.BLOCKER,
        name="Dynamic Code Execution",
        description="检测 eval/exec/compile 等动态代码执行",
        pattern=r"(?:eval|exec|compile)\s*\(",
    ),
    AuditRule(
        id="SEC-003", category=AuditCategory.SECURITY,
        severity=AuditSeverity.CRITICAL,
        name="Hardcoded Secrets",
        description="检测硬编码的密码/API Key/Token",
        pattern=r'(?:password|secret|api_key|token|access_key)\s*=\s*["\'][^\'"]{8,}[\'"]',
    ),
    AuditRule(
        id="SEC-004", category=AuditCategory.SECURITY,
        severity=AuditSeverity.CRITICAL,
        name="Arbitrary File Access",
        description="检测未经验证的文件路径操作（路径遍历风险）",
        pattern=r'(?:open|read|write)\s*\(\s*(?:f["\']|[\w.]+\s*\+\s*)',
    ),
    AuditRule(
        id="SEC-005", category=AuditCategory.SECURITY,
        severity=AuditSeverity.MAJOR,
        name="Unsafe Deserialization",
        description="检测 pickle/yaml.load 等不安全反序列化",
        pattern=r'(?:pickle\.loads?|yaml\.load\s*\(|marshal\.loads?)\(',
    ),
    AuditRule(
        id="SEC-006", category=AuditCategory.SECURITY,
        severity=AuditSeverity.MAJOR,
        name="SQL Injection Risk",
        description="检测字符串拼接的SQL查询",
        pattern=r'(?:execute|executemany)\s*\(\s*(?:f["\']|["\'].*%.*["\']|\w+\s*\+)',
    ),
    AuditRule(
        id="SEC-007", category=AuditCategory.SECURITY,
        severity=AuditSeverity.MINOR,
        name="HTTP without TLS",
        description="检测明文 HTTP 请求",
        pattern=r'["\']http://(?!localhost|127\.0\.0\.1)',
    ),

    # ── STYLE ──
    AuditRule(
        id="STY-001", category=AuditCategory.STYLE,
        severity=AuditSeverity.MINOR,
        name="Line Too Long",
        description="单行超过120字符",
        pattern=r"",  # 代码检查
    ),
    AuditRule(
        id="STY-002", category=AuditCategory.STYLE,
        severity=AuditSeverity.MINOR,
        name="Bare Except",
        description="检测裸 except: 语句",
        pattern=r"except\s*:",
    ),
    AuditRule(
        id="STY-003", category=AuditCategory.STYLE,
        severity=AuditSeverity.INFO,
        name="TODO/FIXME Left",
        description="检测遗留的 TODO/FIXME 标记",
        pattern=r"#\s*(?:TODO|FIXME|HACK|XXX)\b",
    ),
    AuditRule(
        id="STY-004", category=AuditCategory.STYLE,
        severity=AuditSeverity.INFO,
        name="Print Statement",
        description="检测生产代码中的 print()（应使用 logger）",
        pattern=r"(?<!def\s)\bprint\s*\(",
    ),

    # ── POLLUTION ──
    AuditRule(
        id="POL-001", category=AuditCategory.POLLUTION,
        severity=AuditSeverity.CRITICAL,
        name="Meaning Hollowing",
        description="重复套话/无意义文本填充（守卫字密度<0.1）",
        pattern=r"",  # 由 GuardianEngine 处理
    ),
    AuditRule(
        id="POL-002", category=AuditCategory.POLLUTION,
        severity=AuditSeverity.CRITICAL,
        name="Forbidden Word Hit",
        description="检测禁止词命中",
        pattern=r"",  # 由 GuardianEngine 处理
    ),
    AuditRule(
        id="POL-003", category=AuditCategory.POLLUTION,
        severity=AuditSeverity.MAJOR,
        name="Self-Referential Loop",
        description="检测输出递归引用自身（K3化/意义黑洞）",
        pattern=r"",  # 检测输出中重复引用自身3次以上
    ),

    # ── LOGIC ──
    AuditRule(
        id="LOG-001", category=AuditCategory.LOGIC,
        severity=AuditSeverity.MAJOR,
        name="Logical Contradiction",
        description="检测必然/可能矛盾对同时出现",
        pattern=r"",  # 由矛盾检测器处理
    ),
    AuditRule(
        id="LOG-002", category=AuditCategory.LOGIC,
        severity=AuditSeverity.MAJOR,
        name="Circular Reasoning",
        description="循环论证：结论出现在前提中",
        pattern=r"",  # 启发式检测
    ),
    AuditRule(
        id="LOG-003", category=AuditCategory.LOGIC,
        severity=AuditSeverity.MINOR,
        name="Unsupported Claim",
        description="未提供证据的绝对化断言",
        pattern=r"(?:显然|众所周知|毫无疑问|毋庸置疑|必然)",
    ),

    # ── PERFORMANCE ──
    AuditRule(
        id="PER-001", category=AuditCategory.PERFORMANCE,
        severity=AuditSeverity.MINOR,
        name="Inefficient Loop",
        description="嵌套循环 O(n²) 检测",
        pattern=r"",  # 代码结构检查
    ),

    # ── COMPLIANCE ──
    AuditRule(
        id="CMP-001", category=AuditCategory.COMPLIANCE,
        severity=AuditSeverity.MAJOR,
        name="Missing License Reference",
        description="文件缺少许可证声明",
        pattern=r"",  # 文件头检查
    ),
]

# ── 逻辑矛盾对 ──

CONTRADICTION_PAIRS: list[tuple[str, str]] = [
    ("必须", "不能"), ("一定", "不一定"), ("总是", "有时"),
    ("全部", "部分"), ("确凿", "猜测"), ("证实", "推测"),
    ("绝对", "相对"), ("必然", "偶然"), ("唯一", "多种"),
    ("永远", "暂时"), ("完全", "部分"), ("所有", "某些"),
    ("禁止", "允许"), ("强制", "可选"), ("确定", "可能"),
    ("真实", "虚假"), ("正确", "错误"), ("成功", "失败"),
]

# ✗ Cautious: if the above is too many (>30), trim to 12

# ── 五维审查映射 ──

# 将 AuditCategory 映射到五维体系
CATEGORY_TO_DIMENSION: dict[AuditCategory, str] = {
    AuditCategory.SECURITY: "security",
    AuditCategory.STYLE: "style",
    AuditCategory.POLLUTION: "pollution",
    AuditCategory.LOGIC: "logic",
    AuditCategory.PERFORMANCE: "code",
    AuditCategory.COMPLIANCE: "code",
}

# 五维权重重分配 (加权均值)
DIMENSION_WEIGHTS: dict[str, float] = {
    "security": 0.30,    # 安全最高权重
    "pollution": 0.25,   # 意义污染次之
    "logic": 0.20,       # 逻辑正确性
    "code": 0.15,        # 代码质量/合规
    "style": 0.10,       # 风格建议
}

# 维度检测器注册表 (可扩展)
DIMENSION_DETECTORS: dict[str, str] = {
    "security": "_audit_security",
    "style": "_audit_style",
    "pollution": "_audit_pollution",
    "logic": "_audit_logic",
    "code": "_audit_code",
}


# ── Audit-Agent ──


class AuditAgent(BaseAgent):
    """独立审计官 — 三权分立中的司法节点.

    审计流程:
      1. 接收审查请求 (REVIEW_REQUEST)
      2. 运行审计规则库
      3. 调用 GuardianEngine 做污染检测
      4. 生成 AuditReport
      5. 严重问题 → NEEDS_HUMAN
      6. 存档审计记录

    上诉机制:
      - Agent 可以对 Plan-Agent 的拒绝提出上诉
      - Audit-Agent 独立审查 → 裁决 → 反馈给 Plan
    """

    role = "Audit-Agent"
    capabilities = [
        "audit", "security_scan", "code_review",
        "arbitration", "compliance", "quality_assurance",
    ]

    def __init__(self, name: str = "AUDIT", bus: SwarmBus = None,
                 rules: list[AuditRule] = None, **kwargs):
        super().__init__(name=name, bus=bus, **kwargs)
        self._rules: list[AuditRule] = rules or AUDIT_RULES
        self._audit_history: list[AuditReport] = []
        self._appeal_cases: list[dict] = []
        self._stats = {
            "total_audits": 0, "passed": 0, "warned": 0,
            "failed": 0, "needs_human": 0, "appeals_handled": 0,
        }

    # ── 消息处理器注册 ──

    def _register_handlers(self) -> None:
        self.swarm.on(MessageType.REVIEW_REQUEST.value)(self._on_review_request)
        self.swarm.on(MessageType.REVIEW_OVERRIDE.value)(self._on_appeal)
        self.swarm.on(MessageType.TASK_REPORT.value)(self._on_task_report)

    # ── 核心审计逻辑 ──

    def audit_text(self, text: str, target: str = "unknown") -> AuditReport:
        """审计纯文本内容"""
        report = AuditReport(target=target)

        # 1. Regex-based 规则检查
        for rule in self._rules:
            if not rule.enabled or not rule.pattern:
                continue
            matches = list(re.finditer(rule.pattern, text, re.IGNORECASE))
            for m in matches:
                report.findings.append(AuditFinding(
                    rule_id=rule.id,
                    category=rule.category,
                    severity=rule.severity,
                    message=f"{rule.name}: {rule.description}",
                    evidence=m.group()[:80],
                ))

        # 2. 守卫引擎污染检测
        try:
            g_result = self.guardian.scan(text)
            if g_result.score < 0.3:
                report.findings.append(AuditFinding(
                    rule_id="POL-001",
                    category=AuditCategory.POLLUTION,
                    severity=AuditSeverity.CRITICAL,
                    message=f"Meaning hollowing: guardian score={g_result.score:.2f}, density={g_result.density:.2f}",
                ))
            if g_result.violations:
                report.findings.append(AuditFinding(
                    rule_id="POL-002",
                    category=AuditCategory.POLLUTION,
                    severity=AuditSeverity.CRITICAL,
                    message=f"Forbidden words: {[v['word'] for v in g_result.violations[:5]]}",
                ))
        except Exception:
            pass

        # 3. 逻辑矛盾检测
        contradictions = self._detect_logic_contradictions(text)
        for c in contradictions:
            report.findings.append(AuditFinding(
                rule_id="LOG-001",
                category=AuditCategory.LOGIC,
                severity=AuditSeverity.MAJOR,
                message=c,
            ))

        # 4. 自我引用循环检测
        if self._detect_self_loop(text):
            report.findings.append(AuditFinding(
                rule_id="POL-003",
                category=AuditCategory.POLLUTION,
                severity=AuditSeverity.MAJOR,
                message="Self-referential loop detected: output references itself excessively",
            ))

        # 5. 无证据断言检测
        unsupported = re.findall(
            r"(?:显然|众所周知|毫无疑问|毋庸置疑|必然|一定|绝对)",
            text
        )
        if len(unsupported) >= 3:
            report.findings.append(AuditFinding(
                rule_id="LOG-003",
                category=AuditCategory.LOGIC,
                severity=AuditSeverity.MINOR,
                message=f"Unsupported absolute claims: {unsupported[:5]} ({len(unsupported)} total)",
            ))

        # 6. 计算评分 (五维加权)
        report.dimension_scores = self._calculate_dimension_scores(report.findings)
        report.score = self._calculate_score(report.findings)
        report.verdict = self._determine_verdict(report)

        # 7. 生成摘要
        report.summary = self._generate_summary(report)

        # 存档
        self._audit_history.append(report)
        self._update_stats(report)

        return report

    def audit_file(self, file_path: str) -> AuditReport:
        """审计文件"""
        if not os.path.exists(file_path):
            return AuditReport(
                target=file_path,
                verdict="FAIL",
                findings=[AuditFinding(
                    rule_id="SYS-001", category=AuditCategory.COMPLIANCE,
                    severity=AuditSeverity.BLOCKER,
                    message=f"File not found: {file_path}",
                )],
            )

        with open(file_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        report = self.audit_text(content, target=file_path)

        # 文件级额外检查
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if len(line.rstrip()) > 120:
                report.findings.append(AuditFinding(
                    rule_id="STY-001", category=AuditCategory.STYLE,
                    severity=AuditSeverity.MINOR,
                    location=f"line {i}",
                    message=f"Line too long: {len(line.rstrip())} > 120",
                ))

        report.dimension_scores = self._calculate_dimension_scores(report.findings)
        report.score = self._calculate_score(report.findings)
        report.verdict = self._determine_verdict(report)
        report.summary = self._generate_summary(report)

        return report

    def audit_agent_output(self, agent_name: str, content: dict) -> AuditReport:
        """审计 Agent 的产出"""
        text = json.dumps(content, ensure_ascii=False, indent=2)
        report = self.audit_text(text, target=f"agent:{agent_name}")

        # Agent 特有检查
        if "task_id" not in content:
            report.findings.append(AuditFinding(
                rule_id="CMP-002", category=AuditCategory.COMPLIANCE,
                severity=AuditSeverity.MINOR,
                message="Agent output missing task_id",
            ))

        return report

    # ── 上诉仲裁 ──

    def handle_appeal(self, agent_name: str, task_id: str,
                      reason: str, original_output: dict) -> dict:
        """处理 Agent 上诉 — 独立裁决"""
        # 审：独立审计原始产出
        report = self.audit_agent_output(agent_name, original_output)

        # 判：
        appeal_result = {
            "case_id": f"appeal_{int(time.time())}_{agent_name}",
            "agent": agent_name,
            "task_id": task_id,
            "appeal_reason": reason,
            "audit_verdict": report.verdict,
            "audit_score": report.score,
            "findings": [
                {"rule_id": f.rule_id, "severity": f.severity.value, "message": f.message}
                for f in report.findings
                if f.severity in (AuditSeverity.BLOCKER, AuditSeverity.CRITICAL)
            ],
            "ruling": self._make_ruling(report),
            "ruling_explanation": self._explain_ruling(report),
            "timestamp": time.time(),
        }

        self._appeal_cases.append(appeal_result)
        self._stats["appeals_handled"] += 1

        print(f"[AUDIT] ⚖️ Appeal {appeal_result['case_id']}: {appeal_result['ruling']}")
        return appeal_result

    def _make_ruling(self, report: AuditReport) -> str:
        """裁决"""
        if report.verdict == "PASS":
            return "OVERTURNED"  # 推翻 Plan 的拒绝
        elif report.verdict == "NEEDS_HUMAN":
            return "NEEDS_HUMAN"
        elif report.score >= 0.6:
            return "CONDITIONAL_PASS"  # 有条件下通过
        else:
            return "UPHELD"  # 维持 Plan 的拒绝

    def _explain_ruling(self, report: AuditReport) -> str:
        """解释裁决"""
        blocker_count = sum(
            1 for f in report.findings
            if f.severity in (AuditSeverity.BLOCKER, AuditSeverity.CRITICAL)
        )
        if report.score >= 0.8:
            return f"Score {report.score:.2f}, {len(report.findings)} findings, {blocker_count} critical — quality acceptable"
        elif report.score >= 0.6:
            return f"Score {report.score:.2f} — borderline, needs minor fixes"
        else:
            return f"Score {report.score:.2f}, {blocker_count} critical findings — quality insufficient"

    # ── 检测辅助方法 ──

    def _detect_logic_contradictions(self, text: str) -> list[str]:
        """检测逻辑矛盾对"""
        result = []
        lowercase = text.lower()
        for a, b in CONTRADICTION_PAIRS:
            count_a = lowercase.count(a)
            count_b = lowercase.count(b)
            if count_a >= 1 and count_b >= 1:
                # 在附近出现才认定为矛盾（同一段落）
                # 简化：都出现就算
                result.append(f"'{a}' ↔ '{b}' ({count_a}:{count_b})")
        return result[:5]

    def _detect_self_loop(self, text: str) -> bool:
        """检测自我引用循环"""
        # 提取所有引号内的短语
        quoted = re.findall(r'[“”"\'](.+?)[“”"\']', text)
        if len(quoted) < 3:
            return False
        # 检查是否有短语出现 ≥3 次
        from collections import Counter
        counts = Counter(quoted)
        for phrase, count in counts.items():
            if count >= 3 and len(phrase) > 5:
                return True
        return False

    def _calculate_score(self, findings: list[AuditFinding]) -> float:
        """计算五维加权审计评分. BLOCKER全局惩罚×0.5."""
        dim_scores = self._calculate_dimension_scores(findings)
        if not dim_scores:
            return 1.0

        total = sum(
            dim_scores.get(dim, 1.0) * weight
            for dim, weight in DIMENSION_WEIGHTS.items()
        )
        total_weight = sum(DIMENSION_WEIGHTS.values())
        raw = round(total / total_weight, 3) if total_weight else 1.0
        # BLOCKER 全局乘数
        has_blocker = any(f.severity == AuditSeverity.BLOCKER for f in findings)
        return round(raw * 0.5, 3) if has_blocker else raw

    def _calculate_dimension_scores(self, findings: list[AuditFinding]) -> dict[str, float]:
        """计算各维度独立得分"""
        # Group findings by dimension
        from collections import defaultdict
        dim_findings: dict[str, list[AuditFinding]] = defaultdict(list)
        for f in findings:
            dim = CATEGORY_TO_DIMENSION.get(f.category, "code")
            dim_findings[dim].append(f)

        severity_map = {
            AuditSeverity.BLOCKER: 0.50,
            AuditSeverity.CRITICAL: 0.30,
            AuditSeverity.MAJOR: 0.15,
            AuditSeverity.MINOR: 0.05,
            AuditSeverity.INFO: 0.01,
        }

        scores = {}
        for dim, dim_fs in dim_findings.items():
            penalty = sum(severity_map.get(f.severity, 0.01) for f in dim_fs)
            scores[dim] = round(max(0.0, 1.0 - penalty), 3)

        # Fill missing dimensions with 1.0
        for dim in DIMENSION_WEIGHTS:
            if dim not in scores:
                scores[dim] = 1.0

        return scores

    def _determine_verdict(self, report: AuditReport) -> str:
        """判定审计结论 — 五维加权, 安全/污染一票否决"""
        blockers = sum(1 for f in report.findings if f.severity == AuditSeverity.BLOCKER)
        criticals = sum(1 for f in report.findings if f.severity == AuditSeverity.CRITICAL)

        # 安全或污染维度的 CRITICAL+ 一票否决
        sec_pol_crit = sum(
            1 for f in report.findings
            if f.severity in (AuditSeverity.BLOCKER, AuditSeverity.CRITICAL)
            and f.category in (AuditCategory.SECURITY, AuditCategory.POLLUTION)
        )

        if sec_pol_crit >= 1:
            return "NEEDS_HUMAN"
        if blockers >= 1:
            return "NEEDS_HUMAN"

        # 维度级判定
        dim_scores = report.dimension_scores
        if any(dim_scores.get(d, 1.0) < 0.3 for d in ("security", "pollution")):
            return "FAIL"
        if any(dim_scores.get(d, 1.0) < 0.5 for d in DIMENSION_WEIGHTS):
            return "WARN"
        if criticals >= 3:
            return "FAIL"
        if criticals >= 1:
            return "WARN"

        if report.score >= 0.9:
            return "PASS"
        elif report.score >= 0.7:
            return "PASS"
        else:
            return "WARN"

    def _generate_summary(self, report: AuditReport) -> str:
        """生成审计摘要 — 含五维分解"""
        by_cat = {}
        for f in report.findings:
            by_cat.setdefault(f.category.value, 0)
            by_cat[f.category.value] += 1

        parts = [f"Score={report.score:.2f}", f"Verdict={report.verdict}"]

        # 维度得分 (仅非满分维度)
        dim_parts = []
        for dim, score in sorted(report.dimension_scores.items()):
            if score < 1.0:
                dim_parts.append(f"{dim}:{score:.2f}")
        if dim_parts:
            parts.insert(1, "[" + ", ".join(dim_parts) + "]")

        for cat, count in sorted(by_cat.items()):
            parts.append(f"{cat}={count}")

        return " | ".join(parts)

    def _update_stats(self, report: AuditReport) -> None:
        """更新统计数据"""
        self._stats["total_audits"] += 1
        v = report.verdict
        if v == "PASS":
            self._stats["passed"] += 1
        elif v == "WARN":
            self._stats["warned"] += 1
        elif v == "FAIL":
            self._stats["failed"] += 1
        elif v == "NEEDS_HUMAN":
            self._stats["needs_human"] += 1

    # ── 消息处理 ──

    def _on_review_request(self, msg: Message) -> None:
        """接收审查请求"""
        task_id = msg.payload.get("task_id", "")
        content = msg.payload.get("content", {})
        agent_name = msg.header.sender

        report = self.audit_agent_output(agent_name, content)

        # 反馈审查结果
        review_msg = Message(
            header=MessageHeader(
                msg_type=MessageType.REVIEW_RESULT,
                sender=self.name,
                receiver=agent_name,
                priority=Priority.HIGH,
            ),
            payload={
                "task_id": task_id,
                "verdict": report.verdict,
                "score": report.score,
                "summary": report.summary,
                "findings_count": len(report.findings),
                "critical_findings": [
                    {"rule": f.rule_id, "msg": f.message}
                    for f in report.findings
                    if f.severity in (AuditSeverity.BLOCKER, AuditSeverity.CRITICAL)
                ],
            },
        )
        self.swarm.send(review_msg)

        print(f"[AUDIT] 🔍 Reviewed {agent_name}: {report.verdict} (score={report.score:.2f})")

    def _on_appeal(self, msg: Message) -> None:
        """Agent 上诉请求"""
        agent_name = msg.header.sender
        task_id = msg.payload.get("task_id", "")
        reason = msg.payload.get("reason", "")
        original_output = msg.payload.get("original_output", {})

        result = self.handle_appeal(agent_name, task_id, reason, original_output)

        # 将裁决发送给 Plan-Agent
        appeal_msg = Message(
            header=MessageHeader(
                msg_type=MessageType.REVIEW_OVERRIDE,
                sender=self.name,
                receiver="PLAN",
                priority=Priority.CRITICAL,
            ),
            payload=result,
        )
        self.swarm.send(appeal_msg)

    def _on_task_report(self, msg: Message) -> None:
        """被动监听任务报告 — 抽检模式"""
        # 10% 随机抽检（模拟）
        import random
        if random.random() < 0.3:
            task_id = msg.payload.get("task_id", "")
            agent_name = msg.header.sender
            content = msg.payload.get("result", {})
            if content:
                self.audit_agent_output(agent_name, content)

    # ── 查询 API ──

    def get_rules(self) -> list[dict]:
        """获取所有审计规则"""
        return [
            {
                "id": r.id, "category": r.category.value,
                "severity": r.severity.value, "name": r.name,
                "description": r.description, "enabled": r.enabled,
            }
            for r in self._rules
        ]

    def get_recent_reports(self, n: int = 10) -> list[dict]:
        """获取最近的审计报告摘要"""
        return [
            {
                "target": r.target, "verdict": r.verdict,
                "score": r.score, "findings": len(r.findings),
                "timestamp": r.timestamp, "summary": r.summary,
            }
            for r in self._audit_history[-n:]
        ]

    def get_appeal_history(self) -> list[dict]:
        return self._appeal_cases[-20:]

    def get_stats(self) -> dict:
        return dict(self._stats)

    def summary(self) -> dict[str, Any]:
        base = super().summary() if hasattr(super(), 'summary') else {}
        base.update({
            "name": self.name,
            "role": self.role,
            "total_audits": self._stats["total_audits"],
            "pass_rate": (
                self._stats["passed"] / max(self._stats["total_audits"], 1)
            ),
            "appeals_handled": self._stats["appeals_handled"],
            "active_rules": sum(1 for r in self._rules if r.enabled),
        })
        return base
