"""
L1 Quorum-Fast 汇聚 (H525). 多 Agent 视角收敛检测.

收敛 = 坏 (视角闭合). 发散 = 好 (多个独立视角).
"""
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class QuorumFast:
    """
    多 Agent quorum 检测.

    Usage:
        qf = QuorumFast()
        qf.report("agent_a", 0.72)
        qf.report("agent_b", 0.35)
        qf.report("agent_c", 0.68)
        if qf.converged():
            print("Warning: agents converging on same answer")
    """
    threshold: float = 0.6  # quorum > this OR < (1-this) → converged
    reports: List[Dict] = field(default_factory=list)

    def report(self, agent_id: str, score: float, label: str = ""):
        self.reports.append({
            "agent": agent_id,
            "score": round(score, 4),
            "label": label,
        })

    def quorum(self) -> float:
        """Quorum value: fraction of agents above threshold."""
        if not self.reports:
            return 0.0
        above = sum(1 for r in self.reports if r["score"] > self.threshold)
        return round(above / len(self.reports), 3)

    def converged(self) -> bool:
        """True = BAD (all agents agree, no diversity)."""
        q = self.quorum()
        return q > 0.8 or q < 0.2

    def status(self) -> str:
        q = self.quorum()
        if q > 0.9:
            return "HYPER_CONVERGENT (warning: groupthink)"
        if q < 0.1:
            return "HYPER_CONVERGENT (warning: unanimous disagree)"
        if self.converged():
            return "CONVERGENT"
        return "DIVERGENT (healthy)"

    def snapshot(self) -> dict:
        return {
            "agents": len(self.reports),
            "quorum": self.quorum(),
            "status": self.status(),
            "scores": {r["agent"]: r["score"] for r in self.reports},
        }
