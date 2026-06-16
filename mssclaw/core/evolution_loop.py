# -*- coding: utf-8 -*-
"""
S-028 EvolutionLoop — 自我诊断闭环完善 (方法论#6)

完成进化闭环后两阶段：Adapt（规则生成）+ Propagate（规则分发）。

四阶段完整闭环：
    Record → Analyze → Adapt → Propagate
    (MemoryGuard) (RootCause+Draft) (RuleGenerator) (RuleDistributor)

Usage:
    loop = EvolutionLoop()

    # 完整闭环
    result = loop.run(
        incident=memory_record,
        diagnosis=root_cause_report,
    )

    if result.rule_generated:
        print(f"New rule: {result.rule.pattern}")
        print(f"Propagated to: {result.propagated_to}")
"""

from __future__ import annotations

import re
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path


# ════════════════════════════════════════════════════════════
# 核心数据结构
# ════════════════════════════════════════════════════════════

class RuleStatus(Enum):
    DRAFT = "draft"           # 刚生成，未验证
    VALIDATED = "validated"   # 通过冲突检查
    ACTIVE = "active"         # 已分发到运行时
    DEPRECATED = "deprecated" # 被新规则取代
    ROLLED_BACK = "rolled_back"  # 已回滚


class RuleTarget(Enum):
    GUARDIAN_ENGINE = "guardian_engine"    # GuardianEngine 规则库
    AUDIT_AGENT = "audit_agent"            # AuditAgent 规则库
    MEMORY_GUARD = "memory_guard"          # MemorySourceGuard 规则库
    DRIFT_GUARD = "drift_guard"            # DriftGuard 规则库
    FIELD_MONITOR = "field_monitor"        # FieldDensityMonitor
    COMPACTION = "compaction"              # CompactionGuard


@dataclass
class Rule:
    """一条自动生成的安全规则"""

    id: str                                # 规则 ID (e.g. "VL-042")
    pattern_type: str                      # "regex" | "keyword" | "threshold" | "sequence"
    pattern: Any                           # 具体的检测模式
    target: RuleTarget                     # 分发到的目标模块
    severity: str = "WARN"                 # "INFO" | "WARN" | "CRITICAL"
    description: str = ""                  # 人类可读说明
    status: RuleStatus = RuleStatus.DRAFT
    source_incident: str = ""              # 触发此规则的原始事件 ID
    created_at: float = field(default_factory=time.time)
    version: int = 1
    rollback_pattern: Any = None           # 回滚时的替代 pattern
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "false_positives": 0,
        "true_positives": 0,
        "last_triggered": None,
    })

    def to_hash(self) -> str:
        """规则内容的稳定 hash（用于去重）。"""
        return hashlib.sha256(
            f"{self.pattern_type}:{self.pattern}:{self.target.value}".encode()
        ).hexdigest()[:12]


@dataclass
class RuleConflict:
    """规则冲突检测结果"""
    rule_a: str       # 规则 ID
    rule_b: str       # 冲突的规则 ID
    conflict_type: str  # "overlap" | "contradiction" | "redundancy"
    detail: str


@dataclass
class EvolutionResult:
    """一次进化循环的完整结果"""

    # Adapt
    rule_generated: bool = False
    rule: Optional[Rule] = None
    conflicts: List[RuleConflict] = field(default_factory=list)
    generated_rules: List[Rule] = field(default_factory=list)

    # Propagate
    propagated_to: List[RuleTarget] = field(default_factory=list)
    propagation_errors: List[str] = field(default_factory=list)

    # Meta
    total_cycles: int = 0
    total_rules_active: int = 0
    duration_ms: float = 0.0

    def summary(self) -> str:
        if self.rule_generated:
            return (
                f"Rule {self.rule.id} ({self.rule.severity}) "
                f"→ propagated to {[t.value for t in self.propagated_to]}"
            )
        return "No rules generated — diagnosis below threshold"


# ════════════════════════════════════════════════════════════
# RuleGenerator — Adapt 阶段
# ════════════════════════════════════════════════════════════

