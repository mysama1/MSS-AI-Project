"""
MSS-Agent v0.3 — Memory Guard (会话记忆自动归档)

Auto-archives conversation turns to long-term memory based on quality signals:
- High Delta (Δ > 0.5): novel insight → archive
- Decision made (words like "decide"/"choose"/"ok let's") → archive
- Error + fix (pattern detection) → archive as lesson
- Task completed → archive as milestone

Integrates with DeltaQuickAudit and HeatTaxAccountant for signal extraction.

Part of the P0 tool suite (memory_guard / auto_archive / session_recall / budget_gate).
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
import re
import time


class MemoryCategory(Enum):
    """Type of memory being archived."""
    DECISION = "decision"       # "We chose X over Y because..."
    LESSON = "lesson"           # "We learned that X causes Y"
    MILESTONE = "milestone"     # "Task Z completed"
    INSIGHT = "insight"         # "New understanding emerged"
    ERROR = "error"             # "This went wrong, avoid next time"
    PATTERN = "pattern"         # "Recurring behavior detected"


@dataclass
class Memory:
    """A single archived memory."""
    category: MemoryCategory
    content: str
    source: str                # Which agent/turn produced this
    delta: float               # Quality score at time of archiving
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.5
    tags: List[str] = field(default_factory=list)
    context: Dict = field(default_factory=dict)


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
        # Extract explicit #tags
        for m in re.finditer(r'#(\w+)', text):
            tags.append(m.group(1).lower())
        # Extract common topics
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
        return tags[:5]  # Max 5 tags

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


# ── CLI 自检 ──

if __name__ == "__main__":
    print("=== Memory Guard Demo ===\n")

    guard = MemoryGuard()

    # Simulate various conversation turns
    turns = [
        ("We decided to use asyncio for parallel execution instead of threading.", 0.6, "agent:orchestrator"),
        ("The test failed with SIGKILL — process was killed by Windows Job Object.", 0.2, "agent:executor"),
        ("Interesting pattern: PowerShell f-string escaping breaks every time with dict access.", 0.5, "agent:observer"),
        ("✅ v0.3.4 released to PyPI with ToolBudgetGate.", 0.7, "agent:deployer"),
        ("Learned that Zenodo DOI 10.5281/zenodo.20587900 is the correct one for the project.", 0.4, "agent:researcher"),
        ("Just saying hi", 0.1, "agent:chatter"),
        ("ModuleNotFoundError: No module named 'mssclaw' — forgot to pip install.", 0.3, "agent:tester"),
    ]

    for content, delta, source in turns:
        mem = guard.observe(content, delta, source)
        if mem:
            icon = "💾" if mem.confidence > 0.5 else "📝"
            print(f"  {icon} [{mem.category.value}] Δ={delta:.1f}: {content[:70]}...")
        else:
            print(f"  ⏭️  [filtered] Δ={delta:.1f}: {content[:50]}...")

    print(f"\n📊 Guard Summary:")
    s = guard.summary()
    print(f"  Total: {s['total']} | Avg Δ={s['avg_delta']:.2f} | Flush needed: {s['needs_flush']}")
    print(f"  Categories: {s['by_category']}")
    print(f"  Error patterns: {s['error_patterns']}")

    # Flush to temp file
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), "memory_guard_test.md")
    guard.flush(tmp)
    print(f"\n  Flushed to: {tmp}")
