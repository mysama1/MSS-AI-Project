# MSS-LLM Perception Shell v2.0 — A7 + Molt upgrades
# Attached to: mssclaw/core/semantic/mss_llm_perception_shell.py (v0.1 base)
# Sprint 167, 2026-06-17

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

@dataclass
class CreativeOption:
    name: str
    eta_contribution: float
    heat_cost: float
    novelty: float
    source: str

    @property
    def efficiency(self) -> float:
        return self.eta_contribution / max(self.heat_cost, 0.001)


class A7CreativeSelector:
    """
    A7 最优性=创造性选择
    When L2-OP argmax ceiling (H635: eta <= 0.40) is hit,
    generate novel options beyond the existing choice set.

    Principle: Selection among existing = L2-OP (argmax).
              Creation of new options = A7 (creative).
    """

    L2_OP_CEILING = 0.40
    MIN_EFFICIENCY = 0.5

    def __init__(self):
        self.attempts = 0
        self.successes = 0

    def should_create(self, eta: float, options_count: int) -> bool:
        return eta < self.L2_OP_CEILING or options_count < 2

    def generate_options(self, problem: str, existing: List[str] = None) -> List[CreativeOption]:
        self.attempts += 1
        existing = existing or []
        options = [
            CreativeOption(f"synth({problem[:15]})", 0.45, 0.12, 0.6, "synthesis"),
            CreativeOption(f"mut({problem[:15]})", 0.35, 0.08, 0.4, "mutation"),
            CreativeOption(f"search({problem[:15]})", 0.25, 0.20, 0.9, "search"),
        ]
        valid = [o for o in options if o.efficiency >= self.MIN_EFFICIENCY]
        if not valid:
            valid = [options[0]]
        valid.sort(key=lambda o: o.efficiency, reverse=True)
        if valid[0].eta_contribution > 0.25:
            self.successes += 1
        return valid

    def select(self, opts: List[CreativeOption]) -> CreativeOption:
        return opts[0]

    def stats(self) -> dict:
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "rate": self.successes / max(self.attempts, 1),
            "ceiling": self.L2_OP_CEILING,
        }


class MoltAwareness:
    """
    H646: Eta-weighted KB molting awareness.

    Key finding: molt direction depends on model capability.
    - Weak models (0.5b): hardened = noise    -> molt beneficial (+67% eta)
    - Strong models (7b): hardened = reliable -> molt harmful   (-27% eta)

    Decision rule: molt iff eta_avg < 0.5 AND usage >= hardening_threshold.
    """

    HARDENING_THRESHOLD = 3
    ETA_MOLT_THRESHOLD = 0.5

    def __init__(self):
        self.history: Dict[str, dict] = {}

    def record(self, entry_id: str, eta: float, heat: float):
        if entry_id not in self.history:
            self.history[entry_id] = {"uses": 0, "eta_sum": 0.0, "heat_sum": 0.0}
        h = self.history[entry_id]
        h["uses"] += 1
        h["eta_sum"] += eta
        h["heat_sum"] += heat

    def should_molt(self, entry_id: str) -> Tuple[bool, str]:
        """Returns (should_molt, reason)"""
        if entry_id not in self.history:
            return False, "unknown"
        h = self.history[entry_id]
        if h["uses"] < self.HARDENING_THRESHOLD:
            return False, "not_hardened"
        avg = h["eta_sum"] / h["uses"]
        if avg < self.ETA_MOLT_THRESHOLD:
            return True, f"low_eta({avg:.2f}<{self.ETA_MOLT_THRESHOLD})"
        return False, f"protected(eta={avg:.2f})"

    def stats(self) -> dict:
        total = len(self.history)
        hardened = sum(1 for h in self.history.values() if h["uses"] >= self.HARDENING_THRESHOLD)
        molt_candidates = 0
        for eid in self.history:
            should, _ = self.should_molt(eid)
            if should:
                molt_candidates += 1
        return {
            "total_entries": total,
            "hardened": hardened,
            "molt_candidates": molt_candidates,
            "molt_rate": molt_candidates / max(total, 1),
        }


# ============================================================
# Quick demo
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MSS Perception Shell v2.0 — A7 + Molt Upgrades")
    print("=" * 60)

    # A7 Demo
    print("\n[A7 Creative Selector]")
    a7 = A7CreativeSelector()
    print(f"  L2-OP ceiling: {a7.L2_OP_CEILING}")

    # Stuck case
    stuck_eta = 0.35
    print(f"  eta={stuck_eta} (< ceiling) -> should_create: {a7.should_create(stuck_eta, 5)}")
    opts = a7.generate_options("Type_II_stuck_paradox")
    best = a7.select(opts)
    print(f"  Generated {len(opts)} options, best: {best.name} (eta={best.eta_contribution}, heat={best.heat_cost})")

    # Free case
    free_eta = 0.55
    print(f"  eta={free_eta} (> ceiling) -> should_create: {a7.should_create(free_eta, 5)}")
    print(f"  Stats: {a7.stats()}")

    # Molt Demo
    print("\n[Molt Awareness — Weak Model Simulation]")
    molt = MoltAwareness()

    # Simulate: weak model entries get low eta
    for i in range(3):
        molt.record("weak_entry", eta=0.2, heat=0.1)
    should, reason = molt.should_molt("weak_entry")
    print(f"  weak_entry: uses=3, eta=0.2 -> should_molt={should} ({reason})")

    # Simulate: strong model entries get high eta
    for i in range(3):
        molt.record("strong_entry", eta=0.95, heat=0.05)
    should, reason = molt.should_molt("strong_entry")
    print(f"  strong_entry: uses=3, eta=0.95 -> should_molt={should} ({reason})")

    # Not yet hardened
    molt.record("new_entry", eta=0.3, heat=0.0)
    should, reason = molt.should_molt("new_entry")
    print(f"  new_entry: uses=1 -> should_molt={should} ({reason})")

    print(f"\n  Stats: {molt.stats()}")
    print("\n✅ v2.0 Demo Complete")