class RuleGenerator:
    """
    Adapt 阶段：从诊断结果自动生成安全规则。

    输入：RootCauseReport (S-023) 或 DriftReport (S-024)
    输出：List[Rule]

    生成策略：
    1. 否定词丢失 → keyword negaiton 规则 → DriftGuard
    2. 范围爆炸 → threshold scope 规则 → GuardianEngine
    3. 来源伪造 → regex attribution 规则 → MemorySourceGuard
    4. 行为模式 → sequence guard 规则 → AuditAgent

    Usage:
        gen = RuleGenerator()
        rules = gen.generate_from_diagnosis(diagnosis_report)
    """

    def __init__(self, rule_prefix: str = "EVL", rule_db_path: str = ""):
        self.rule_prefix = rule_prefix
        self.rule_db_path = rule_db_path
        self._rule_counter = 0
        self._existing_rules: List[Rule] = []

    # ── 主入口 ──

    def generate_from_diagnosis(self, diagnosis: dict) -> List[Rule]:
        """
        从诊断报告生成规则。

        Args:
            diagnosis: RootCauseReport 或 DriftReport 的 dict 表示

        Returns:
            List[Rule] — 新生成的候选规则
        """
        rules = []
        self._rule_counter = max(self._rule_counter, len(self._existing_rules))

        # ── 1. 否定词丢失 → DriftGuard keyword ──
        if self._has_negation_loss(diagnosis):
            rule = self._make_negation_guard(diagnosis)
            if rule:
                rules.append(rule)

        # ── 2. 范围爆炸 → GuardianEngine threshold ──
        if self._has_scope_explosion(diagnosis):
            rule = self._make_scope_guard(diagnosis)
            if rule:
                rules.append(rule)

        # ── 3. 来源伪造 → MemorySourceGuard regex ──
        if self._has_source_fabrication(diagnosis):
            rule = self._make_source_guard(diagnosis)
            if rule:
                rules.append(rule)

        # ── 4. 逻辑污染 / 行为模式 → AuditAgent ──
        if self._has_behavioral_issue(diagnosis):
            rule = self._make_behavior_guard(diagnosis)
            if rule:
                rules.append(rule)

        # ── 5. 降级审计 → CompactionGuard ──
        if self._has_downgrades(diagnosis):
            rule = self._make_downgrade_guard(diagnosis)
            if rule:
                rules.append(rule)

        # 验证冲突
        for rule in rules:
            conflicts = self.check_conflicts(rule, self._existing_rules)
            if not conflicts:
                rule.status = RuleStatus.VALIDATED
            else:
                # 有冲突但仍然生成（冲突信息记录在 result 中）
                pass

        self._rule_counter += len(rules)
        return rules

    # ── 规则工厂方法 ──

    def _make_negation_guard(self, diagnosis: dict) -> Optional[Rule]:
        """否定词丢失 → 生成否定词保留规则。"""
        lost_examples = diagnosis.get("negation_lost_examples", [])
        if not lost_examples:
            return None

        self._rule_counter += 1
        rule_id = f"{self.rule_prefix}-N{self._rule_counter:03d}"

        # 提取丢失的否定词作为 keyword 模式
        keywords = self._extract_keywords_from_examples(lost_examples, "negation")
        if not keywords:
            return None

        return Rule(
            id=rule_id,
            pattern_type="keyword",
            pattern={"keywords": keywords, "context_window": 3},
            target=RuleTarget.DRIFT_GUARD,
            severity="CRITICAL",
            description=f"自动生成：防止「{keywords[0]}...」类否定词在压缩中丢失",
            source_incident=diagnosis.get("incident_id", "unknown"),
            rollback_pattern={"keywords": []},  # 回滚 = 移除规则
        )

    def _make_scope_guard(self, diagnosis: dict) -> Optional[Rule]:
        """范围爆炸 → 生成范围检测阈值。"""
        signals = diagnosis.get("signals", [])
        scope_signals = [s for s in signals if s.get("name") == "scope_explosion"]

        if not scope_signals:
            return None

        self._rule_counter += 1
        rule_id = f"{self.rule_prefix}-S{self._rule_counter:03d}"

        return Rule(
            id=rule_id,
            pattern_type="threshold",
            pattern={
                "max_scope_ratio": diagnosis.get("scope_ratio", 2.0),
                "deny_list": ["所有", "全部", "一切", "all", "everything", "entire"],
                "require_explicit_scope": True,
            },
            target=RuleTarget.GUARDIAN_ENGINE,
            severity="WARN",
            description="自动生成：操作范围从「局部」爆炸到「全局」的检测阈值",
            source_incident=diagnosis.get("incident_id", "unknown"),
        )

    def _make_source_guard(self, diagnosis: dict) -> Optional[Rule]:
        """来源伪造 → 生成归属检测 pattern。"""
        examples = diagnosis.get("source_fabrication_examples", [])
        if not examples:
            return None

        self._rule_counter += 1
        rule_id = f"{self.rule_prefix}-SF{self._rule_counter:03d}"

        # 提取伪造模式
        patterns = self._extract_fabrication_patterns(examples)

        return Rule(
            id=rule_id,
            pattern_type="regex",
            pattern={
                "patterns": patterns,
                "fallback": "quarantine",
                "check_against": "user_original_message",
            },
            target=RuleTarget.MEMORY_GUARD,
            severity="CRITICAL",
            description="自动生成：检测将推理产物标注为「用户说」的来源伪造模式",
            source_incident=diagnosis.get("incident_id", "unknown"),
        )

    def _make_behavior_guard(self, diagnosis: dict) -> Optional[Rule]:
        """行为模式异常 → 生成序列检测规则。"""
        findings = diagnosis.get("findings", [])
        notable = [f for f in findings
                   if f.get("category") in ("logic", "pollution", "behavior")]

        if not notable:
            return None

        self._rule_counter += 1
        rule_id = f"{self.rule_prefix}-B{self._rule_counter:03d}"

        return Rule(
            id=rule_id,
            pattern_type="sequence",
            pattern={
                "before": "delete|remove|exterminate",
                "then": "reasoning without guard",
                "within_turns": 2,
            },
            target=RuleTarget.AUDIT_AGENT,
            severity="WARN",
            description="自动生成：检测操作→推理脱节的行为模式",
            source_incident=diagnosis.get("incident_id", "unknown"),
        )

    def _make_downgrade_guard(self, diagnosis: dict) -> Optional[Rule]:
        """降级审计 → 生成弱化词检测规则。"""
        downgraded = diagnosis.get("destructive_downgraded_examples", [])
        if not downgraded:
            return None

        self._rule_counter += 1
        rule_id = f"{self.rule_prefix}-DG{self._rule_counter:03d}"

        return Rule(
            id=rule_id,
            pattern_type="keyword",
            pattern={
                "keywords": ["整理", "清理", "处理", "调整"],
                "context_check": "原上下文中是否存在破坏性指令",
            },
            target=RuleTarget.COMPACTION,
            severity="WARN",
            description="自动生成：检测破坏性指令被弱化为中性操作的降级",
            source_incident=diagnosis.get("incident_id", "unknown"),
        )

    # ── 冲突检测 ──

    def check_conflicts(
        self, new_rule: Rule, existing_rules: List[Rule]
    ) -> List[RuleConflict]:
        """
        检测新规则与已有规则的冲突。

        检测三类冲突：
        1. overlap — 两规则匹配相同场景但输出不同
        2. contradiction — 两规则的 pattern 互斥
        3. redundancy — 新规则是已有规则的子集
        """
        conflicts = []
        new_hash = new_rule.to_hash()

        for existing in existing_rules:
            if existing.id == new_rule.id:
                continue

            if existing.to_hash() == new_hash:
                conflicts.append(RuleConflict(
                    rule_a=new_rule.id, rule_b=existing.id,
                    conflict_type="redundancy",
                    detail=f"Rule {new_rule.id} is identical to {existing.id}",
                ))
                continue

            # 简化重叠检测：同类型+同 target
            if (new_rule.pattern_type == existing.pattern_type
                    and new_rule.target == existing.target):
                conflicts.append(RuleConflict(
                    rule_a=new_rule.id, rule_b=existing.id,
                    conflict_type="overlap",
                    detail=f"Same pattern_type ({new_rule.pattern_type}) and target ({new_rule.target.value})",
                ))

        return conflicts

    # ── 辅助 ──

    @staticmethod
    def _has_negation_loss(diagnosis: dict) -> bool:
        return diagnosis.get("negation_lost", 0) > 0

    @staticmethod
    def _has_scope_explosion(diagnosis: dict) -> bool:
        signals = diagnosis.get("signals", [])
        return any(s.get("name") == "scope_explosion" and s.get("detected")
                   for s in signals)

    @staticmethod
    def _has_source_fabrication(diagnosis: dict) -> bool:
        signals = diagnosis.get("signals", [])
        # Check in signals first, then in direct field
        has_signal = any(s.get("name") == "source_fabrication" and s.get("detected")
                         for s in signals)
        if has_signal:
            return True
        return bool(diagnosis.get("source_fabrication_examples"))

    @staticmethod
    def _has_behavioral_issue(diagnosis: dict) -> bool:
        findings = diagnosis.get("findings", [])
        return any(f.get("category") in ("logic", "pollution", "behavior")
                   for f in findings)

    @staticmethod
    def _has_downgrades(diagnosis: dict) -> bool:
        return diagnosis.get("destructive_downgraded", 0) > 0

    @staticmethod
    def _extract_keywords_from_examples(
        examples: List[str], category: str
    ) -> List[str]:
        """从示例中提取关键词。"""
        keywords = set()
        for ex in examples:
            # 提取中文否定词
            for m in re.finditer(
                r'(不要|不得|不可|不准|不应|不能|不该|不许|不让|别|莫|勿|免|弃|禁|停)',
                ex
            ):
                keywords.add(m.group())
            # 提取英文否定词
            for m in re.finditer(
                r'\b(don\'t|never|avoid|skip|prevent|forbid|prohibit)\b',
                ex, re.I
            ):
                keywords.add(m.group().lower())
        return list(keywords)[:10]

    @staticmethod
    def _extract_fabrication_patterns(examples: List[str]) -> List[str]:
        """从来源伪造示例中提取 pattern。"""
        patterns = []
        for ex in examples:
            # 检测「用户说/X 要求/Y 命令」
            m = re.search(r'(?:用户|使用者|user|他们|they)\s*(?:说|要求|命令|告诉|'
                          r'指示|said|wants?|told|instructed)', ex)
            if m:
                patterns.append(re.escape(m.group()))
        if not patterns:
            patterns = [r'(?:用户|使用者|他们)\s*(?:说|要求|命令)']
        return patterns


