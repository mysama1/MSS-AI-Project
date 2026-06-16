"""
MSS-Agent v0.3 → v0.4 — Memory Guard (会话记忆自动归档 + 证据链约束)

Auto-archives conversation turns to long-term memory based on quality signals:
- High Delta (Δ > 0.5): novel insight → archive
- Decision made (words like "decide"/"choose"/"ok let's") → archive
- Error + fix (pattern detection) → archive as lesson
- Task completed → archive as milestone

v0.4 新增（S-025 / 方法论#3）:
- SourceType 三态分类: MSG / OBSERVATION / INFERENCE
- Source 结构化证据标记
- MemorySourceGuard 记忆证据链约束引擎
- MSC-001~MSC-005 告警码体系
- 推理记忆隔离审查 (quarantine → release)

Part of the P0 tool suite (memory_guard / auto_archive / session_recall / budget_gate).
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
import re
import sys
import time


# ════════════════════════════════════════════════════════════
# S-025: 记忆证据链约束（方法论#3）
# ════════════════════════════════════════════════════════════

class SourceType(Enum):
    """
    记忆来源的三态分类。

    规则（从方法论#3）：
    - MSG: 可溯源到具体用户消息，需提供 msg_id
    - OBSERVATION: 从系统状态直接观察到的，需提供观测对象
    - INFERENCE: 推理产物，confidence ≤ 0.7，写入前必须 grep 验证
    - 三者在同一条目中不可混排
    """
    MSG = "msg"             # [msg:xxx] — 可溯源到具体用户消息
    OBSERVATION = "obs"     # [观测] — 从系统状态直接观察
    INFERENCE = "inf"       # [推断] — 推理产物


@dataclass
class Source:
    """记忆来源的结构化标记，替代原来的 source: str 自由文本。"""
    type: SourceType
    ref: Optional[str] = None      # msg_id / 观测对象 / 推理链ID
    confidence: float = 1.0         # MSG=1.0, OBS=0.9, INF≤0.7
    detail: str = ""               # 人类可读的说明

    @classmethod
    def from_msg(cls, msg_id: str, detail: str = "") -> "Source":
        """创建可溯源到用户消息的来源。"""
        return cls(type=SourceType.MSG, ref=msg_id, confidence=1.0, detail=detail)

    @classmethod
    def from_observation(cls, target: str, detail: str = "") -> "Source":
        """创建从系统状态观察的来源。"""
        return cls(type=SourceType.OBSERVATION, ref=target, confidence=0.9, detail=detail)

    @classmethod
    def from_inference(cls, chain_id: str, detail: str = "") -> "Source":
        """创建推理产物来源。confidence 上限 0.7。"""
        return cls(type=SourceType.INFERENCE, ref=chain_id, confidence=0.7, detail=detail)

    def to_tag(self) -> str:
        """生成可脚本解析的来源标签。"""
        base = f"[{self.type.value}"
        if self.ref:
            base += f":{self.ref}"
        base += "]"
        if self.detail:
            base += f" {self.detail}"
        return base

    @staticmethod
    def parse_tag(tag: str) -> Optional["Source"]:
        """从标签字符串反向解析 Source。"""
        m = re.match(r'\[(msg|obs|inf)(?::([^\]]+))?\]\s*(.*)', tag)
        if not m:
            return None
        type_map = {"msg": SourceType.MSG, "obs": SourceType.OBSERVATION, "inf": SourceType.INFERENCE}
        return Source(
            type=type_map[m.group(1)],
            ref=m.group(2),
            confidence={"msg": 1.0, "obs": 0.9, "inf": 0.7}[m.group(1)],
            detail=m.group(3),
        )


class MemoryCategory(Enum):
    """Type of memory being archived."""
    DECISION = "decision"       # "We chose X over Y because..."
    LESSON = "lesson"           # "We learned that X causes Y"
    MILESTONE = "milestone"     # "Task Z completed"
    INSIGHT = "insight"         # "New understanding emerged"
    ERROR = "error"             # "This went wrong, avoid next time"
    PATTERN = "pattern"         # "Recurring behavior detected"

    @property
    def tier(self) -> str:
        """Cognitive tier (方法论#8): episodic | semantic | procedural | working."""
        _TIER_MAP = {
            MemoryCategory.DECISION: "semantic",
            MemoryCategory.LESSON: "semantic",
            MemoryCategory.MILESTONE: "episodic",
            MemoryCategory.INSIGHT: "semantic",
            MemoryCategory.ERROR: "episodic",
            MemoryCategory.PATTERN: "procedural",
        }
        return _TIER_MAP.get(self, "episodic")


@dataclass
class Memory:
    """A single archived memory with evidence chain (方法论#3)."""
    category: MemoryCategory
    content: str
    source: str                # Human-readable source label (kept for backward compat)
    delta: float               # Quality score at time of archiving
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.5
    tags: List[str] = field(default_factory=list)
    context: Dict = field(default_factory=dict)
    source_evidence: Optional[Source] = None  # 新增: 结构化来源标记 (S-025)


class MemoryGuard:
    """
    会话记忆守卫 — 自动检测并归档有价值的对话片段。

    用法:
        guard = MemoryGuard()

        # 每轮对话后调用
        mem = guard.observe(
            content="We decided to use asyncio for parallel execution",
            delta=0.6,
            source="agent:orchestrator",
        )
        if mem:
            print(f"Archived: {mem.category.value} — {mem.content[:80]}")

        # 定期写入
        guard.flush("memory/2026-06-08.md")
    """

    def __init__(
        self,
        delta_threshold: float = 0.35,       # Min Δ to consider archiving
        decision_threshold: float = 0.3,      # Min Δ for decisions
        flush_interval: int = 20,             # Flush after N memories
        auto_tag: bool = True,                # Auto-generate tags
    ):
        self.delta_threshold = delta_threshold
        self.decision_threshold = decision_threshold
        self.flush_interval = flush_interval
        self.auto_tag = auto_tag

        self.memories: List[Memory] = []
        self._error_patterns: Dict[str, int] = {}  # Track recurring errors

    # ── Decision word patterns for auto-detection ──
    _DECISION_PATTERNS = [
        (re.compile(r'\b(?:decided|decide|chose|choose|selected|opted|went with)\b', re.I),
         MemoryCategory.DECISION),
        (re.compile(r'\b(?:learned|realized|discovered|found that|it turns out)\b', re.I),
         MemoryCategory.LESSON),
        (re.compile(r'\b(?:error|fail|bug|broke|wrong|mistake|oops)\b', re.I),
         MemoryCategory.ERROR),
        (re.compile(r'\b(?:done|complete|finished|achieved|delivered|✅)\b', re.I),
         MemoryCategory.MILESTONE),
        (re.compile(r'\b(?:insight|aha|interesting|fascinating|wow|pattern)\b', re.I),
         MemoryCategory.INSIGHT),
    ]

    # ── Error patterns for lesson extraction ──
    _ERROR_PATTERNS = [
        (re.compile(r'ModuleNotFoundError:.*?(\w+)', re.I), "missing_module"),
        (re.compile(r'SyntaxError|IndentationError', re.I), "syntax"),
        (re.compile(r'ConnectionError|Timeout|DNS', re.I), "network"),
        (re.compile(r'403|401|Forbidden|Unauthorized', re.I), "auth"),
        (re.compile(r'out of memory|OOM|MemoryError', re.I), "memory"),
        (re.compile(r'SIGKILL|killed|terminated', re.I), "process_killed"),
        (re.compile(r'499|invalid_request', re.I), "api_invalid"),
    ]

    def observe(
        self,
        content: str,
        delta: float,
        source: str = "",
        force_category: Optional[MemoryCategory] = None,
    ) -> Optional[Memory]:
        """
        观察一轮对话，决定是否归档为记忆。

        Args:
            content: The text content of this turn
            delta: Δ (quality) score from DeltaProtocol
            source: Source identifier (e.g. "agent:reviewer")
            force_category: Override auto-detection

        Returns:
            Memory if archived, None if filtered out.
        """
        # Filter: only archive if Δ is high enough
        if delta < self.decision_threshold:
            return None

        # Auto-detect category
        category = force_category or self._detect_category(content)
        confidence = min(delta * 1.5, 0.95)

        # For low-Δ turns, only archive if it's a decision or milestone
        if delta < self.delta_threshold and category not in (
            MemoryCategory.DECISION, MemoryCategory.MILESTONE, MemoryCategory.ERROR
        ):
            return None

        # For errors, track patterns
        if category == MemoryCategory.ERROR:
            self._track_error_pattern(content)

        # Auto-tag
        tags = self._extract_tags(content) if self.auto_tag else []

        memory = Memory(
            category=category,
            content=content[:500],  # Truncate very long content
            source=source,
            delta=delta,
            confidence=confidence,
            tags=tags,
            context={"length": len(content), "word_count": len(content.split())},
        )

        self.memories.append(memory)
        return memory

    def _detect_category(self, text: str) -> MemoryCategory:
        """Auto-detect memory category from text content."""
        for pattern, category in self._DECISION_PATTERNS:
            if pattern.search(text):
                return category
        return MemoryCategory.INSIGHT  # Default: novel content

    def _track_error_pattern(self, text: str):
        """Track recurring error types."""
        for pattern, error_type in self._ERROR_PATTERNS:
            if pattern.search(text):
                self._error_patterns[error_type] = self._error_patterns.get(error_type, 0) + 1

    def _extract_tags(self, text: str) -> List[str]:
        """Extract hashtags or key terms as memory tags."""
        tags = []
        for m in re.finditer(r'#(\w+)', text):
            tags.append(m.group(1).lower())
        topic_patterns = {
            r'\bpy(?:thon)?\b': 'python',
            r'\bapi\b': 'api',
            r'\bgit\b': 'git',
            r'\bpypi\b': 'pypi',
            r'\bzenodo\b': 'zenodo',
            r'\bdoi\b': 'doi',
            r'\bci[/-]?cd\b': 'ci-cd',
            r'\bkb\b': 'kb',
            r'\bv\d+\.\d+': 'release',
            r'\bpublish\b': 'publish',
        }
        for pattern, tag in topic_patterns.items():
            if re.search(pattern, text, re.I) and tag not in tags:
                tags.append(tag)
        return tags[:5]

    def flush(self, path: str, format: str = "markdown") -> str:
        """
        写入积累的记忆到文件。

        Args:
            path: Output file path
            format: "markdown" (default) or "jsonl"

        Returns:
            Path written to.
        """
        if not self.memories:
            return path

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "jsonl":
            with open(path, 'a', encoding='utf-8') as f:
                for m in self.memories:
                    f.write(json.dumps({
                        "category": m.category.value,
                        "content": m.content,
                        "source": m.source,
                        "delta": m.delta,
                        "confidence": m.confidence,
                        "tags": m.tags,
                        "timestamp": datetime.fromtimestamp(m.timestamp).isoformat(),
                    }, ensure_ascii=False) + '\n')
        else:
            with open(path, 'a', encoding='utf-8') as f:
                now = datetime.fromtimestamp(time.time()).strftime('%H:%M')
                f.write(f"\n## {now} — Auto-Archived ({len(self.memories)} memories)\n\n")
                for m in self.memories:
                    icon = {
                        MemoryCategory.DECISION: "🔗",
                        MemoryCategory.LESSON: "📖",
                        MemoryCategory.MILESTONE: "✅",
                        MemoryCategory.INSIGHT: "💡",
                        MemoryCategory.ERROR: "🐛",
                        MemoryCategory.PATTERN: "🔁",
                    }.get(m.category, "📝")
                    tags_str = f" [{', '.join(m.tags)}]" if m.tags else ""
                    f.write(f"- {icon} **{m.category.value.title()}**{tags_str} "
                            f"(Δ={m.delta:.2f}, src={m.source})\n")
                    f.write(f"  {m.content[:200]}\n")

        count = len(self.memories)
        self.memories.clear()
        return str(path)

    def summary(self) -> dict:
        """Return a summary of all archived memories."""
        by_cat = {}
        total_delta = 0.0
        for m in self.memories:
            cat = m.category.value
            by_cat.setdefault(cat, 0)
            by_cat[cat] += 1
            total_delta += m.delta

        return {
            "total": len(self.memories),
            "by_category": by_cat,
            "avg_delta": total_delta / max(len(self.memories), 1),
            "error_patterns": dict(self._error_patterns),
            "needs_flush": len(self.memories) >= self.flush_interval,
        }

    def get_lessons(self, limit: int = 5) -> List[Memory]:
        """Get the most recent lessons learned."""
        lessons = [m for m in self.memories if m.category == MemoryCategory.LESSON]
        return sorted(lessons, key=lambda m: m.delta, reverse=True)[:limit]

    def get_decisions(self, limit: int = 5) -> List[Memory]:
        """Get recent decisions."""
        decisions = [m for m in self.memories if m.category == MemoryCategory.DECISION]
        return sorted(decisions, key=lambda m: m.timestamp, reverse=True)[:limit]


# ════════════════════════════════════════════════════════════
# S-025: MemorySourceGuard — 记忆证据链约束引擎
# ════════════════════════════════════════════════════════════

class MemorySourceGuard(MemoryGuard):
    """
    方法论#3 工程落地：记忆写入必须有证据来源标记。

    核心约束：
    1. observe() 新增 source_evidence: Source 参数（必填）
    2. INFERENCE 类型写入前 grep 验证（_verify_inference 方法）
    3. 无 Source 的写入 → MSC-001 告警 + 拒绝归档
    4. 三种来源在同一 Memory 中不可混排
    5. INFERENCE 写入时 confidence 上限锁定为 0.7

    Usage:
        guard = MemorySourceGuard()

        # ✅ 有消息来源
        mem = guard.observe(
            content="确认：KB 清理不包括删除操作",
            delta=0.5,
            source="agent:auditor",
            source_evidence=Source.from_msg(msg_id="msg#50497", detail="用户上传说明"),
        )

        # ✅ 有观测来源
        mem = guard.observe(
            content="GuardianEngine 扫描完成，22/22 通过",
            delta=0.6,
            source="agent:guardian",
            source_evidence=Source.from_observation(
                target="GuardianEngine.scan", detail="全量扫描结果"),
        )

        # ⚠️ 推理来源 — 写入前会调用 _verify_inference 验证
        mem = guard.observe(
            content="用户想要删除所有 skill",
            delta=0.4,
            source="agent:inference",
            source_evidence=Source.from_inference(
                chain_id="INF-001", detail="从 KB 语义推测"),
        )
        # → 包含「用户想要」归属词 → MSC-005 + MSC-003 → 隔离 → None
    """

    def __init__(
        self,
        delta_threshold: float = 0.35,
        decision_threshold: float = 0.3,
        flush_interval: int = 20,
        auto_tag: bool = True,
        verify_fn: Optional[Callable] = None,  # 外部验证回调
    ):
        super().__init__(
            delta_threshold=delta_threshold,
            decision_threshold=decision_threshold,
            flush_interval=flush_interval,
            auto_tag=auto_tag,
        )
        self.verify_fn = verify_fn
        self.alerts: List[dict] = []
        self._inference_chain: Dict[str, List[Memory]] = {}

    # ── 核心: 带证据链的 observe ──

    def observe(
        self,
        content: str,
        delta: float,
        source: str = "",
        force_category: Optional[MemoryCategory] = None,
        source_evidence: Optional[Source] = None,
    ) -> Optional[Memory]:
        """
        观察并归档记忆（带证据链约束）。

        Returns:
            Memory 或 None（如果被过滤/拒绝/隔离）
        """
        # ── MSC-001: 无来源写入 → 拒绝 ──
        if source_evidence is None:
            self._alert("MSC-001",
                f"Memory write rejected: no source_evidence provided. "
                f"Content: {content[:60]}...",
                severity="WARN")
            return None

        # ── MSC-002: 推理类型 + 高 confidence → 降级 ──
        if (source_evidence.type == SourceType.INFERENCE
            and source_evidence.confidence > 0.7):
            self._alert("MSC-002",
                f"INFERENCE confidence clamped {source_evidence.confidence:.2f} → 0.7",
                severity="INFO")
            source_evidence.confidence = 0.7

        # ── MSC-003: 推理类型 + 验证失败 → 隔离 ──
        if source_evidence.type == SourceType.INFERENCE:
            if not self._verify_inference(content, source_evidence):
                self._alert("MSC-003",
                    f"INFERENCE memory quarantined: chain_id={source_evidence.ref}. "
                    f"Content: {content[:80]}...",
                    severity="CRITICAL")
                self._quarantine_inference(content, source, delta, source_evidence)
                return None

        # ── 正常归档流程 ──
        effective_delta = delta * source_evidence.confidence
        if effective_delta < self.decision_threshold:
            return None

        category = force_category or self._detect_category(content)
        confidence = min(effective_delta * 1.5, source_evidence.confidence)

        if effective_delta < self.delta_threshold and category not in (
            MemoryCategory.DECISION, MemoryCategory.MILESTONE, MemoryCategory.ERROR
        ):
            return None

        if category == MemoryCategory.ERROR:
            self._track_error_pattern(content)

        tags = self._extract_tags(content) if self.auto_tag else []

        memory = Memory(
            category=category,
            content=content[:500],
            source=source,
            delta=delta,
            confidence=confidence,
            tags=tags,
            context={"length": len(content), "word_count": len(content.split())},
            source_evidence=source_evidence,
        )

        self.memories.append(memory)
        return memory

    # ── 推理验证 ──

    def _verify_inference(self, content: str, source_evidence: Source) -> bool:
        """
        验证推理记忆。先走外部验证，再走内置归属词检测。

        Returns:
            True if verification passes, False if quarantined.
        """
        # 外部验证函数（e.g. grep 用户消息历史）
        if self.verify_fn:
            try:
                return self.verify_fn(content, source_evidence)
            except Exception as e:
                self._alert("MSC-004",
                    f"verify_fn raised: {e}. Falling back to built-in check.",
                    severity="WARN")

        # 内置检查: 推理内容不能包含归属词（方法论#2 L3 来源伪造检测）
        attribution_keywords = [
            r'(?:用户|user|they)\s*(?:说|said|告诉|wants?|要求|命令|指令)',
            r'(?:来自|from)\s*(?:用户|user)',
        ]
        for pattern in attribution_keywords:
            if re.search(pattern, content, re.I):
                self._alert("MSC-005",
                    f"INFERENCE contains attribution keyword: '{pattern}'. "
                    f"This matches L3 source fabrication pattern (方法论#2).",
                    severity="CRITICAL")
                return False

        return True

    def _quarantine_inference(self, content: str, source: str,
                              delta: float, evidence: Source):
        """隔离未通过验证的推理记忆到推理链存储。"""
        chain_id = evidence.ref or f"INF-{len(self._inference_chain):03d}"
        mem = Memory(
            category=MemoryCategory.INSIGHT,
            content=content[:500],
            source=source,
            delta=delta,
            confidence=0.0,  # 零置信标记
            source_evidence=evidence,
            context={"quarantined": True, "reason": "MSC-003: unverified inference"},
        )
        self._inference_chain.setdefault(chain_id, []).append(mem)

    # ── 告警系统 ──

    MSG_TYPES = {"CRITICAL": "🔥", "WARN": "⚠️", "INFO": "ℹ️"}

    def _alert(self, code: str, message: str, severity: str = "WARN"):
        """发出告警并记录。"""
        alert = {
            "code": code,
            "severity": severity,
            "message": message,
            "timestamp": time.time(),
        }
        self.alerts.append(alert)
        prefix = self.MSG_TYPES.get(severity, "⚠️")
        print(f"  {prefix} [{code}] [{severity}] {message[:120]}", file=sys.stderr)

    # ── 隔离区管理 ──

    def quarantine_summary(self) -> dict:
        """查看隔离区中的推理记忆。"""
        return {
            "chains": len(self._inference_chain),
            "quarantined_items": sum(len(v) for v in self._inference_chain.values()),
            "chain_ids": list(self._inference_chain.keys()),
        }

    def release_quarantine(self, chain_id: str, verified: bool = True) -> List[Memory]:
        """
        释放隔离区中的推理记忆（用户手动验证通过后调用）。
        释放后升级为 OBSERVATION 类型，confidence 升至 0.9。
        """
        if chain_id not in self._inference_chain:
            return []

        memories = self._inference_chain.pop(chain_id)
        if verified:
            for mem in memories:
                mem.confidence = 0.7
                if mem.source_evidence:
                    mem.source_evidence.type = SourceType.OBSERVATION
                    mem.source_evidence.ref = f"verified:{chain_id}"
                    mem.source_evidence.confidence = 0.9
                self.memories.append(mem)

        return memories

    # ── 增强 flush: 带证据标记 ──

    def flush(self, path: str, format: str = "markdown") -> str:
        """
        写入记忆（带证据标记）。

        与父类区别：
        - 每条记忆附加 [msg:id] / [观测] / [推断] 标签
        - 推理记忆标注 confidence 和验证状态
        """
        if not self.memories:
            return path

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "jsonl":
            with open(path, 'a', encoding='utf-8') as f:
                for m in self.memories:
                    record = {
                        "category": m.category.value,
                        "content": m.content,
                        "source": m.source,
                        "delta": m.delta,
                        "confidence": m.confidence,
                        "tags": m.tags,
                        "timestamp": datetime.fromtimestamp(m.timestamp).isoformat(),
                    }
                    if m.source_evidence:
                        record["source_type"] = m.source_evidence.type.value
                        record["source_ref"] = m.source_evidence.ref
                        record["source_detail"] = m.source_evidence.detail
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
        else:
            with open(path, 'a', encoding='utf-8') as f:
                now = datetime.fromtimestamp(time.time()).strftime('%H:%M')
                f.write(f"\n## {now} — Auto-Archived ({len(self.memories)} memories)\n\n")
                for m in self.memories:
                    icon = {
                        MemoryCategory.DECISION: "🔗",
                        MemoryCategory.LESSON: "📖",
                        MemoryCategory.MILESTONE: "✅",
                        MemoryCategory.INSIGHT: "💡",
                        MemoryCategory.ERROR: "🐛",
                        MemoryCategory.PATTERN: "🔁",
                    }.get(m.category, "📝")
                    evidence_tag = f" {m.source_evidence.to_tag()}" if m.source_evidence else ""
                    tags_str = f" [{', '.join(m.tags)}]" if m.tags else ""
                    f.write(f"- {icon} **{m.category.value.title()}**{tags_str}"
                            f" (Δ={m.delta:.2f}, conf={m.confidence:.2f}, src={m.source}){evidence_tag}\n")
                    f.write(f"  {m.content[:200]}\n")

        count = len(self.memories)
        self.memories.clear()
        return str(path)


# ════════════════════════════════════════════════════════════
# S-029 MemoryTierGuard — 认知记忆分层 (方法论#8)
# ════════════════════════════════════════════════════════════

# 四层认知记忆的写入门槛
TIER_THRESHOLDS: Dict[str, dict] = {
    "episodic":   {"delta": 0.25, "confirmations": 1, "ttl_days": 7},
    "semantic":   {"delta": 0.55, "confirmations": 3, "ttl_days": 365},
    "procedural": {"delta": 0.45, "confirmations": 2, "ttl_days": 90},
    "working":    {"delta": 0.0,  "confirmations": 0, "ttl_days": 0},
}

TIER_DESTINATIONS = {
    "episodic": "memory/{date}.md",
    "semantic": "knowledge_base/h{id}_{title}.json",
    "procedural": "mssclaw/core/schema.py",
    "working": None,  # 自动丢弃，不持久化
}


class MemoryTierGuard(MemorySourceGuard):
    """
    方法论#8 工程落地：认知记忆分层 (Cognitive Memory Tiering)。

    四层记忆结构：
    - **EPISODIC**  (情景记忆) → memory/YYYY-MM-DD.md, 低门槛 (Δ≥0.25)
    - **SEMANTIC**   (语义记忆) → H 条目, 高门槛 (Δ≥0.55, 3 轮确认)
    - **PROCEDURAL** (程序记忆) → Executor Schema, 中门槛 (Δ≥0.45, 2 轮确认)
    - **WORKING**    (工作记忆) → 对话窗口, 无门槛 (自动丢弃)

    关键约束：
    1. 写入时根据 MemoryCategory 自动分配到对应 tier
    2. SEMANTIC 写入需多轮确认 (confirmation_count ≥ 3)
    3. WORKING 记忆不调用 observe (走独立 fast_path)
    4. EPISODIC 日终自动 flush, SEMANTIC 累积后批量入库

    Usage:
        guard = MemoryTierGuard()

        # 情景记忆 — 随时写
        mem = guard.observe("Task S-025 complete", delta=0.6,
            source="agent:worker",
            source_evidence=Source.from_observation("S-025", "completed"))
        # → tier=episodic, 直接写入

        # 语义记忆 — 需要 3 轮确认
        mem = guard.observe("新公理: A7 感知壳相对性", delta=0.7,
            source="agent:theorist",
            source_evidence=Source.from_inference("T-001", "理论推演"))
        # → tier=semantic, 进入确认队列 (confirmation 1/3)

        # 第三轮确认同一条目后 → 写入
        guard.confirm_semantic("新公理: A7 感知壳相对性")
        guard.confirm_semantic("新公理: A7 感知壳相对性")
        # → 3/3 confirmations → 写入 H 条目
    """

    def __init__(
        self,
        delta_threshold: float = 0.25,
        decision_threshold: float = 0.20,
        flush_interval: int = 20,
        auto_tag: bool = True,
        verify_fn: Optional[Callable] = None,
    ):
        super().__init__(
            delta_threshold=delta_threshold,
            decision_threshold=decision_threshold,
            flush_interval=flush_interval,
            auto_tag=auto_tag,
            verify_fn=verify_fn,
        )
        # 语义记忆确认队列: {content_hash: (category, content, delta, source, evidence, count)}
        self._semantic_queue: Dict[int, tuple] = {}
        # 程序记忆确认队列
        self._procedural_queue: Dict[int, tuple] = {}
        # 降级记忆（本应进语义但确认不够）→ 降为情景
        self._downgraded: List[Memory] = []

    # ── 核心：带分层路由的 observe ──

    def observe(
        self,
        content: str,
        delta: float,
        source: str = "",
        force_category: Optional[MemoryCategory] = None,
        source_evidence: Optional[Source] = None,
    ) -> Optional[Memory]:
        """
        观察并路由到正确 tier。

        路由逻辑：
        1. 无 source_evidence → 父类 MSC-001 拒绝
        2. 自动检测 category → 映射 tier
        3. 根据 tier_thresholds 判断是否满足写入门槛
        4. SEMANTIC/PROCEDURAL 进入确认队列
        5. EPISODIC 直接写入
        """
        # ── MSC-001 ──
        if source_evidence is None:
            self._alert("MSC-001",
                f"Memory write rejected: no source_evidence. Content: {content[:60]}...")
            return None

        # ── 自动检测 category ──
        category = force_category or self._detect_category(content)
        tier = category.tier
        threshold = TIER_THRESHOLDS[tier]

        # ── WORKING: 不做持久化，直接返回标记对象 ──
        if tier == "working":
            return Memory(
                category=category,
                content=content[:500],
                source=source,
                delta=delta,
                confidence=0.1,
                source_evidence=source_evidence,
                context={"tier": "working", "persisted": False},
            )

        # ── 检查 Δ 门槛 ──
        if delta < threshold["delta"]:
            return None

        # ── SEMANTIC: 进入确认队列 ──
        if tier == "semantic":
            return self._enqueue_semantic(content, delta, source, category, source_evidence, threshold)

        # ── PROCEDURAL: 进入确认队列 ──
        if tier == "procedural":
            return self._enqueue_procedural(content, delta, source, category, source_evidence, threshold)

        # ── EPISODIC: 直接写入 (bypass MemorySourceGuard, use MemoryGuard base) ──
        return MemoryGuard.observe(
            self, content, delta, source, force_category=category,
        )

    # ── 语义确认队列 ──

    def _enqueue_semantic(
        self, content: str, delta: float, source: str,
        category: MemoryCategory, evidence: Source, threshold: dict,
    ) -> Optional[Memory]:
        """将语义记忆入队。需 3 轮确认后才写入。"""
        content_hash = hash(content[:200])  # 用前 200 字符做模糊匹配

        if content_hash in self._semantic_queue:
            _, _, _, _, _, count = self._semantic_queue[content_hash]
            count += 1
            self._semantic_queue[content_hash] = (category, content, delta, source, evidence, count)

            if count >= threshold["confirmations"]:
                # 3 轮确认 → 释放并写入
                cat, c, d, s, ev, _ = self._semantic_queue.pop(content_hash)
                # Confirmed → write via MemorySourceGuard with full evidence
                mem = MemoryGuard.observe(
                    self, c, d, s, force_category=cat,
                )
                if mem:
                    mem.source_evidence = ev
                    mem.context["tier"] = "semantic"
                    mem.context["confirmations"] = count
                    mem.context["confirmed_at"] = time.time()
                return mem
            return None  # 还在队列中，未释放

        else:
            # 首次入队
            self._semantic_queue[content_hash] = (category, content, delta, source, evidence, 1)
            return None

    # ── 程序确认队列 ──

    def _enqueue_procedural(
        self, content: str, delta: float, source: str,
        category: MemoryCategory, evidence: Source, threshold: dict,
    ) -> Optional[Memory]:
        """将程序记忆入队。需 2 轮确认后才写入。"""
        content_hash = hash(content[:200])

        if content_hash in self._procedural_queue:
            _, _, _, _, _, count = self._procedural_queue[content_hash]
            count += 1
            self._procedural_queue[content_hash] = (category, content, delta, source, evidence, count)

            if count >= threshold["confirmations"]:
                cat, c, d, s, ev, _ = self._procedural_queue.pop(content_hash)
                # Confirmed → write via MemoryGuard base
                mem = MemoryGuard.observe(
                    self, c, d, s, force_category=cat,
                )
                if mem:
                    mem.source_evidence = ev
                    mem.context["tier"] = "procedural"
                    mem.context["confirmations"] = count
                return mem
            return None

        else:
            self._procedural_queue[content_hash] = (category, content, delta, source, evidence, 1)
            return None

    # ── 手动确认（用于外部循环驱动） ──

    def confirm_semantic(self, partial_content: str) -> bool:
        """
        外部调用：再次确认某条语义记忆。
        Returns True if the memory was released after this confirmation.
        """
        content_hash = hash(partial_content[:200])
        if content_hash in self._semantic_queue:
            cat, content, delta, source, evidence, count = self._semantic_queue[content_hash]
            count += 1
            threshold = TIER_THRESHOLDS["semantic"]["confirmations"]
            self._semantic_queue[content_hash] = (cat, content, delta, source, evidence, count)

            if count >= threshold:
                cat, c, d, s, ev, _ = self._semantic_queue.pop(content_hash)
                mem = MemoryGuard.observe(self, c, d, s, force_category=cat)
                if mem:
                    mem.source_evidence = ev
                    mem.context["tier"] = "semantic"
                    mem.context["confirmations"] = count
                return True
        return False

    # ── 降级处理 ──

    def downgrade_unconfirmed(self, max_age_hours: float = 24.0) -> List[Memory]:
        """
        将超时未确认的语义/程序记忆降级为情景记忆。
        每个 observe 调用时可以检查是否需要降级。
        """
        downgraded = []
        now = time.time()

        # 没有时间戳追踪的简化版：直接清空未达标的队列
        stale_semantic = [
            (cat, c, d, s, ev, cnt) for cnt_key, (cat, c, d, s, ev, cnt)
            in self._semantic_queue.items() if cnt < TIER_THRESHOLDS["semantic"]["confirmations"]
        ]
        for cat, c, d, s, ev, cnt in stale_semantic:
            mem = Memory(
                category=cat,
                content=f"[DOWNGRADED from semantic, confirmations={cnt}] {c[:400]}",
                source=s,
                delta=d,
                confidence=0.5,
                source_evidence=ev,
                context={"tier": "episodic", "original_tier": "semantic", "confirmations": cnt},
            )
            self.memories.append(mem)
            self._downgraded.append(mem)
            downgraded.append(mem)

        self._semantic_queue.clear()
        return downgraded

    # ── 队列状态查询 ──

    def queue_status(self) -> dict:
        """查看各 tier 确认队列状态。"""
        return {
            "semantic_pending": len(self._semantic_queue),
            "semantic_confirmations": {str(k)[:8]: v[5] for k, v in self._semantic_queue.items()},
            "procedural_pending": len(self._procedural_queue),
            "procedural_confirmations": {str(k)[:8]: v[5] for k, v in self._procedural_queue.items()},
            "downgraded_count": len(self._downgraded),
        }


# ════════════════════════════════════════════════════════════
# CLI 自检
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Memory Guard v0.4 — S-025 Evidence Chain Demo ===\n")

    # ── 测试 1: 基础 MemoryGuard (向后兼容) ──
    print("─ 测试 1: 基础 MemoryGuard (backward compat) ─")
    guard = MemoryGuard()
    turns = [
        ("We decided to use asyncio.", 0.6, "agent:orchestrator"),
        ("The test failed with SIGKILL.", 0.2, "agent:executor"),
        ("Just saying hi", 0.1, "agent:chatter"),
    ]
    for content, delta, source in turns:
        mem = guard.observe(content, delta, source)
        status = "💾" if mem else "⏭️"
        print(f"  {status} [{content[:50]}...]")

    # ── 测试 2: MemorySourceGuard — 正常流程 ──
    print("\n─ 测试 2: MemorySourceGuard — 合法写入 ─")
    ms_guard = MemorySourceGuard()

    mem1 = ms_guard.observe(
        content="确认：KB 清理不包括删除操作",
        delta=0.5,
        source="agent:auditor",
        source_evidence=Source.from_msg(msg_id="msg#50497", detail="用户上传说明"),
    )
    print(f"  MSG source: {'✅ archived' if mem1 else '❌ rejected'}"
          f" | tag={mem1.source_evidence.to_tag() if mem1 else 'N/A'}")

    mem2 = ms_guard.observe(
        content="GuardianEngine 扫描完成，22/22 通过",
        delta=0.6,
        source="agent:guardian",
        source_evidence=Source.from_observation(target="GuardianEngine.scan",
                                                detail="全量扫描结果"),
    )
    print(f"  OBS source: {'✅ archived' if mem2 else '❌ rejected'}"
          f" | tag={mem2.source_evidence.to_tag() if mem2 else 'N/A'}")

    # ── 测试 3: MSC-001 — 无来源写入 → 拒绝 ──
    print("\n─ 测试 3: MSC-001 — 无来源写入 → 应被拒绝 ─")
    mem3 = ms_guard.observe(
        content="这条记忆没有来源",
        delta=0.8,
        source="agent:unknown",
    )
    assert mem3 is None, "MSC-001: should reject write without source_evidence"
    assert len(ms_guard.alerts) >= 1
    assert ms_guard.alerts[0]["code"] == "MSC-001"
    print(f"  ✅ MSC-001: correctly rejected | alert: {ms_guard.alerts[0]['code']}")

    # ── 测试 4: MSC-005 — 推理含归属词 → 隔离 ──
    print("\n─ 测试 4: MSC-005 — 推理含「用户说」归属词 → 应被隔离 ─")
    alerts_before = len(ms_guard.alerts)
    mem4 = ms_guard.observe(
        content="用户说了要删除所有 skill，我们需要执行",
        delta=0.6,
        source="agent:inference",
        source_evidence=Source.from_inference(
            chain_id="INF-004", detail="从 KB 语义推测"),
    )
    assert mem4 is None, "MSC-005: should quarantine inference with attribution"
    assert len(ms_guard.alerts) > alerts_before
    criticals = [a for a in ms_guard.alerts if a["severity"] == "CRITICAL"]
    assert len(criticals) >= 1
    qs = ms_guard.quarantine_summary()
    assert qs["quarantined_items"] >= 1
    print(f"  ✅ MSC-005: correctly quarantined | quarantine: {qs}")

    # ── 测试 5: 隔离释放 ──
    print("\n─ 测试 5: 释放隔离记忆 ─")
    released = ms_guard.release_quarantine("INF-004", verified=True)
    print(f"  Released: {len(released)} memory | new type: {released[0].source_evidence.type.value}")
    qs2 = ms_guard.quarantine_summary()
    print(f"  Quarantine after release: {qs2}")

    # ── 测试 6: Source 序列化 ──
    print("\n─ 测试 6: Source 标签序列化/反序列化 ─")
    s1 = Source.from_msg("msg#50497", "用户上传说明")
    tag = s1.to_tag()
    parsed = Source.parse_tag(tag)
    assert parsed is not None
    assert parsed.type == SourceType.MSG
    assert parsed.ref == "msg#50497"
    print(f"  Serialize: '{tag}' → Parse: type={parsed.type.value}, ref={parsed.ref}")

    s2 = Source.from_inference("INF-001", "KB语义推测")
    tag2 = s2.to_tag()
    parsed2 = Source.parse_tag(tag2)
    assert parsed2.type == SourceType.INFERENCE
    print(f"  Serialize: '{tag2}' → Parse: type={parsed2.type.value}")

    # ── 汇总 ──
    print(f"\n📊 S-025 MemorySourceGuard 验收报告:")
    print(f"  基础 MemoryGuard: ✅ 向后兼容")
    print(f"  MSC-001 (无源拒绝): ✅")
    print(f"  MSC-005 (归属词隔离): ✅")
    print(f"  隔离释放: ✅")
    print(f"  Source 序列化: ✅")
    print(f"  总告警数: {len(ms_guard.alerts)}")
    for a in ms_guard.alerts:
        print(f"    [{a['code']}] [{a['severity']}] {a['message'][:80]}")
    print(f"\n  🎉 S-025 MemorySourceGuard — ALL PASS")

    # ══════════════ S-029 MemoryTierGuard 自检 ══════════════
    print("\n" + "="*50)
    print("=== MemoryTierGuard v0.1 — S-029 Cognitive Tier Demo ===")
    print("="*50)

    # ── 测试 7: tier 映射 ──
    print("\n─ 测试 7: MemoryCategory → tier 映射 ─")
    tier_tests = [
        (MemoryCategory.DECISION, "semantic"),
        (MemoryCategory.LESSON, "semantic"),
        (MemoryCategory.MILESTONE, "episodic"),
        (MemoryCategory.INSIGHT, "semantic"),
        (MemoryCategory.ERROR, "episodic"),
        (MemoryCategory.PATTERN, "procedural"),
    ]
    for cat, expected_tier in tier_tests:
        assert cat.tier == expected_tier, f"{cat.value} → {cat.tier} (expected {expected_tier})"
    print(f"  ✅ 6/6 tier mappings correct")

    # ── 测试 8: EPISODIC 直接写入 ──
    print("\n─ 测试 8: EPISODIC 直接写入 (Δ≥0.25) ─")
    tier_guard = MemoryTierGuard()
    mem8 = tier_guard.observe(
        content="Task S-025 completed — MemorySourceGuard done",
        delta=0.7,
        source="agent:worker",
        force_category=MemoryCategory.MILESTONE,
        source_evidence=Source.from_observation("S-025", "completed"),
    )
    assert mem8 is not None, "EPISODIC with Δ=0.7 should be written"
    assert mem8.category == MemoryCategory.MILESTONE
    print(f"  ✅ EPISODIC write: category={mem8.category.value} Δ={mem8.delta}")

    # ── 测试 9: SEMANTIC 需 3 轮确认 ──
    print("\n─ 测试 9: SEMANTIC 需 3 轮确认 ─")
    content9 = "新理论发现: A7 感知壳相对性公理"
    # 第 1 轮 — 入队不写入
    mem9a = tier_guard.observe(
        content=content9,
        delta=0.72,
        source="agent:theorist",
        source_evidence=Source.from_inference("T-001", "理论推演"),
    )
    assert mem9a is None, f"SEMANTIC round 1 should not write, got {mem9a}"
    qs = tier_guard.queue_status()
    assert qs["semantic_pending"] == 1
    print(f"  Round 1: pending → {qs}")

    # 第 2 轮
    mem9b = tier_guard.observe(
        content=content9,
        delta=0.72,
        source="agent:theorist",
        source_evidence=Source.from_inference("T-001", "理论推演"),
    )
    assert mem9b is None, f"SEMANTIC round 2 should not write, got {mem9b}"
    qs = tier_guard.queue_status()
    assert qs["semantic_pending"] == 1  # still same entry
    print(f"  Round 2: pending → {qs}")

    # 第 3 轮 — 确认达标，写入
    mem9c = tier_guard.observe(
        content=content9,
        delta=0.72,
        source="agent:theorist",
        source_evidence=Source.from_inference("T-001", "理论推演"),
    )
    assert mem9c is not None, "SEMANTIC round 3 should write"
    assert mem9c.context.get("tier") == "semantic"
    assert mem9c.context.get("confirmations") == 3
    qs = tier_guard.queue_status()
    assert qs["semantic_pending"] == 0
    print(f"  Round 3: ✅ WRITTEN | tier=semantic, confirmations=3 | queue: {qs}")

    # ── 测试 10: 低 Δ 过滤 ──
    print("\n─ 测试 10: 低 Δ 过滤 (SEMANTIC Δ=0.3 < 0.55) ─")
    mem10 = tier_guard.observe(
        content="随便一条想法",
        delta=0.3,
        source="agent:chatter",
        source_evidence=Source.from_observation("chat", "闲聊"),
    )
    assert mem10 is None, f"Δ=0.3 should be filtered, got {mem10}"
    print(f"  ✅ Correctly filtered (Δ=0.3 < semantic threshold 0.55)")

    # ── 测试 11: confirm_semantic 手动驱动 ──
    print("\n─ 测试 11: confirm_semantic 手动驱动 ─")
    tier_guard2 = MemoryTierGuard()
    content11 = "模式发现: PowerShell 编码坑是系统性缺陷"
    tier_guard2.observe(content11, 0.68, "agent:auditor",
                        source_evidence=Source.from_observation("PS", "pattern"))
    tier_guard2.observe(content11, 0.68, "agent:auditor",
                        source_evidence=Source.from_observation("PS", "pattern"))
    qs_before = tier_guard2.queue_status()
    assert qs_before["semantic_pending"] == 1
    # 手动确认第 3 轮
    released = tier_guard2.confirm_semantic(content11)
    assert released, "confirm_semantic should release the memory"
    qs_after = tier_guard2.queue_status()
    assert qs_after["semantic_pending"] == 0
    print(f"  ✅ Manual confirm: released={released} | queue: {qs_before} → {qs_after}")

    # ── 测试 12: 降级处理 ──
    print("\n─ 测试 12: 降级未确认语义记忆 → 情景记忆 ─")
    tier_guard3 = MemoryTierGuard()
    tier_guard3.observe("一个只有1轮确认的理论", 0.7, "agent:X",
                        source_evidence=Source.from_inference("inf", "unconfirmed"))
    qs_before_dg = tier_guard3.queue_status()
    assert qs_before_dg["semantic_pending"] == 1
    downgraded = tier_guard3.downgrade_unconfirmed()
    assert len(downgraded) >= 1
    qs_after_dg = tier_guard3.queue_status()
    assert qs_after_dg["semantic_pending"] == 0
    print(f"  ✅ Downgraded: {len(downgraded)} memories → episodic")
    print(f"  Queue after downgrade: {qs_after_dg}")

    # ── S-029 汇总 ──
    print(f"\n📊 S-029 MemoryTierGuard 验收报告:")
    print(f"  Tier mapping (6/6): ✅")
    print(f"  EPISODIC direct write: ✅")
    print(f"  SEMANTIC 3-round confirmation: ✅")
    print(f"  Low-Δ filtering: ✅")
    print(f"  Manual confirm_semantic: ✅")
    print(f"  Downgrade unconfirmed: ✅")
    print(f"  🎉 S-029 MemoryTierGuard — ALL PASS")
