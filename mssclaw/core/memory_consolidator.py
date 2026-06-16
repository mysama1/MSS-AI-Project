"""
Memory Consolidator — 自动凝聚旧记忆

类似人脑睡眠时的记忆整合:
  - 短时记忆(活跃) → 长时记忆(凝聚)
  - 相似记忆合并
  - 降低冗余, 保留精髓
  - 模式提取

用法:
    consolidator = MemoryConsolidator(agent.memory)
    summary = consolidator.consolidate()
    # 或: agent.memory.auto_consolidate()
"""
from __future__ import annotations
from collections import Counter
import re
import time
from typing import List, Dict


class MemoryConsolidator:
    """
    记忆凝聚器.

    当活跃记忆超过阈值时, 自动将旧记忆转化为压缩版.
    """

    def __init__(self, memory, max_active: int = 50, similarity_threshold: float = 0.6):
        self._memory = memory
        self._max_active = max_active
        self._similarity = similarity_threshold
        self._consolidated_count = 0
        self._last_consolidation = 0.0

    def should_consolidate(self) -> bool:
        """是否需要凝聚."""
        stats = self._memory.stats()
        return stats.get("active", 0) > self._max_active

    def consolidate(self) -> dict:
        """
        执行记忆凝聚.

        返回: {consolidated, merged, patterns, summary}
        """
        items = []
        try:
            items = self._memory.items
        except AttributeError:
            return {"error": "memory has no items attribute"}

        if not items:
            return {"consolidated": 0, "merged": 0, "patterns": [], "summary": ""}

        now = time.time()
        consolidated = 0
        merged_pairs = 0

        # 1. Find and merge similar items
        to_remove = set()
        for i in range(len(items)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(items)):
                if j in to_remove:
                    continue
                sim = self._similarity_score(
                    self._item_text(items[i]),
                    self._item_text(items[j]),
                )
                if sim > self._similarity:
                    # Merge: keep the higher-delta one, remove the other
                    delta_i = self._item_delta(items[i])
                    delta_j = self._item_delta(items[j])
                    if delta_i >= delta_j:
                        to_remove.add(j)
                    else:
                        to_remove.add(i)
                        break
                    merged_pairs += 1

        # Remove marked items (newest first to avoid index shifts)
        for idx in sorted(to_remove, reverse=True):
            del items[idx]
            consolidated += 1

        # 2. Extract patterns
        patterns = self._extract_patterns(items)

        # 3. Generate summary
        summary = self._generate_summary(items, patterns)

        self._consolidated_count += consolidated
        self._last_consolidation = now

        return {
            "consolidated": consolidated,
            "merged_pairs": merged_pairs,
            "patterns": patterns,
            "summary": summary,
            "remaining": len(items),
            "total_consolidated": self._consolidated_count,
        }

    def auto_consolidate(self) -> dict:
        """自动凝聚 (如果超过阈值)."""
        if self.should_consolidate():
            return self.consolidate()
        return {"consolidated": 0, "merged_pairs": 0, "patterns": [], "summary": "below threshold"}

    @staticmethod
    def _item_text(item) -> str:
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            return item.get("content", item.get("text", str(item)))
        try:
            return str(item)
        except Exception:
            return ""

    @staticmethod
    def _item_delta(item) -> float:
        if isinstance(item, dict):
            return item.get("delta", item.get("score", 0.5))
        return 0.5

    @staticmethod
    def _similarity_score(a: str, b: str) -> float:
        """简单 Jaccard 相似度."""
        if not a or not b:
            return 0.0
        words_a = set(re.findall(r'\w+', a.lower()))
        words_b = set(re.findall(r'\w+', b.lower()))
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    @staticmethod
    def _extract_patterns(items: list) -> list:
        """提取重复模式."""
        words = []
        for item in items:
            text = MemoryConsolidator._item_text(item)
            words.extend(re.findall(r'\w{3,}', text.lower()))

        counter = Counter(words)
        # Top patterns (>2 occurrences, >3 chars)
        patterns = [
            {"word": w, "count": c}
            for w, c in counter.most_common(20)
            if c >= 2 and len(w) >= 4
        ]
        return patterns[:10]

    @staticmethod
    def _generate_summary(items: list, patterns: list) -> str:
        """生成记忆摘要."""
        if not items:
            return "(empty)"
        total = len(items)
        top_patterns = ", ".join(p["word"] for p in patterns[:5])
        avg_delta = sum(
            MemoryConsolidator._item_delta(i) for i in items
        ) / max(total, 1)
        return (
            f"{total} memories | avg Δ={avg_delta:.2f} | "
            f"patterns: {top_patterns}" if top_patterns else
            f"{total} memories | avg Δ={avg_delta:.2f}"
        )

    def stats(self) -> dict:
        return {
            "max_active": self._max_active,
            "similarity_threshold": self._similarity,
            "total_consolidated": self._consolidated_count,
            "last_consolidation": self._last_consolidation,
        }