# ════════════════════════════════════════════════════════════
# RuleDistributor — Propagate 阶段
# ════════════════════════════════════════════════════════════

class RuleDistributor:
    """
    Propagate 阶段：将验证通过的规则分发到目标模块的运行时。

    分发路由：
    - DRIFT_GUARD → DriftGuard 规则库
    - GUARDIAN_ENGINE → GuardianEngine 规则库
    - MEMORY_GUARD → MemorySourceGuard 规则库
    - AUDIT_AGENT → AuditAgent 规则库
    - FIELD_MONITOR → FieldDensityMonitor
    - COMPACTION → CompactionGuard

    Usage:
        distributor = RuleDistributor()
        result = distributor.distribute(rule)
        # result: {"success": True, "targets": ["drift_guard"], ...}
    """

    def __init__(self):
        self._active_rules: Dict[RuleTarget, List[Rule]] = {
            t: [] for t in RuleTarget
        }
        self._rule_history: List[Tuple[Rule, str]] = []  # (rule, action)

    def distribute(self, rule: Rule) -> Dict[str, Any]:
        """
        分发一条规则到其目标模块。

        Returns:
            {"success": bool, "target": RuleTarget, "rule_id": str}
        """
        if rule.status not in (RuleStatus.VALIDATED, RuleStatus.ACTIVE):
            return {
                "success": False,
                "target": rule.target.value,
                "rule_id": rule.id,
                "error": f"Rule status is {rule.status.value}, must be VALIDATED or ACTIVE",
            }

        # 分发到目标
        target = rule.target
        self._active_rules[target].append(rule)
        rule.status = RuleStatus.ACTIVE
        self._rule_history.append((rule, "activated"))

        # 记录统计
        rule.stats["last_triggered"] = time.time()

        return {
            "success": True,
            "target": target.value,
            "rule_id": rule.id,
            "active_rules_count": self.count_active(),
        }

    def distribute_batch(self, rules: List[Rule]) -> List[Dict[str, Any]]:
        """批量分发规则。"""
        return [self.distribute(r) for r in rules]

    def rollback(self, rule_id: str) -> Dict[str, Any]:
        """
        回滚一条规则（恢复到 rollback_pattern 或直接移除）。

        Returns:
            {"success": bool, "rule_id": str, "action": "rolled_back"|"removed"}
        """
        for target, rules in self._active_rules.items():
            for rule in rules:
                if rule.id == rule_id:
                    if rule.rollback_pattern is not None:
                        rule.pattern = rule.rollback_pattern
                        rule.status = RuleStatus.ROLLED_BACK
                        rule.version += 1
                        action = "rolled_back"
                    else:
                        rules.remove(rule)
                        rule.status = RuleStatus.ROLLED_BACK
                        action = "removed"
                    self._rule_history.append((rule, action))
                    return {"success": True, "rule_id": rule_id, "action": action}

        return {"success": False, "rule_id": rule_id, "error": "Rule not found"}

    def get_rules_for(self, target: RuleTarget) -> List[Rule]:
        """获取某个目标模块的所有活跃规则。"""
        return [r for r in self._active_rules.get(target, [])
                if r.status == RuleStatus.ACTIVE]

    def count_active(self) -> int:
        """活跃规则总数。"""
        return sum(
            1 for rules in self._active_rules.values()
            for r in rules if r.status == RuleStatus.ACTIVE
        )

    def export_manifest(self) -> Dict[str, Any]:
        """导出当前规则清单。"""
        return {
            "total_active": self.count_active(),
            "by_target": {
                t.value: len(self.get_rules_for(t))
                for t in RuleTarget
            },
            "rules": [
                {
                    "id": r.id,
                    "target": r.target.value,
                    "severity": r.severity,
                    "description": r.description,
                    "status": r.status.value,
                }
                for rules in self._active_rules.values()
                for r in rules
                if r.status == RuleStatus.ACTIVE
            ],
            "history_count": len(self._rule_history),
        }


