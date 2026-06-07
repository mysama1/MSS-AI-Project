"""
Δ 增强记忆 — MSS-Agent 的记忆不是缓存, 是有自检的.

普通 Agent: task→memory→retrieve→repeat
MSS-Agent: task→memory→delta_check→Δ↓→forget_old→learn_new
"""
from dataclasses import dataclass, field
from typing import Any, Optional
import hashlib
import time


@dataclass
class DeltaMemory:
    """
    Δ 增强记忆. 三个原则:
    1. 不要记住一切 (闭合)
    2. 遗忘模式=学习 (蜕壳)
    3. 新鲜度>完整度

    max_items: 最大记忆条数 (超过则遗忘重复次数最多的)
    """
    max_items: int = 100
    items: list = field(default_factory=list)  # [{hash, content, delta, repeats, ts}]

    def _hash(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def store(self, content: str, delta: float):
        """存入记忆. 如果已存在→增加重复计数. 重复>3次→标记为闭合."""
        h = self._hash(content)

        for item in self.items:
            if item["hash"] == h:
                item["repeats"] += 1
                item["ts"] = time.time()
                item["delta"] = delta
                if item["repeats"] > 3:
                    item["closed"] = True  # 闭合 = 应该遗忘的
                return

        self.items.append({
            "hash": h,
            "content": content[:500],
            "delta": delta,
            "repeats": 1,
            "closed": False,
            "ts": time.time(),
        })

        # Evict: remove closed items first, then oldest
        if len(self.items) > self.max_items:
            closed = [i for i in self.items if i["closed"]]
            for c in closed[:max(1, len(closed) // 2)]:
                self.items.remove(c)
            while len(self.items) > self.max_items:
                self.items.sort(key=lambda x: x["ts"])
                self.items.pop(0)

    def retrieve(self, query: str, top_k: int = 5) -> list:
        """检索相关记忆. 排除已闭合的."""
        active = [i for i in self.items if not i["closed"]]
        # Simple keyword overlap scoring
        query_words = set(query.lower().split())
        scored = []
        for item in active:
            content_words = set(item["content"].lower().split())
            overlap = len(query_words & content_words)
            freshness = 1.0 - (time.time() - item["ts"]) / 86400  # 1 day decay
            score = overlap * 0.7 + freshness * 0.3
            if overlap > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    def novelty_score(self, content: str) -> float:
        """计算当前内容的 newness. 0=完全重复, 1=全新."""
        h = self._hash(content)
        for item in self.items:
            if item["hash"] == h:
                return max(0.0, 1.0 - item["repeats"] * 0.25)
        return 1.0

    def diversity_score(self) -> float:
        """计算记忆多样性。重复任务压低分数。0=单一模式, 1=高度多样。"""
        if len(self.items) < 3:
            return 1.0
        unique_hashes = len(set(i["hash"] for i in self.items))
        # Weighted: each repeat adds weight, reducing diversity
        weighted_total = sum(1 + (i["repeats"] - 1) * 0.5 for i in self.items)
        return round(min(unique_hashes / weighted_total, 1.0), 4)

    def stats(self) -> dict:
        active = [i for i in self.items if not i["closed"]]
        closed = [i for i in self.items if i["closed"]]
        return {
            "total": len(self.items),
            "active": len(active),
            "closed": len(closed),
            "diversity": round(self.diversity_score(), 3),
            "avg_repeats": round(sum(i["repeats"] for i in self.items) / max(len(self.items), 1), 1),
        }
