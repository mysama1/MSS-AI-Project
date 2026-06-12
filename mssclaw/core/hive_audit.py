"""
mssclaw/core/hive_audit.py

蜂巢化审计系统 — Hive Audit System.

设计哲学:
  "大方向审抽象范围逻辑校准，小任务切片执行校准，
   冲突校准，阶段性完成对阶段进行全量审计。有分有合。"

架构 (5 层包围网):
  L0 微观层 — 单任务微审计 (per-task, 极轻量)
  L1 批次层 — N 任务累积触发检查点 (batch checkpoint)
  L2 阶段层 — 阶段完成全量审计 (phase-level full audit)
  L3 冲突层 — 跨 Agent 矛盾检测 (cross-agent contradiction)
  L4 宏面层 — 大方向逻辑校准 (strategic calibration)

节点散布化:
  不是每个任务都审 → 任务量达标才触发 → 省算力
  检查点密度自适应 → 异常增多则收紧 → 正常则放松

意义包围:
  L0→L1→L2→L3→L4 多层网格叠加 → 精准压制逻辑病毒+固有缺陷

Usage:
    from mssclaw.core.hive_audit import HiveAuditor
    auditor = HiveAuditor()
    auditor.on_task_done(task_id, output)  # L0 + maybe L1
    auditor.on_phase_done()                # L2
    auditor.check_conflicts(agent_outputs)  # L3
    auditor.calibrate_direction()           # L4
"""
import time, json, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
from collections import defaultdict


class AuditLevel(Enum):
    L0_MICRO = 0       # 单任务微审计
    L1_BATCH = 1        # 批次检查点
    L2_PHASE = 2        # 阶段全量
    L3_CONFLICT = 3     # 跨Agent矛盾
    L4_MACRO = 4        # 大方向校准


@dataclass
class AuditFinding:
    level: AuditLevel
    severity: str        # "info"|"warning"|"critical"|"blocker"
    category: str        # "logic"|"direction"|"conflict"|"quality"|"drift"
    message: str
    source: str = ""     # task_id or phase_id
    timestamp: float = field(default_factory=time.time)


@dataclass
class HiveConfig:
    """蜂巢审计配置."""
    # L1: batch checkpoint triggers
    batch_size: int = 5              # 每 N 个任务触发 L1
    min_severity_for_trigger: str = "warning"  # 低于此等级不触发

    # L2: phase audit
    phase_trigger_tasks: int = 20    # 阶段任务数阈值

    # L3: conflict
    conflict_similarity_threshold: float = 0.85  # 输出相似度阈值

    # 散布化 (省算力)
    adaptive_density: bool = True    # 自适应检查密度
    min_density: int = 3             # 最小任务间隔
    max_density: int = 10            # 最大任务间隔
    current_density: int = 5         # 当前间隔 (动态调整)

    # 方向校准
    direction_check_interval: int = 50  # 每 N 个任务校准一次方向


