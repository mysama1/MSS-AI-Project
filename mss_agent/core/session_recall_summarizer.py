"""
MSS-Agent v0.3 — Session Recall Summarizer (会话摘要生成)

Generates compact summaries from session transcripts:
- Extracts key decisions, lessons, milestones, and errors
- Multi-pass analysis: topic segmentation → entity extraction → summarization
- Outputs structured markdown suitable for MEMORY.md or daily files
- Integrates with MemoryGuard for filtered archiving

Part of the P0 tool suite (memory_guard / auto_archive / session_recall / budget_gate).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import Counter
import re
import time


@dataclass
class SessionSegment:
    """A coherent segment of the session."""
    topic: str
    start_turn: int
    end_turn: int
    summary: str
    key_entities: List[str]
    decision_count: int
    lesson_count: int


@dataclass
class SessionSummary:
    """Complete session summary."""
    session_id: str
    timestamp: float = field(default_factory=time.time)
    total_turns: int = 0
    decisions: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    milestones: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    segments: List[SessionSegment] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)


class SessionRecallSummarizer:
    """
    会话摘要生成器 — 从transcript中提取结构化总结。

    用法:
        summarizer = SessionRecallSummarizer()

        # 逐轮feed
        summarizer.feed("agent:decided to use asyncio", turn=1, source="orchestrator")

        # 生成摘要
        summary = summarizer.summarize("memory/2026-06-08.md")

        # 或用MemoryGuard过滤低质量内容
        from mss_agent import MemoryGuard
        guard = MemoryGuard()
        summary = summarizer.summarize_with_guard(guard, "memory/2026-06-08.md")
    """

    def __init__(self, session_id: str = "", max_segment_size: int = 20):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d-%H%M")
        self.max_segment_size = max_segment_size

        self._turns: List[dict] = []
        self._topic_changes: List[int] = []
        self._decisions: List[str] = []
        self._lessons: List[str] = []
        self._milestones: List[str] = []
        self._errors: List[str] = []
        self._key_files: set = set()
        self._entity_counts: Counter = Counter()

    def feed(
        self,
        content: str,
        turn: int = 0,
        source: str = "",
        delta: float = 0.0,
    ):
        """
        Feed a conversation turn into the summarizer.

        Args:
            content: The text content of this turn
            turn: Turn number
            source: Source identifier
            delta: Quality score
        """
        turn_data = {
            "content": content,
            "turn": turn or len(self._turns) + 1,
            "source": source,
            "delta": delta,
        }
        self._turns.append(turn_data)

        # Extract signals
        self._extract_decisions(content, turn_data["turn"])
        self._extract_lessons(content, turn_data["turn"])
        self._extract_milestones(content, turn_data["turn"])
        self._extract_errors(content, turn_data["turn"])
        self._extract_entities(content)
        self._extract_files(content)

        # Detect topic changes
        if self._turns and len(self._turns) > 1:
            prev = self._turns[-2]["content"]
            similarity = self._text_similarity(prev, content)
            if similarity < 0.3:  # Low similarity = topic change
                self._topic_changes.append(turn_data["turn"])

    def _extract_decisions(self, text: str, turn: int):
        """Extract decision statements."""
        patterns = [
            re.compile(r'(?:decided|decide|chose|choose|opted|went with)\s+(?:to\s+)?(.{10,120}?)(?:\.|\n|$)', re.I),
            re.compile(r'(?:ok|okay)\s+(?:let.?s|we.?ll)\s+(.{10,120}?)(?:\.|\n|$)', re.I),
            re.compile(r'(?:will|going to|gonna)\s+(.{10,120}?)(?:\.|\n|$)', re.I),
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                decision = m.group(1).strip()
                if len(decision) > 10:
                    self._decisions.append(f"[T{turn}] {decision}")

    def _extract_lessons(self, text: str, turn: int):
        """Extract learned lessons."""
        patterns = [
            re.compile(r'(?:learned|realized|discovered|found that|turns out)\s+(?:that\s+)?(.{10,120}?)(?:\.|\n|$)', re.I),
            re.compile(r'(?:the issue was|the problem was|root cause)\s*(?:is\s+)?(.{10,120}?)(?:\.|\n|$)', re.I),
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                lesson = m.group(1).strip()
                if len(lesson) > 10:
                    self._lessons.append(f"[T{turn}] {lesson}")

    def _extract_milestones(self, text: str, turn: int):
        """Extract milestone/completion statements."""
        patterns = [
            re.compile(r'(?:✅|done|complete|finished|achieved|delivered|released|published|pushed)\s+(?:the\s+)?(.{10,120}?)(?:\.|\n|$)', re.I),
            re.compile(r'v[\d.]+(?:\s+\w+){0,3}\s+(?:released|published|deployed)', re.I),
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                milestone = m.group(0).strip()
                self._milestones.append(f"[T{turn}] {milestone}")

    def _extract_errors(self, text: str, turn: int):
        """Extract error statements."""
        patterns = [
            re.compile(r'(?:error|fail|bug|broke|wrong|mistake|oops|SIGKILL|499|402|403)[:\s]+(.{10,120}?)(?:\.|\n|$)', re.I),
            re.compile(r'(?:ModuleNotFound|ImportError|SyntaxError|ConnectionError|HTTPError)[:\s]+(.{10,120}?)(?:\.|\n|$)', re.I),
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                error = m.group(0).strip()
                self._errors.append(f"[T{turn}] {error}")

    def _extract_entities(self, text: str):
        """Extract key entities (versions, tools, concepts)."""
        # Version strings
        for m in re.finditer(r'v(\d+\.\d+\.\d+)', text):
            self._entity_counts[f"v{m.group(1)}"] += 1
        # Tool names
        for m in re.finditer(r'\b(PyPI|GitHub|Zenodo|JOSS|OSF|arXiv)\b', text, re.I):
            self._entity_counts[m.group(1)] += 1
        # File references
        for m in re.finditer(r'\b([\w/]+\.(?:py|md|jsonl|yaml|yml|toml))\b', text):
            fname = m.group(1)
            if '/' in fname or '_' in fname:
                self._entity_counts[fname] += 1

    def _extract_files(self, text: str):
        """Extract file paths mentioned in the text."""
        for m in re.finditer(r'([\w/\\]+\.(?:py|md|jsonl|cff))', text):
            self._key_files.add(m.group(1))

    def _text_similarity(self, a: str, b: str) -> float:
        """Simple Jaccard similarity for topic change detection."""
        words_a = set(re.findall(r'\w{3,}', a.lower()))
        words_b = set(re.findall(r'\w{3,}', b.lower()))
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def _segment_turns(self) -> List[SessionSegment]:
        """Segment turns into coherent topic blocks."""
        if not self._turns:
            return []

        segments = []
        boundaries = [1] + sorted(self._topic_changes) + [self._turns[-1]["turn"] + 1]

        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1] - 1

            # Get turns in this segment
            seg_turns = [t for t in self._turns if start <= t["turn"] <= end]
            if not seg_turns:
                continue

            # Topic = most frequent entity
            seg_text = " ".join(t["content"] for t in seg_turns)
            seg_entities = self._entity_counts.most_common(3)
            topic = seg_entities[0][0] if seg_entities else f"Segment {i+1}"

            # Count decisions/lessons in this segment
            dec_count = sum(1 for d in self._decisions
                           if start <= int(re.search(r'\d+', d).group() if re.search(r'\d+', d) else '0') <= end)
            les_count = sum(1 for l in self._lessons
                           if start <= int(re.search(r'\d+', l).group() if re.search(r'\d+', l) else '0') <= end)

            # Summary = first sentence of each significant turn
            summary_parts = []
            for t in seg_turns[:5]:
                first_sent = re.split(r'[.。!！\n]', t["content"])[0][:100]
                if len(first_sent) > 10:
                    summary_parts.append(first_sent)
            summary = "; ".join(summary_parts[:3])

            segments.append(SessionSegment(
                topic=topic,
                start_turn=start,
                end_turn=end,
                summary=summary[:200],
                key_entities=[e[0] for e in seg_entities],
                decision_count=dec_count,
                lesson_count=les_count,
            ))

        return segments

    def summarize(self, output_path: str = "") -> SessionSummary:
        """
        Generate a full session summary.

        Args:
            output_path: If provided, write markdown summary to this file.

        Returns:
            SessionSummary with all extracted information.
        """
        segments = self._segment_turns()

        summary = SessionSummary(
            session_id=self.session_id,
            total_turns=len(self._turns),
            decisions=self._decisions[-10:],  # Last 10
            lessons=self._lessons[-10:],
            milestones=self._milestones[-10:],
            errors=self._errors[-10:],
            segments=segments,
            key_files=sorted(self._key_files)[-20:],
            stats={
                "avg_turn_length": sum(len(t["content"]) for t in self._turns) // max(len(self._turns), 1),
                "topic_changes": len(self._topic_changes),
                "top_entities": dict(self._entity_counts.most_common(10)),
            },
        )

        # Generate next steps from uncompleted decisions
        # (Simple heuristic: decisions without a following milestone)
        completed_keywords = ["released", "done", "completed", "finished", "pushed"]
        for d in self._decisions:
            is_completed = any(
                kw in m for m in self._milestones for kw in completed_keywords
            )
            if not is_completed and d not in summary.next_steps:
                summary.next_steps.append(d)

        # Write to file if requested
        if output_path:
            self._write_md(summary, output_path)

        return summary

    def summarize_with_guard(
        self,
        guard,
        output_path: str = "",
    ) -> SessionSummary:
        """
        Generate summary using MemoryGuard for quality filtering.

        Args:
            guard: MemoryGuard instance for filtering
            output_path: If provided, write markdown to this file
        """
        # First pass: feed all turns to guard
        for t in self._turns:
            guard.observe(
                content=t["content"],
                delta=t.get("delta", 0.5),
                source=t.get("source", ""),
            )

        # Archive guard memories before summarizing
        guard.flush(output_path)

        # Then summarize normally
        return self.summarize(output_path)

    def _write_md(self, summary: SessionSummary, path: str):
        """Write session summary as markdown."""
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        dt = datetime.fromtimestamp(summary.timestamp).strftime('%Y-%m-%d %H:%M')
        lines = [
            f"# Session Summary — {summary.session_id}",
            f"Generated: {dt} | {summary.total_turns} turns",
            "",
        ]

        if summary.decisions:
            lines.append("## 🔗 Decisions")
            for d in summary.decisions:
                lines.append(f"- {d}")
            lines.append("")

        if summary.lessons:
            lines.append("## 📖 Lessons")
            for l in summary.lessons:
                lines.append(f"- {l}")
            lines.append("")

        if summary.milestones:
            lines.append("## ✅ Milestones")
            for m in summary.milestones:
                lines.append(f"- {m}")
            lines.append("")

        if summary.errors:
            lines.append("## 🐛 Errors")
            for e in summary.errors:
                lines.append(f"- {e}")
            lines.append("")

        if summary.segments:
            lines.append("## 📐 Segments")
            for seg in summary.segments[:10]:
                lines.append(
                    f"- **{seg.topic}** (T{seg.start_turn}-T{seg.end_turn}): "
                    f"{seg.summary[:120]}"
                )
            lines.append("")

        if summary.next_steps:
            lines.append("## 🔜 Next Steps")
            for ns in summary.next_steps[:5]:
                lines.append(f"- [ ] {ns}")
            lines.append("")

        lines.append("---")
        lines.append(f"*Auto-generated by MSS-Agent SessionRecallSummarizer v0.3*")

        with open(path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))


# ── CLI 自检 ──

if __name__ == "__main__":
    print("=== Session Recall Summarizer Demo ===\n")

    summarizer = SessionRecallSummarizer(session_id="demo-001")

    # Simulate session turns
    turns = [
        ("✅ v0.3.4 released with ToolBudgetGate. Decided to push P0 tools to completion.", 0.7),
        ("SIGKILL error: the Windows Job Object killed the twine upload process. Root cause: subprocess timeout.", 0.2),
        ("Bug found: KB had 20 duplicate entries from the fill batch. Removed 5 duplicates in L2_APPLIED_THEORY.", 0.45),
        ("Learned that PowerShell f-string escaping fails every time with dict key access using brackets.", 0.5),
        ("Built MemoryGuard — auto-archives conversation turns filtered by Delta quality.", 0.6),
        ("Decided to use asyncio.gather for parallel agent execution. It cut latency by 50%.", 0.8),
        ("Just casual chat about the weather.", 0.1),
        ("Pushed v0.3.5 to PyPI and GitHub with MemoryGuard exports.", 0.7),
        ("ModuleNotFoundError on auto_archive.py — forgot to add __init__ export.", 0.3),
        ("✅ P0 tool suite 3/4 complete: ToolBudgetGate, MemoryGuard, AutoArchiver done.", 0.75),
    ]

    for i, (content, delta) in enumerate(turns, 1):
        summarizer.feed(content, turn=i, delta=delta)

    summary = summarizer.summarize("memory/session_demo.md")

    print(f"Session: {summary.session_id}")
    print(f"Turns: {summary.total_turns}")
    print(f"Decisions: {len(summary.decisions)}")
    print(f"Lessons: {len(summary.lessons)}")
    print(f"Milestones: {len(summary.milestones)}")
    print(f"Errors: {len(summary.errors)}")
    print(f"Segments: {len(summary.segments)}")
    print(f"Next steps: {len(summary.next_steps)}")
    print(f"Key files: {summary.key_files}")
    print(f"Top entities: {summary.stats.get('top_entities', {})}")
    print(f"\nWritten to: memory/session_demo.md")