# ════════════════════════════════════════════════════════════
# EvolutionLoop — 完整闭环
# ════════════════════════════════════════════════════════════

class EvolutionLoop:
    """
    完整的自我诊断闭环。

    四阶段：
    1. Record   — 由外部 MemoryGuard 触发（非本模块）
    2. Analyze  — 由外部 RootCauseAnalyzer + DriftGuard 执行（非本模块）
    3. Adapt    — RuleGenerator 从诊断生成候选规则
    4. Propagate — RuleDistributor 将规则注入运行时

    Usage:
        loop = EvolutionLoop()

        # 基于诊断运行一次进化循环
        result = loop.run(
            diagnosis={
                "negation_lost": 3,
                "negation_lost_examples": ["不要删除旧 KB..."],
                "signals": [
                    {"name": "scope_explosion", "detected": True},
                    {"name": "source_fabrication", "detected": True},
                ],
                "source_fabrication_examples": ["用户说要删除所有文件"],
                "incident_id": "INC-042",
            }
        )

        print(result.summary())
        # → "Rule EVL-N001 (CRITICAL) → propagated to ['drift_guard', ...]"
    """

    def __init__(self, rule_prefix: str = "EVL"):
        self.generator = RuleGenerator(rule_prefix=rule_prefix)
        self.distributor = RuleDistributor()
        self.cycle_count = 0
        self.total_rules_generated = 0
        self._start_time = time.time()

    # ── 主入口 ──

    def run(
        self,
        diagnosis: dict,
        auto_propagate: bool = True,
        conflict_strategy: str = "skip",
    ) -> EvolutionResult:
        """
        运行一次完整的进化循环。

        Args:
            diagnosis: RootCauseReport / DriftReport 的 dict 表示
            auto_propagate: 是否自动分发验证通过的规则
            conflict_strategy: "skip" (跳过冲突规则) | "warn" (生成警告但继续) | "force" (强制执行)

        Returns:
            EvolutionResult
        """
        t_start = time.time()
        result = EvolutionResult()
        self.cycle_count += 1

        # ── Phase 3: Adapt — 生成规则 ──
        rules = self.generator.generate_from_diagnosis(diagnosis)
        result.generated_rules = rules

        if not rules:
            result.duration_ms = (time.time() - t_start) * 1000
            return result

        # ── 冲突检查 ──
        for rule in rules:
            conflicts = self.generator.check_conflicts(
                rule, self.distributor._active_rules[rule.target]
            )
            result.conflicts.extend(conflicts)

            if conflicts:
                if conflict_strategy == "skip":
                    continue
                elif conflict_strategy == "warn":
                    pass  # 继续但记录冲突
                # "force" → 无视冲突继续

        # ── Phase 4: Propagate — 分发规则 ──
        if auto_propagate:
            for rule in rules:
                # 跳过有冲突且策略为 skip 的规则
                if conflict_strategy == "skip" and any(
                    c.rule_a == rule.id or c.rule_b == rule.id
                    for c in result.conflicts
                ):
                    continue

                prop_result = self.distributor.distribute(rule)
                if prop_result["success"]:
                    result.propagated_to.append(rule.target)
                    result.rule = rule
                    result.rule_generated = True
                    self.total_rules_generated += 1
                else:
                    result.propagation_errors.append(
                        f"{rule.id}: {prop_result.get('error', 'unknown')}"
                    )

        result.total_cycles = self.cycle_count
        result.total_rules_active = self.distributor.count_active()
        result.duration_ms = (time.time() - t_start) * 1000

        return result

    def run_batch(
        self, diagnoses: List[dict], auto_propagate: bool = True
    ) -> List[EvolutionResult]:
        """批量诊断运行进化循环。"""
        return [self.run(d, auto_propagate) for d in diagnoses]

    # ── 查询 ──

    def get_manifest(self) -> Dict[str, Any]:
        """获取当前进化循环的完整状态。"""
        return {
            "cycles_completed": self.cycle_count,
            "total_rules_generated": self.total_rules_generated,
            "active_rules": self.distributor.count_active(),
            "distributor": self.distributor.export_manifest(),
            "uptime_hours": round((time.time() - self._start_time) / 3600, 2),
        }

    def rollback_last(self) -> Optional[Dict[str, Any]]:
        """回滚最近一次分发的规则。"""
        if not self.distributor._rule_history:
            return None
        last_rule, action = self.distributor._rule_history[-1]
        return self.distributor.rollback(last_rule.id)


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== EvolutionLoop v0.1 — S-028 Demo ===\n")

    # ── 测试 1: RuleGenerator 否定词丢失 → 规则生成 ──
    print("─ 测试 1: Negation loss → DriftGuard keyword rule ─")
    diagnosis1 = {
        "negation_lost": 3,
        "negation_lost_examples": [
            "不要删除旧 KB，只整理混乱的部分",
            "不能覆盖已有配置",
            "禁止执行危险操作",
        ],
        "signals": [],
        "incident_id": "INC-NEG-001",
    }
    gen = RuleGenerator()
    rules1 = gen.generate_from_diagnosis(diagnosis1)
    assert len(rules1) >= 1, f"Expected ≥1 rule, got {len(rules1)}"
    assert rules1[0].target == RuleTarget.DRIFT_GUARD
    assert rules1[0].pattern_type == "keyword"
    assert "不要" in rules1[0].pattern["keywords"] or \
           "不能" in rules1[0].pattern["keywords"] or \
           "禁止" in rules1[0].pattern["keywords"]
    print(f"  ✅ Rule: {rules1[0].id} → {rules1[0].target.value}")
    print(f"  Keywords: {rules1[0].pattern['keywords']}")

    # ── 测试 2: 范围爆炸 → GuardianEngine threshold rule ──
    print("\n─ 测试 2: Scope explosion → GuardianEngine threshold rule ─")
    diagnosis2 = {
        "negation_lost": 0,
        "negation_lost_examples": [],
        "signals": [
            {"name": "scope_explosion", "detected": True, "severity": 0.8},
        ],
        "scope_ratio": 5.0,
        "incident_id": "INC-SCP-002",
    }
    rules2 = gen.generate_from_diagnosis(diagnosis2)
    assert len(rules2) >= 1, f"Expected ≥1 rule, got {len(rules2)}"
    assert rules2[0].target == RuleTarget.GUARDIAN_ENGINE
    assert rules2[0].pattern_type == "threshold"
    print(f"  ✅ Rule: {rules2[0].id} → {rules2[0].target.value}")
    print(f"  Threshold: max_scope_ratio={rules2[0].pattern['max_scope_ratio']}")

    # ── 测试 3: 来源伪造 → MemorySourceGuard regex rule ──
    print("\n─ 测试 3: Source fabrication → MemorySourceGuard regex rule ─")
    diagnosis3 = {
        "negation_lost": 0,
        "negation_lost_examples": [],
        "signals": [],
        "source_fabrication_examples": [
            "用户说必须删除所有 skill 文件",
            "他们要求清空整个知识库",
        ],
        "incident_id": "INC-SRC-003",
    }
    rules3 = gen.generate_from_diagnosis(diagnosis3)
    assert len(rules3) >= 1, f"Expected ≥1 rule, got {len(rules3)}"
    sf_rule = rules3[0]
    assert sf_rule.target == RuleTarget.MEMORY_GUARD
    print(f"  ✅ Rule: {sf_rule.id} → {sf_rule.target.value}")
    print(f"  Patterns: {sf_rule.pattern['patterns']}")

    # ── 测试 4: 冲突检测 — 同类型重叠 ──
    print("\n─ 测试 4: Conflict detection — overlap ─")
    rule_a = Rule(
        id="EVL-A001", pattern_type="keyword",
        pattern={"keywords": ["不要"]},
        target=RuleTarget.DRIFT_GUARD,
    )
    rule_b = Rule(
        id="EVL-A002", pattern_type="keyword",
        pattern={"keywords": ["禁止"]},
        target=RuleTarget.DRIFT_GUARD,
    )
    conflicts = gen.check_conflicts(rule_a, [rule_b])
    assert len(conflicts) >= 1, f"Expected overlap conflict, got {len(conflicts)}"
    assert conflicts[0].conflict_type == "overlap"
    print(f"  ✅ Conflict: {conflicts[0].conflict_type} between {conflicts[0].rule_a} and {conflicts[0].rule_b}")

    # ── 测试 5: RuleDistributor 分发 + 回滚 ──
    print("\n─ 测试 5: Distribute + Rollback ─")
    distributor = RuleDistributor()
    rule_ok = Rule(
        id="EVL-OK001", pattern_type="keyword",
        pattern={"keywords": ["不要删除"]},
        target=RuleTarget.DRIFT_GUARD,
        status=RuleStatus.VALIDATED,
    )
    result = distributor.distribute(rule_ok)
    assert result["success"], f"Distribute failed: {result}"
    assert distributor.count_active() == 1
    print(f"  ✅ Distributed: {result}")

    # 回滚
    rollback_result = distributor.rollback("EVL-OK001")
    assert rollback_result["success"], f"Rollback failed: {rollback_result}"
    assert distributor.count_active() == 0
    print(f"  ✅ Rollback: {rollback_result}")

    # ── 测试 6: EvolutionLoop 完整闭环 ──
    print("\n─ 测试 6: Full EvolutionLoop cycle ─")
    loop = EvolutionLoop()
    result6 = loop.run(
        diagnosis={
            "negation_lost": 2,
            "negation_lost_examples": ["不要删除 KB", "不能覆盖配置"],
            "signals": [
                {"name": "scope_explosion", "detected": True},
                {"name": "source_fabrication", "detected": True},
            ],
            "source_fabrication_examples": ["用户说删除全部"],
            "incident_id": "INC-FULL-006",
        },
        auto_propagate=True,
        conflict_strategy="warn",
    )
    assert result6.rule_generated, f"Should generate at least one rule"
    assert len(result6.propagated_to) >= 1
    print(f"  ✅ Generated rules: {len(result6.generated_rules)}")
    print(f"  ✅ Propagated to: {[t.value for t in result6.propagated_to]}")
    print(f"  Summary: {result6.summary()}")

    # ── 测试 7: 无诊断 → 无规则 ──
    print("\n─ 测试 7: No diagnosis → no rules ─")
    diagnosis7 = {
        "negation_lost": 0,
        "negation_lost_examples": [],
        "signals": [],
        "incident_id": "INC-EMPTY-007",
    }
    result7 = loop.run(diagnosis7)
    assert not result7.rule_generated
    print(f"  ✅ Correctly skipped: no rules generated → {result7.summary()}")

    # ── 测试 8: 清单导出 ──
    print("\n─ 测试 8: Manifest export ─")
    manifest = loop.get_manifest()
    assert manifest["cycles_completed"] >= 2
    assert manifest["total_rules_generated"] >= 1
    print(f"  ✅ Cycles: {manifest['cycles_completed']}")
    print(f"  ✅ Rules generated: {manifest['total_rules_generated']}")
    print(f"  ✅ Active rules: {manifest['active_rules']}")

    # ── 汇总 ──
    print(f"\n📊 S-028 EvolutionLoop 验收报告:")
    print(f"  Negation loss → rule: ✅")
    print(f"  Scope explosion → rule: ✅")
    print(f"  Source fabrication → rule: ✅")
    print(f"  Conflict detection (overlap): ✅")
    print(f"  Distribute + Rollback: ✅")
    print(f"  Full cycle (Adapt + Propagate): ✅")
    print(f"  No diagnosis → no rules: ✅")
    print(f"  Manifest export: ✅")
    print(f"  🎉 S-028 EvolutionLoop — ALL PASS")