class HiveAuditor:
    """蜂巢审计器 — 多层包围网.

    Usage:
        auditor = HiveAuditor()
        for task in tasks:
            result = agent.execute(task)
            auditor.on_task_done(task.id, result)  # L0 + maybe L1/L2/L4
        auditor.on_phase_done()                     # L2 full audit
        auditor.check_conflicts(all_outputs)         # L3
    """

    def __init__(self, config: HiveConfig = None, audit_fn: Callable = None):
        self.config = config or HiveConfig()
        self._audit_fn = audit_fn  # external audit function (e.g., AuditAgent)
        self._task_count = 0
        self._phase_task_count = 0
        self._findings: list[AuditFinding] = []
        self._checkpoints: list[dict] = []
        self._drift_vector: list[float] = []  # 方向漂移累积
        self._last_elevation_idx: int = 0     # 上次升级后的索引
        self._lock = threading.Lock()

    # ═══ L0: 微观层 — 单任务微审计 ═══

    def on_task_done(self, task_id: str, output: str) -> list[AuditFinding]:
        """每完成一个任务时调用. 触发 L0 + 可能 L1/L2/L4."""
        findings = []

        with self._lock:
            self._task_count += 1
            self._phase_task_count += 1

        # L0: 微观审计 (每条都审, 但极轻量)
        l0 = self._micro_audit(task_id, output)
        findings.extend(l0)

        # L1: 批次检查点
        if self._task_count % self.config.batch_size == 0:
            l1 = self._batch_checkpoint()
            findings.extend(l1)

        # L2: 阶段全量
        if self._phase_task_count >= self.config.phase_trigger_tasks:
            l2 = self._phase_full_audit()
            findings.extend(l2)
            self._phase_task_count = 0  # 重置阶段计数

        # L4: 方向校准
        if self._task_count % self.config.direction_check_interval == 0:
            l4 = self._calibrate_direction()
            findings.extend(l4)

        # 自适应密度调整
        if self.config.adaptive_density:
            severe = sum(1 for f in findings if f.severity in ("critical", "blocker"))
            if severe > 0:
                self.config.current_density = max(self.config.min_density,
                    self.config.current_density // 2)
            else:
                self.config.current_density = min(self.config.max_density,
                    self.config.current_density + 1)

        with self._lock:
            self._findings.extend(findings)

        return findings

    def _micro_audit(self, task_id: str, output: str) -> list[AuditFinding]:
        """L0: 轻量级单任务审计."""
        findings = []
        # 基础检查: 空输出 / 过短 / 重复模式
        if not output or len(output) < 10:
            findings.append(AuditFinding(
                level=AuditLevel.L0_MICRO, severity="warning",
                category="quality", message="Output too short or empty",
                source=task_id
            ))
        # 逻辑病毒检测: 自指涉 / 无限循环标记
        dangerous = ["while True:", "while (true)", "eval(", "exec(", "os.system("]
        for d in dangerous:
            if d in output.lower():
                findings.append(AuditFinding(
                    level=AuditLevel.L0_MICRO, severity="critical",
                    category="logic", message=f"Dangerous pattern: {d}",
                    source=task_id
                ))

        # 外部审计器 (如果配置了)
        if self._audit_fn:
            try:
                result = self._audit_fn(output)
                if result and getattr(result, 'score', 0) < 0.5:
                    findings.append(AuditFinding(
                        level=AuditLevel.L0_MICRO, severity="warning",
                        category="quality", message=f"External audit score low: {result.score}",
                        source=task_id
                    ))
            except:
                pass

        return findings

    # ═══ L1: 批次层 — 累积触发检查点 ═══

    def _batch_checkpoint(self) -> list[AuditFinding]:
        """L1: 批次检查点 — 检查最近 N 个任务的质量趋势."""
        findings = []
        recent = self._findings[-self.config.batch_size * 3:]  # 最近3倍批次

        # 质量下滑趋势
        severe_count = sum(1 for f in recent if f.severity in ("critical", "blocker"))
        warning_count = sum(1 for f in recent if f.severity == "warning")

        if severe_count >= 2:
            findings.append(AuditFinding(
                level=AuditLevel.L1_BATCH, severity="critical",
                category="quality",
                message=f"Batch checkpoint: {severe_count} severe issues in recent tasks"
            ))
        elif warning_count >= 3:
            findings.append(AuditFinding(
                level=AuditLevel.L1_BATCH, severity="warning",
                category="quality",
                message=f"Batch checkpoint: {warning_count} warnings accumulated"
            ))

        # 记录检查点
        self._checkpoints.append({
            "level": "L1", "task_count": self._task_count,
            "severe": severe_count, "warning": warning_count,
            "time": time.time()
        })

        return findings

    # ═══ L2: 阶段层 — 全量审计 ═══

    def _phase_full_audit(self) -> list[AuditFinding]:
        """L2: 阶段全量审计 — 对本阶段所有发现做综合判断."""
        findings = []
        phase_findings = self._findings[-self.config.phase_trigger_tasks * 3:]

        # 按类别聚合
        by_cat = defaultdict(list)
        for f in phase_findings:
            by_cat[f.category].append(f)

        # 逻辑矛盾检测
        logic_count = len(by_cat.get("logic", []))
        if logic_count >= 3:
            findings.append(AuditFinding(
                level=AuditLevel.L2_PHASE, severity="blocker",
                category="logic",
                message=f"Phase audit: {logic_count} logic issues — potential logic virus"
            ))

        # 方向漂移
        drift_count = len(by_cat.get("drift", []))
        if drift_count >= 2:
            findings.append(AuditFinding(
                level=AuditLevel.L2_PHASE, severity="critical",
                category="direction",
                message=f"Phase audit: {drift_count} direction drifts — may need recalibration"
            ))

        # 质量趋势
        quality_count = len(by_cat.get("quality", []))
        avg_samples = max(self._phase_task_count, 1)
        quality_ratio = quality_count / avg_samples
        if quality_ratio > 0.3:
            findings.append(AuditFinding(
                level=AuditLevel.L2_PHASE, severity="warning",
                category="quality",
                message=f"Phase audit: quality issue rate {quality_ratio:.0%}"
            ))

        # 记录阶段检查点
        self._checkpoints.append({
            "level": "L2", "task_count": self._task_count,
            "categories": {k: len(v) for k, v in by_cat.items()},
            "time": time.time()
        })

        return findings

    # ═══ L3: 冲突层 — 跨 Agent 矛盾检测 ═══

    def check_conflicts(self, agent_outputs: dict[str, list[str]]) -> list[AuditFinding]:
        """L3: 跨 Agent 冲突检测.

        Args:
            agent_outputs: {agent_name: [output1, output2, ...]}
        """
        findings = []

        # 简单相似度检测: 归一化文本
        all_texts = []
        for agent, outputs in agent_outputs.items():
            for o in outputs:
                normalized = " ".join(o.lower().split()[:20])  # 前20词
                all_texts.append((agent, normalized))

        # 检测矛盾: 如果两个 Agent 产出高度相似但方向相反
        for i, (a1, t1) in enumerate(all_texts):
            for j, (a2, t2) in enumerate(all_texts):
                if i >= j or a1 == a2:
                    continue
                # 检查否定词冲突
                if ("not" in t1) != ("not" in t2):
                    findings.append(AuditFinding(
                        level=AuditLevel.L3_CONFLICT, severity="warning",
                        category="conflict",
                        message=f"Potential contradiction: {a1} vs {a2}",
                        source=f"{a1}/{a2}"
                    ))

        return findings

    # ═══ L4: 宏面层 — 大方向逻辑校准 ═══

    def _calibrate_direction(self) -> list[AuditFinding]:
        """L4: 大方向校准 — 检查整体是否偏离目标."""
        findings = []

        # 从最近检查点中提取方向信号
        recent_cps = self._checkpoints[-5:]
        if not recent_cps:
            return findings

        # 计算漂移: 如果连续检查点 severity 递增 → 方向偏了
        severity_scores = {"info": 0, "warning": 1, "critical": 2, "blocker": 3}
        recent_severity = []
        for cp in recent_cps:
            if cp.get("severe", 0) > 0:
                recent_severity.append(severity_scores["critical"])
            elif cp.get("warning", 0) > 0:
                recent_severity.append(severity_scores["warning"])
            else:
                recent_severity.append(severity_scores["info"])

        if len(recent_severity) >= 3:
            self._drift_vector.append(sum(recent_severity) / len(recent_severity))
            if len(self._drift_vector) >= 3:
                # 趋势: 最近3个方向的移动平均
                trend = sum(self._drift_vector[-3:]) / 3
                if trend > 1.5:  # 持续在 warning 以上
                    findings.append(AuditFinding(
                        level=AuditLevel.L4_MACRO, severity="critical",
                        category="direction",
                        message=f"Direction drift detected: avg severity {trend:.1f} — recalibrate strategy"
                    ))

        return findings

    def on_phase_done(self):
        """强制触发阶段审计."""
        return self._phase_full_audit()

    def calibrate_direction(self):
        """强制触发方向校准."""
        return self._calibrate_direction()

    # ═══ Status ═══

    def status(self) -> dict:
        return {
            "total_tasks": self._task_count,
            "phase_tasks": self._phase_task_count,
            "total_findings": len(self._findings),
            "checkpoints": len(self._checkpoints),
            "current_density": self.config.current_density,
            "drift_vector": self._drift_vector[-3:] if self._drift_vector else [],
            "by_severity": {
                s: sum(1 for f in self._findings if f.severity == s)
                for s in ["info", "warning", "critical", "blocker"]
            },
            "by_level": {
                str(l.name): sum(1 for f in self._findings if f.level == l)
                for l in AuditLevel
            },
        }

    def snapshot(self) -> list[dict]:
        """导出所有发现."""
        return [{
            "level": f.level.name, "severity": f.severity,
            "category": f.category, "message": f.message,
            "source": f.source, "time": f.timestamp
        } for f in self._findings]

    # ═══ 升级机制: A6 逻辑升维 — 检查无效 → 停止死磕 → 升维 ═══

    def should_escalate(self) -> tuple[bool, str, Optional[str]]:
        """
        判断是否应该升级 (A6 矛盾升维).

        逻辑: 同一类别连续 N 次检查无效 → 不在这一层继续死磕 → 升维
        Returns: (should_escalate, reason, target_dimension)
        """
        if not self._findings:
            return False, "", None

        # 检查最近发现 (只看升级点之后)
        recent = self._findings[self._last_elevation_idx:]
        by_cat = defaultdict(int)
        for f in recent:
            if f.severity in ("critical", "blocker"):
                by_cat[f.category] += 1

        # 同一类别 >=3 次 → 当前层检查无效, 需要升维
        for cat, count in by_cat.items():
            if count >= 3:
                dim = self._get_elevation_dimension(cat)
                return True, f"{count} critical findings in '{cat}' — elevation needed", dim

        # 检查点持续恶化
        recent_cps = self._checkpoints[-3:]
        if len(recent_cps) >= 3:
            worsening = all(
                (recent_cps[i].get("severe", 0) + recent_cps[i].get("warning", 0)) >= 
                (recent_cps[i-1].get("severe", 0) + recent_cps[i-1].get("warning", 0))
                for i in range(1, len(recent_cps))
            )
            if worsening:
                return True, "Checkpoints worsening — current level insufficient", "strategic"

        return False, "", None

    def _get_elevation_dimension(self, category: str) -> str:
        """根据问题类别返回应升级到的维度."""
        dim_map = {
            "quality": "process",      # 质量问题 → 流程维度
            "logic": "symbolic",       # 逻辑问题 → 符号维度
            "conflict": "semantic",    # 冲突 → 语义维度
            "direction": "strategic",  # 方向 → 战略维度
            "drift": "strategic",      # 漂移 → 战略维度
        }
        return dim_map.get(category, "meta")

    def trigger_elevation(self, category: str, reason: str) -> AuditFinding:
        """
        触发 A6 逻辑升维 — 发起 MOLT_SIGNAL.
        不在当前层继续死磕, 而是把问题提升到更高维度.
        """
        dim = self._get_elevation_dimension(category)
        finding = AuditFinding(
            level=AuditLevel.L4_MACRO,  # 宏面层发出升级信号
            severity="blocker" if category in ("logic", "conflict") else "critical",
            category="direction",
            message=f"A6 ELEVATION: {category} → {dim} dimension. {reason}",
            source="hive_escalation"
        )
        self._findings.append(finding)
        self._last_elevation_idx = len(self._findings)  # 标记升级点
        return finding

    def investigate(self) -> dict:
        """
        启动调查 — 不是增加检查, 而是更深层的分析.
        返回调查建议和元分析结果.
        """
        should_esc, reason, dim = self.should_escalate()
        if not should_esc:
            return {"action": "continue", "reason": "no escalation needed"}

        # 深层分析: 聚合所有发现中的模式
        all_categories = defaultdict(int)
        all_severities = defaultdict(int)
        for f in self._findings[-20:]:
            all_categories[f.category] += 1
            all_severities[f.severity] += 1

        top_cat = max(all_categories, key=all_categories.get) if all_categories else "unknown"

        return {
            "action": "elevate",
            "reason": reason,
            "target_dimension": dim or self._get_elevation_dimension(top_cat),
            "pattern_analysis": {
                "dominant_category": top_cat,
                "category_distribution": dict(all_categories),
                "severity_distribution": dict(all_severities),
            },
            "recommendation": f"Stop checking at current level. Elevate {top_cat} issue to {dim} dimension.",
        }

    def tick_delta(self, delta_protocol=None):
        """
        联动 DeltaProtocol: 每次检查后 tick 一次。
        如果 delta 检测到闭合/平台期 → 自动触发升级.
        """
        if delta_protocol:
            delta_protocol.tick(score=self.status().get("by_severity", {}).get("critical", 0))
            if delta_protocol.molting_alert:
                return self.trigger_elevation("direction", "Delta closure detected — auto-elevation")
