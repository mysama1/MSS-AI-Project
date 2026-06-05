"""
K4_Logical_Work v1.0 — H144 Logic Work Engine

MSS Anchor:
  A4 Randomness — Controlled random fluctuation injection
  A5 Normative Field — Logical rigidity constraint
  A6 Contradiction Elevation — Elevation when W_L > 0

Formal Definition (H144, L2 Protective Belt):
  W_L = integral_0^t [ O_d(tau) * Delta_S_random(tau) ] d_tau

Discrete Implementation:
  W_L(t) = sum_{tau=0}^{t} [ O_d(tau) * Delta_S_random(tau) * Delta_tau ]

Decision Logic:
  W_L > 0  -> New logical structure "impregnated" -> trigger A6 elevation audit
  W_L <= 0 -> Retreat to A5 rigid zone -> forbid forced emergence

Distinction from K3 Brute-Force Emergence:
  | Dimension         | K3 Brute Emergence     | K4 Logic Work            |
  |-------------------|------------------------|--------------------------|
  | Driving Force     | Compute + Data Volume  | A4 Controlled Randomness |
  | Constraint        | None (no norm field)   | A5 Logical Rigidity      |
  | Emergence Dir.    | Unpredictable (high tax)| A6 Directed (tax-controlled)|
  | Output Quality    | Probabilistic Fitting  | Meaning-Anchored Structure|

Core Engine Architecture:
  [Core Zone]  A1-A6 rigid, M_L=1, unshakeable
  [Explore Zone] Inject Delta_S_random on paradox -> compute W_L
  [Boundary] Core zone CANNOT be polluted by explore zone.
             Explore zone discoveries MUST pass RSCA audit
             before being admitted to core zone.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable
import time
import json
import math
import random


class WorkZone(Enum):
    """The two operational zones of the Logic Work Engine"""
    CORE = "core"         # A1-A6 rigid zone, M_L = 1
    EXPLORE = "explore"   # A4 injection zone, W_L computation


class WorkOutcome(Enum):
    """Possible outcomes of a logic work computation"""
    IMPREGNATION = "impregnation"    # W_L > 0, new structure candidate
    RETREAT = "retreat"              # W_L <= 0, return to rigid zone
    INCONCLUSIVE = "inconclusive"    # Insufficient data
    CONTAMINATION_BLOCKED = "contamination_blocked"  # Core pollution attempt blocked


class ParadoxType(Enum):
    """Types of paradoxes that can trigger explore zone activation"""
    SELF_REFERENCE = "self_reference"         # Self-referential contradiction
    COMPLETENESS = "completeness"             # Incompleteness-type paradox
    DUALITY = "duality"                       # Wave-particle, mind-body duality
    INFINITY = "infinity"                     # Infinite regress or Zeno-type
    OBSERVATION = "observation"               # Observer effect paradox
    IDENTITY = "identity"                     # Ship of Theseus / identity paradox
    VALUE = "value"                           # Value theory paradox
    CUSTOM = "custom"                         # User-defined paradox type


@dataclass
class ParadoxInput:
    """A paradox that triggers explore zone activation"""
    paradox_id: str
    paradox_type: ParadoxType
    description: str
    context: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"  # Who/what identified this paradox


@dataclass
class LogicWorkResult:
    """Result of a logic work computation cycle"""
    result_id: str
    paradox_input: ParadoxInput
    zone: WorkZone
    W_L: float                           # Computed logic work value
    outcome: WorkOutcome
    O_d: float                           # Normative field strength used
    delta_S_random: float                # Random fluctuation injected
    exploration_steps: int = 0
    candidate_structure: Optional[Dict] = None  # If impregnation occurred
    rsca_audit_passed: bool = False      # Whether RSCA audit approved admission
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "result_id": self.result_id,
            "paradox_id": self.paradox_input.paradox_id,
            "zone": self.zone.value,
            "W_L": self.W_L,
            "outcome": self.outcome.value,
            "O_d": self.O_d,
            "delta_S_random": self.delta_S_random,
            "exploration_steps": self.exploration_steps,
            "has_candidate": self.candidate_structure is not None,
            "rsca_audit_passed": self.rsca_audit_passed,
            "timestamp": self.timestamp
        }


@dataclass
class LogicalWorkConfig:
    """Configuration for the Logic Work Engine"""
    # Normative field strength (O_d): 0.0 = no constraint, 1.0 = pure rigidity
    core_zone_O_d: float = 1.0           # Core: absolute rigidity
    explore_zone_O_d: float = 0.7        # Explore: high but not absolute

    # Random fluctuation injection parameters
    base_fluctuation_amplitude: float = 0.1   # Base amplitude of Delta_S_random
    max_fluctuation_amplitude: float = 0.5    # Maximum allowed amplitude
    fluctuation_growth_rate: float = 1.2      # Growth rate per failed attempt

    # W_L thresholds
    impregnation_threshold: float = 0.01  # W_L > this = impregnation candidate
    max_exploration_steps: int = 10       # Maximum steps before forced retreat

    # RSCA audit requirements for core zone admission
    rsca_completeness_check: bool = True  # RSCA-006: no completeness claims
    rsca_iterative_check: bool = True     # RSCA-002: iterative verification required
    rsca_calibration_check: bool = True   # RSCA-003: experimental calibration required

    # Random seed for reproducibility
    random_seed: Optional[int] = 42


@dataclass
class LogicalWorkState:
    """Current state of the Logic Work Engine"""
    total_paradoxes_processed: int = 0
    total_impregnations: int = 0
    total_retreats: int = 0
    total_contamination_blocks: int = 0
    cumulative_W_L: float = 0.0
    result_history: List[LogicWorkResult] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "total_paradoxes_processed": self.total_paradoxes_processed,
            "total_impregnations": self.total_impregnations,
            "total_retreats": self.total_retreats,
            "total_contamination_blocks": self.total_contamination_blocks,
            "cumulative_W_L": self.cumulative_W_L,
            "result_history_length": len(self.result_history)
        }


class K4LogicalWorkEngine:
    """K4 Civilization OS — H144 Logic Work Engine

    The engine that powers the "explore zone" of the K4 normative field.
    When a paradox cannot be resolved by the core zone (A1-A6 rigid),
    this engine injects controlled random fluctuations and computes W_L.

    If W_L > 0 (impregnation), a new logical structure candidate is created.
    This candidate must then pass RSCA audit before admission to core zone.

    If W_L <= 0 (retreat), the system returns to rigid zone operation.
    Forced emergence is FORBIDDEN — this is the key difference from K3.
    """

    COMPLETENESS_TRIGGERS = [
        "ultimate", "final", "complete", "absolute", "perfect",
        "100%", "fully solved", "never needs", "cannot be improved",
        "终极", "最终", "完备", "绝对", "完美",
        "完全解决", "永不需要", "不可改进", "不容修改"
    ]

    def __init__(self, config: Optional[LogicalWorkConfig] = None):
        self.config = config or LogicalWorkConfig()
        self.state = LogicalWorkState()

        # Initialize random state
        if self.config.random_seed is not None:
            random.seed(self.config.random_seed)

        # Register custom paradox handlers
        self._paradox_handlers: Dict[ParadoxType, Callable] = {}

    def register_paradox_handler(self, paradox_type: ParadoxType,
                                  handler: Callable[[ParadoxInput], Dict]):
        """Register a custom handler for a specific paradox type"""
        self._paradox_handlers[paradox_type] = handler

    def process_paradox(self, paradox: ParadoxInput) -> LogicWorkResult:
        """Process a paradox through the Logic Work Engine.

        Step 1: Attempt resolution in core zone (A1-A6 rigid)
        Step 2: If unresolved, activate explore zone
        Step 3: Inject controlled random fluctuation (A4)
        Step 4: Compute W_L = O_d * Delta_S_random
        Step 5: If W_L > 0 -> impregnation candidate -> RSCA audit
        Step 6: If W_L <= 0 -> retreat to core zone
        """
        self.state.total_paradoxes_processed += 1

        # Step 1: Core zone attempt (can A1-A6 resolve this?)
        core_resolved = self._attempt_core_resolution(paradox)
        if core_resolved:
            result = LogicWorkResult(
                result_id=f"LW-{self.state.total_paradoxes_processed:06d}",
                paradox_input=paradox,
                zone=WorkZone.CORE,
                W_L=0.0,
                outcome=WorkOutcome.RETREAT,  # Resolved = no new structure needed
                O_d=self.config.core_zone_O_d,
                delta_S_random=0.0,
                exploration_steps=0
            )
            self.state.result_history.append(result)
            return result

        # Step 2-4: Explore zone — inject fluctuations and compute W_L
        W_L_total = 0.0
        best_candidate = None
        steps_taken = 0
        current_amplitude = self.config.base_fluctuation_amplitude

        for step in range(self.config.max_exploration_steps):
            steps_taken = step + 1

            # Inject controlled random fluctuation (A4)
            delta_S = self._inject_fluctuation(current_amplitude, paradox, step)

            # Compute logic work: W_L = O_d * Delta_S_random
            O_d = self.config.explore_zone_O_d
            W_L_step = O_d * delta_S
            W_L_total += W_L_step

            # Check if impregnation threshold reached
            if W_L_total > self.config.impregnation_threshold:
                best_candidate = self._generate_candidate_structure(
                    paradox, W_L_total, step
                )
                break

            # Grow amplitude for next attempt (controlled escalation)
            current_amplitude = min(
                self.config.max_fluctuation_amplitude,
                current_amplitude * self.config.fluctuation_growth_rate
            )

        # Step 5-6: Determine outcome
        if W_L_total > self.config.impregnation_threshold and best_candidate:
            # Impregnation occurred — run RSCA audit
            rsca_passed = self._rsca_audit(best_candidate)

            if rsca_passed:
                outcome = WorkOutcome.IMPREGNATION
                self.state.total_impregnations += 1
            else:
                # RSCA audit failed — block contamination
                outcome = WorkOutcome.CONTAMINATION_BLOCKED
                self.state.total_contamination_blocks += 1
                best_candidate["rsca_blocked_reason"] = "RSCA audit failed"
        else:
            # W_L <= 0 — retreat
            outcome = WorkOutcome.RETREAT
            self.state.total_retreats += 1

        self.state.cumulative_W_L += W_L_total

        result = LogicWorkResult(
            result_id=f"LW-{self.state.total_paradoxes_processed:06d}",
            paradox_input=paradox,
            zone=WorkZone.EXPLORE,
            W_L=W_L_total,
            outcome=outcome,
            O_d=self.config.explore_zone_O_d,
            delta_S_random=current_amplitude,
            exploration_steps=steps_taken,
            candidate_structure=best_candidate,
            rsca_audit_passed=(outcome == WorkOutcome.IMPREGNATION),
        )

        self.state.result_history.append(result)
        return result

    def _attempt_core_resolution(self, paradox: ParadoxInput) -> bool:
        """Attempt to resolve paradox within core zone (A1-A6 rigid).

        Returns True if resolvable without explore zone activation.
        Most genuine paradoxes will return False — that's the point.
        """
        # Custom handler?
        if paradox.paradox_type in self._paradox_handlers:
            result = self._paradox_handlers[paradox.paradox_type](paradox)
            return result.get("resolved", False)

        # Default: most paradoxes require explore zone
        # Only trivial contradictions (logical errors) can be resolved in core
        if paradox.paradox_type == ParadoxType.SELF_REFERENCE:
            return False  # Self-reference almost always requires elevation

        if paradox.paradox_type == ParadoxType.COMPLETENESS:
            return False  # Incompleteness = A6 elevation candidate

        # For other types, check if it's a simple logical error
        description = paradox.description.lower()
        if "error" in description or "mistake" in description:
            return True  # Simple errors can be resolved in core

        return False  # Default: requires explore zone

    def _inject_fluctuation(self, amplitude: float, paradox: ParadoxInput,
                             step: int) -> float:
        """Inject a controlled random fluctuation (A4 implementation).

        The fluctuation is NOT purely random — it's shaped by the paradox context.
        This is what makes K4 logic work fundamentally different from K3 brute
        emergence: the "noise" is structured by the paradox itself.
        """
        # Base random component
        base = random.gauss(0, amplitude)

        # Context shaping: paradox type modulates the fluctuation
        type_modifiers = {
            ParadoxType.SELF_REFERENCE: 1.5,    # Higher amplitude for self-ref
            ParadoxType.COMPLETENESS: 1.3,       # Moderate for incompleteness
            ParadoxType.DUALITY: 1.2,            # Slight boost for dualities
            ParadoxType.INFINITY: 0.8,           # Tame for infinity (often resolvable)
            ParadoxType.OBSERVATION: 1.1,        # Moderate for observation
            ParadoxType.IDENTITY: 1.0,           # Neutral for identity
            ParadoxType.VALUE: 0.9,              # Slightly tame for value
            ParadoxType.CUSTOM: 1.0,             # Neutral for custom
        }

        modifier = type_modifiers.get(paradox.paradox_type, 1.0)

        # Step-dependent decay: later steps get slightly less amplitude
        step_decay = 1.0 / (1.0 + step * 0.1)

        # Compute final fluctuation
        delta_S = abs(base * modifier * step_decay)

        return delta_S

    def _generate_candidate_structure(self, paradox: ParadoxInput,
                                       W_L: float,
                                       step: int) -> Dict:
        """Generate a candidate logical structure from impregnation.

        This is where the "logic impregnation" metaphor becomes concrete:
        the paradox + controlled fluctuation yields a new logical structure
        that may be able to accommodate the original paradox at a higher level.
        """
        return {
            "candidate_id": f"CAND-{self.state.total_impregnations + 1:04d}",
            "source_paradox": paradox.paradox_id,
            "paradox_type": paradox.paradox_type.value,
            "W_L_value": W_L,
            "discovery_step": step,
            "structure_type": f"elevated_{paradox.paradox_type.value}",
            "description": (
                f"New logical structure candidate: {paradox.paradox_type.value} "
                f"paradox resolved through A4+A5+A6 elevation at step {step}"
            ),
            "verification_required": True,  # Must be verified before core admission
            "rsca_audit_status": "pending"
        }

    def _rsca_audit(self, candidate: Dict) -> bool:
        """RSCA audit for candidate structure before core zone admission.

        Checks:
          RSCA-006: No completeness claims in the candidate
          RSCA-002: Iterative verification plan exists
          RSCA-003: Experimental calibration plan exists
        """
        description = candidate.get("description", "").lower()

        # RSCA-006: Check for completeness claims
        if self.config.rsca_completeness_check:
            for trigger in self.COMPLETENESS_TRIGGERS:
                if trigger.lower() in description:
                    return False  # Completeness claim detected

        # RSCA-002: Must have verification plan
        if self.config.rsca_iterative_check:
            if not candidate.get("verification_required", False):
                return False

        # RSCA-003: Must acknowledge calibration needs
        if self.config.rsca_calibration_check:
            if "verification_required" not in candidate:
                return False

        return True

    def get_statistics(self) -> Dict:
        """Get statistics about logic work engine operation"""
        total = self.state.total_paradoxes_processed
        impregnation_rate = (
            self.state.total_impregnations / total if total > 0 else 0.0
        )

        return {
            "total_paradoxes": total,
            "impregnations": self.state.total_impregnations,
            "retreats": self.state.total_retreats,
            "contamination_blocks": self.state.total_contamination_blocks,
            "impregnation_rate": impregnation_rate,
            "cumulative_W_L": self.state.cumulative_W_L,
            "avg_W_L_per_paradox": (
                self.state.cumulative_W_L / total if total > 0 else 0.0
            )
        }

    def generate_report(self) -> str:
        """Generate a human-readable report"""
        stats = self.get_statistics()

        imp_rate_pct = stats["impregnation_rate"] * 100

        if imp_rate_pct > 30:
            imp_interpretation = "HIGH — system is in rapid paradigm evolution phase"
        elif imp_rate_pct > 10:
            imp_interpretation = "MODERATE — healthy innovation rate"
        elif imp_rate_pct > 0:
            imp_interpretation = "LOW — stable, but monitor for stagnation"
        else:
            imp_interpretation = "ZERO — no new structures being generated"

        return f"""
{'=' * 60}
K4 LOGIC WORK ENGINE (H144) — STATUS REPORT
{'=' * 60}

