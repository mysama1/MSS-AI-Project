"""
Δ 增强记忆 v1.1 — 三层记忆 + 模式凝聚 + 意义评分.

v1.0: hash→dedup→close→evict (朴素的记忆体)
v1.1: L1热/L2温/L3归档 + 相似凝聚 + 意义评分 + 模式挖掘

三层架构:
  L1 (hot): 最近N条, 快速检索, 影响当前对话
  L2 (warm): 合并后的复合记忆, 影响策略决策
  L3 (cold): 归档模式, 用于跨会话演化分析

核心创新 — 意义评分 (Significance):
  简单重复不是意义, 高Δ+高频+跨任务 才是.
  S = Δ × log(repeats+1) × cross_task_weight
"""
from dataclasses import dataclass, field
from typing import Any, Optional
import hashlib
import time


@dataclass
class DeltaMemory:
    """
    Δ 增强记忆 v1.1.

    三层存储 + 自动凝聚 + 意义评分.
    """
    max_items: int = 100
    items: list = field(default_factory=list)  # [{hash, content, delta, repeats, ts, tier}]

    def _hash(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _embed(self, content: str) -> str:
        """轻量级语义嵌入 — 关键词抽取+权重."""
        words = content.lower().split()
        return " ".join(sorted(list(set(w for w in words if len(w) > 3)))[:20])

    def store(self, content: str, delta: float, task_id: str = ""):
        """存入记忆. 自动分 tier, 重复计数, 闭合检测."""
        h = self._hash(content)
        embed = self._embed(content)

        for item in self.items:
            if item["hash"] == h:
                item["repeats"] += 1
                item["ts"] = time.time()
                item["delta"] = max(item["delta"], delta)
                item["significance"] = self._calc_significance(item)
                if item["repeats"] > 3:
                    item["closed"] = True
                # Promote: active high-significance → L1
                if item["significance"] > 1.5 and item["tier"] != "L1":
                    item["tier"] = "L1"
                return

        # New entry
        ct = content[:500]
        self.items.append({
            "hash": h, "content": ct, "embed": embed,
            "delta": delta, "repeats": 1, "closed": False,
            "ts": time.time(), "tier": "L1",
            "task_id": task_id, "significance": 0.0,
        })
        self._evict()

    def _calc_significance(self, item: dict) -> float:
        """意义评分: S = |Δ| × log(repeats+1) × 任务交叉权重."""
        import math
        delta_w = abs(item.get("delta", 0))
        rep_w = math.log(item["repeats"] + 1)
        # Cross-task: how many unique tasks reference similar memory
        task_set = set(i.get("task_id", "") for i in self.items
                      if i.get("task_id") and self._jaccard(i.get("embed", ""), item.get("embed", "")) > 0.3)
        cross_w = max(1.0, len(task_set))
        return round(delta_w * rep_w * cross_w, 3)

    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        sa, sb = set(a.split()), set(b.split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def _evict(self):
        """三层逐出: L3(closed) → L2(low-sig) → L1(oldest)."""
        if len(self.items) <= self.max_items:
            return
        # Phase 0: promote to L3 cold archive
        self._tier_rotate()
        # Phase 1: evict closed L3
        closed_l3 = [i for i in self.items if i["closed"] and i["tier"] == "L3"]
        for c in closed_l3[:max(1, len(closed_l3) // 2)]:
            self.items.remove(c)
        if len(self.items) <= self.max_items:
            return
        # Phase 2: evict lowest-significance L2
        l2 = sorted([i for i in self.items if i["tier"] == "L2"],
                    key=lambda x: x.get("significance", 0))
        for c in l2[:max(1, len(self.items) - self.max_items)]:
            self.items.remove(c)
        if len(self.items) <= self.max_items:
            return
        # Phase 3: oldest L1
        while len(self.items) > self.max_items:
            self.items.sort(key=lambda x: x["ts"])
            self.items.pop(0)

    def _tier_rotate(self):
        """自动分层: closed→L3, low-sig→L2, high-sig→L1."""
        now = time.time()
        for item in self.items:
            age_h = (now - item["ts"]) / 3600
            if item["closed"]:
                item["tier"] = "L3"
            elif age_h > 24 or item.get("significance", 0) < 0.5:
                item["tier"] = "L2"
            else:
                item["tier"] = "L1"

    # ═══ 检索 ═══

    def retrieve(self, query: str, top_k: int = 5, tier: str = "L1") -> list:
        """检索相关记忆. 默认仅 L1 热记忆."""
        candidates = [i for i in self.items
                     if not i["closed"] and (tier == "all" or i["tier"] in (tier, "L1"))]
        query_words = set(query.lower().split())
        scored = []
        for item in candidates:
            content_words = set(item["content"].lower().split())
            overlap = len(query_words & content_words)
            freshness = max(0.0, 1.0 - (time.time() - item["ts"]) / 86400)
            sig = min(1.0, item.get("significance", 0) / 5.0)
            score = overlap * 0.5 + freshness * 0.3 + sig * 0.2
            if overlap > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    def retrieve_deep(self, query: str, top_k: int = 10) -> list:
        """深度检索: 扫描 L1+L2, 适合策略决策."""
        return self.retrieve(query, top_k=top_k, tier="all")

    # ═══ 凝聚 (Consolidation) ═══

    def consolidate(self, similarity_threshold: float = 0.6) -> int:
        """将相似记忆合并为复合条目.

        不只是去重 — 是组合: 两条 "error: timeout" 的不同实例
        合并为 "error: timeout (2 contexts: API, DB)".
        返回合并数."""
        merged = 0
        active = [i for i in self.items if not i["closed"]]
        for i in range(len(active)):
            if active[i] is None:
                continue
            for j in range(i + 1, len(active)):
                if active[j] is None:
                    continue
                sim = self._jaccard(
                    active[i].get("embed", ""),
                    active[j].get("embed", ""))
                if sim >= similarity_threshold:
                    # Merge: combine content, keep higher delta
                    active[i]["content"] = (
                        active[i]["content"][:400] + " | " +
                        active[j]["content"][:100])
                    active[i]["delta"] = max(active[i]["delta"], active[j]["delta"])
                    active[i]["repeats"] += active[j]["repeats"]
                    active[i]["ts"] = max(active[i]["ts"], active[j]["ts"])
                    active[i]["significance"] = self._calc_significance(active[i])
                    active[i]["merged_from"] = active[i].get("merged_from", 0) + 1
                    # Remove j from self.items
                    self.items.remove(active[j])
                    active[j] = None
                    merged += 1
        return merged

    # ═══ 模式挖掘 (Pattern Mining) ═══

    def patterns(self, min_occurrences: int = 2) -> list[dict]:
        """挖掘重复模式. 返回模式列表."""
        from collections import Counter
        # Extract keywords from all memories
        all_words = []
        for item in self.items:
            all_words.extend(item.get("embed", "").split())
        common = Counter(all_words).most_common(20)
        # Group by keyword
        patterns = []
        for word, count in common:
            if count >= min_occurrences:
                related = [i for i in self.items
                          if word in i.get("embed", "")]
                patterns.append({
                    "keyword": word,
                    "occurrences": count,
                    "avg_delta": round(sum(i["delta"] for i in related) / len(related), 3),
                    "max_significance": max((i.get("significance", 0) for i in related), default=0),
                })
        return sorted(patterns, key=lambda x: -x["max_significance"])

    # ═══ Scoring ═══

    def novelty_score(self, content: str) -> float:
        h = self._hash(content)
        for item in self.items:
            if item["hash"] == h:
                return max(0.0, 1.0 - item["repeats"] * 0.25)
        return 1.0

    def diversity_score(self) -> float:
        if len(self.items) < 3:
            return 1.0
        unique_hashes = len(set(i["hash"] for i in self.items))
        weighted_total = sum(1 + (i["repeats"] - 1) * 0.5 for i in self.items)
        return round(min(unique_hashes / weighted_total, 1.0), 4)

    # ═══ Stats ═══

    def stats(self) -> dict:
        by_tier = {"L1": 0, "L2": 0, "L3": 0}
        for i in self.items:
            by_tier[i.get("tier", "L1")] = by_tier.get(i.get("tier", "L1"), 0) + 1
        active = [i for i in self.items if not i["closed"]]
        closed = [i for i in self.items if i["closed"]]
        patterns = self.patterns(min_occurrences=2)
        return {
            "total": len(self.items),
            "active": len(active),
            "closed": len(closed),
            "by_tier": by_tier,
            "avg_significance": round(sum(i.get("significance", 0) for i in self.items) / max(len(self.items), 1), 3),
            "top_patterns": patterns[:5],
            "diversity": round(self.diversity_score(), 3),
            "avg_repeats": round(sum(i["repeats"] for i in self.items) / max(len(self.items), 1), 1),
        }