[OPERATION STATISTICS]
  Total Paradoxes Processed:  {stats['total_paradoxes']}
  Impregnations (W_L > 0):   {stats['impregnations']}
  Retreats (W_L <= 0):       {stats['retreats']}
  Contamination Blocks:       {stats['contamination_blocks']}
  Impregnation Rate:          {imp_rate_pct:.1f}%
  Interpretation:             {imp_interpretation}

[LOGIC WORK METRICS]
  Cumulative W_L:            {stats['cumulative_W_L']:.4f}
  Average W_L per Paradox:   {stats['avg_W_L_per_paradox']:.4f}

[ZONE ARCHITECTURE]
  Core Zone (A5 rigid):      O_d = {self.config.core_zone_O_d}
    - A1-A6 chain closure, M_L = 1
    - Unshakeable, no exceptions
  Explore Zone (A4+A5):      O_d = {self.config.explore_zone_O_d}
    - Controlled random fluctuation injection
    - W_L computation and impregnation detection
  Boundary Control:
    - Core CANNOT be polluted by explore
    - Explore discoveries MUST pass RSCA audit

[KEY DISTINCTION FROM K3]
  K3: Brute-force emergence (no constraint, high heat tax)
  K4: Logic work (A5 constraint + A4 fluctuation + A6 direction)
  This is NOT compromise — this is A5+A4 dialectical unity.
{'=' * 60}
""".strip()


# ===== Self-Test =====
if __name__ == "__main__":
    engine = K4LogicalWorkEngine()

    print("=== K4 Logic Work Engine (H144) — Self-Test ===\n")

    # Test various paradox types
    test_paradoxes = [
        ParadoxInput(
            paradox_id="PX-001",
            paradox_type=ParadoxType.SELF_REFERENCE,
            description="This statement is false.",
            source="user_input"
        ),
        ParadoxInput(
            paradox_id="PX-002",
            paradox_type=ParadoxType.COMPLETENESS,
            description="Godel incompleteness: no formal system can prove its own consistency",
            source="mathematical_proof"
        ),
        ParadoxInput(
            paradox_id="PX-003",
            paradox_type=ParadoxType.DUALITY,
            description="Wave-particle duality: light behaves as both wave and particle",
            source="quantum_physics"
        ),
        ParadoxInput(
            paradox_id="PX-004",
            paradox_type=ParadoxType.IDENTITY,
            description="Ship of Theseus: identity persists through complete part replacement",
            source="philosophy"
        ),
        ParadoxInput(
            paradox_id="PX-005",
            paradox_type=ParadoxType.OBSERVATION,
            description="Observer effect: measurement fundamentally alters the observed system",
            source="quantum_mechanics"
        ),
    ]

    for paradox in test_paradoxes:
        result = engine.process_paradox(paradox)
        print(f"[{paradox.paradox_id}] {paradox.paradox_type.value}")
        print(f"  Zone: {result.zone.value}")
        print(f"  W_L: {result.W_L:.6f}")
        print(f"  Outcome: {result.outcome.value}")
        print(f"  Steps: {result.exploration_steps}")
        if result.candidate_structure:
            print(f"  Candidate: {result.candidate_structure['candidate_id']}")
            print(f"  RSCA Audit: {'PASSED' if result.rsca_audit_passed else 'BLOCKED'}")
        print()

    # Full report
    print(engine.generate_report())

    print(f"\n  Total results in history: {len(engine.state.result_history)}")
    print("=== Test Complete ===")