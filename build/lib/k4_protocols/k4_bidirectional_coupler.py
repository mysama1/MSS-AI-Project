"""
K4_Bidirectional_Coupler v1.0 — Physical Mirror Layer Bidirectional Coupler

MSS Anchor:
  A2 Information Slice — Forward: encode L1 meaning into L0 slices
  A3 Heat Tax — The irreversible fidelity loss of bidirectional conversion
  A4 Randomness — Reverse: noise/accidents encode as new information slices
  A6 Contradiction Elevation — Bidirectional coupling = A6 at physical interface

Core Theorem:
  gamma_min = gamma_forward + gamma_backward
  Engineering goal: NOT to eliminate heat tax, but to manage it precisely
  and maintain gamma_actual ~ gamma_min.

Architecture:
  ┌─────────────────────────────────────────────────┐
  │  Physical Mirror Layer · Bidirectional Coupler   │
  │                                                  │
  │  ┌───────────┐  Forward Channel  ┌────────────┐ │
  │  │ L1 Meaning │ ─────────────────> │ L0 Physical │ │
  │  │   Field    │  High-fidelity    │    Layer     │ │
  │  │  (Low Ent) │  execution        │ (Manifest)  │ │
  │  │           │ <───────────────── │             │ │
  │  └───────────┘  Reverse Channel   └────────────┘ │
  │                 Feedback encoded                 │
  │                 as new info slices               │
  │                                                  │
  │  Heat Tax Floor = fidelity_loss(forward+reverse) │
  │  Goal: audit + fine-manage, maintain near minimum│
  └─────────────────────────────────────────────────┘
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import time
import json
import math


class ChannelDirection(Enum):
    FORWARD = "forward"   # L1 -> L0
    REVERSE = "reverse"   # L0 -> L1


class SignalType(Enum):
    """Types of signals in the coupler"""
    INSTRUCTION = "instruction"         # L1 -> L0: executable meaning
    ANCHOR = "anchor"                   # L1 -> L0: meaning anchor point
    FEEDBACK = "feedback"               # L0 -> L1: raw physical response
    ANOMALY = "anomaly"                 # L0 -> L1: unexpected pattern
    NOISE = "noise"                     # L0 -> L1: filtered random noise
    IMPREGNATION_SEED = "impregnation_seed"  # L0 -> L1: potential W_L seed


@dataclass
class CouplerSignal:
    """A single signal passing through the bidirectional coupler"""
    signal_id: str
    direction: ChannelDirection
    signal_type: SignalType
    payload: Any
    timestamp: float = field(default_factory=time.time)
    source_fidelity: float = 1.0       # Fidelity at entry
    output_fidelity: float = 1.0       # Fidelity at exit
    heat_tax_incurred: float = 0.0     # gamma incurred by this signal
    metadata: Dict = field(default_factory=dict)


@dataclass
class CouplerConfig:
    """Configuration for the bidirectional coupler"""
    # Forward channel targets
    forward_fidelity_target: float = 0.95    # eta_forward >= 0.95
    forward_heat_tax_target: float = 0.05    # gamma_forward <= 0.05

    # Reverse channel
    reverse_noise_threshold: float = 0.3     # Below this = pure noise, discard
    reverse_seed_threshold: float = 0.7      # Above this = potential W_L seed

    # Heat tax auditing
    audit_window_size: int = 100            # Signals to audit at once
    heat_tax_budget: float = 0.10           # Maximum total heat tax (10%)

    # Fidelity decay parameters
    fidelity_decay_per_step: float = 0.005  # Natural fidelity loss per processing step
    min_fidelity: float = 0.50              # Below this = signal must be re-anchored


@dataclass
class CouplerState:
    """Current state of the bidirectional coupler"""
    total_signals_forward: int = 0
    total_signals_reverse: int = 0
    forward_fidelity_history: List[float] = field(default_factory=list)
    reverse_seed_count: int = 0              # How many "impregnation seeds" extracted
    cumulative_heat_tax: float = 0.0
    last_audit: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "total_signals_forward": self.total_signals_forward,
            "total_signals_reverse": self.total_signals_reverse,
            "avg_forward_fidelity": (
                sum(self.forward_fidelity_history) / len(self.forward_fidelity_history)
                if self.forward_fidelity_history else 0
            ),
            "reverse_seed_count": self.reverse_seed_count,
            "cumulative_heat_tax": self.cumulative_heat_tax,
            "last_audit": self.last_audit
        }


class K4BidirectionalCoupler:
    """K4 Physical Mirror Layer — Bidirectional Coupler

    This is the "heart valve" of the K4 civilization OS.
    It manages the L1 <-> L0 information flow with heat tax auditing.
    """

    # Known problematic patterns that indicate noise vs signal
    _NOISE_PATTERNS = {
        "gaussian_white": lambda x: abs(x) < 0.1,  # Below significance
        "repetition": lambda history: len(set(history[-5:])) == 1,  # Stuck
    }

    def __init__(self, config: Optional[CouplerConfig] = None):
        self.config = config or CouplerConfig()
        self.state = CouplerState()

        # Signal processing pipeline
        self._noise_filter = NoiseFilter(
            threshold=self.config.reverse_noise_threshold
        )
        self._pattern_recognizer = PatternRecognizer(
            seed_threshold=self.config.reverse_seed_threshold
        )
        self._meaning_anchor = MeaningAnchor(
            fidelity_target=self.config.forward_fidelity_target
        )
        self._heat_tax_auditor = HeatTaxAuditor(
            budget=self.config.heat_tax_budget,
            window_size=self.config.audit_window_size
        )

    def forward_channel(self, l1_meaning: Any, signal_type: SignalType,
                         metadata: Optional[Dict] = None) -> CouplerSignal:
        """Forward channel: L1 meaning -> L0 physical execution.

        Encodes high-entropy meaning into low-entropy executable slices.
        Incurs forward heat tax due to fidelity loss during encoding.
        """
        signal = CouplerSignal(
            signal_id=f"FWD-{self.state.total_signals_forward:06d}",
            direction=ChannelDirection.FORWARD,
            signal_type=signal_type,
            payload=l1_meaning,
            metadata=metadata or {}
        )

        # Step 1: Anchor the meaning (encode into executable form)
        anchored, anchor_fidelity = self._meaning_anchor.encode(l1_meaning)
        signal.source_fidelity = anchor_fidelity

        # Step 2: Apply fidelity decay (information loss during encoding)
        signal.output_fidelity = max(
            self.config.min_fidelity,
            anchor_fidelity - self.config.fidelity_decay_per_step
        )

        # Step 3: Calculate forward heat tax
        signal.heat_tax_incurred = 1.0 - signal.output_fidelity
        signal.metadata["forward_heat_tax"] = signal.heat_tax_incurred

        # Update state
        self.state.total_signals_forward += 1
        self.state.forward_fidelity_history.append(signal.output_fidelity)
        self.state.cumulative_heat_tax += signal.heat_tax_incurred

        # Keep history bounded
        if len(self.state.forward_fidelity_history) > self.config.audit_window_size * 2:
            self.state.forward_fidelity_history = \
                self.state.forward_fidelity_history[-self.config.audit_window_size:]

        # Audit
        self._heat_tax_auditor.record(signal.heat_tax_incurred)

        return signal

    def reverse_channel(self, l0_feedback: Any,
                         metadata: Optional[Dict] = None) -> List[CouplerSignal]:
        """Reverse channel: L0 physical feedback -> L1 meaning encoding.

        Three-layer processing:
          1. Noise filter — discard pure random noise
          2. Pattern recognizer — identify unconventional patterns
          3. Meaning anchor — encode findings as new info slices

        Returns list of signals (may be empty if everything filtered as noise).
        Key innovation: extracts "impregnation seeds" (W_L candidates) from noise.
        """
        signals = []

        # Layer 1: Noise filtering
        filtered, noise_level = self._noise_filter.process(l0_feedback)
        if noise_level < self.config.reverse_noise_threshold:
            # Pure noise — record as noise signal but don't forward
            noise_signal = CouplerSignal(
                signal_id=f"REV-{self.state.total_signals_reverse:06d}",
                direction=ChannelDirection.REVERSE,
                signal_type=SignalType.NOISE,
                payload=None,
                heat_tax_incurred=0.0,  # Noise costs nothing
                metadata={
                    "noise_level": noise_level,
                    "filtered": True,
                    **(metadata or {})
                }
            )
            signals.append(noise_signal)
            self.state.total_signals_reverse += 1
            return signals

        # Layer 2: Pattern recognition — look for unconventional patterns
        patterns = self._pattern_recognizer.analyze(filtered)
        for pattern in patterns:
            pattern_type = pattern.get("type", "unknown")
            significance = pattern.get("significance", 0.0)

            if significance >= self.config.reverse_seed_threshold:
                # High significance unconventional pattern -> W_L seed candidate
                signal_type = SignalType.IMPREGNATION_SEED
                self.state.reverse_seed_count += 1
            elif significance >= self.config.reverse_noise_threshold:
                signal_type = SignalType.ANOMALY
            else:
                signal_type = SignalType.FEEDBACK

            signal = CouplerSignal(
                signal_id=f"REV-{self.state.total_signals_reverse:06d}",
                direction=ChannelDirection.REVERSE,
                signal_type=signal_type,
                payload=pattern,
                source_fidelity=1.0 - noise_level,
                output_fidelity=max(
                    self.config.min_fidelity,
                    0.95 - noise_level
                ),
                heat_tax_incurred=noise_level * 0.1,  # Reverse heat tax
                metadata={
                    "noise_level": noise_level,
                    "pattern_type": pattern_type,
                    "is_impregnation_seed": signal_type == SignalType.IMPREGNATION_SEED,
                    **(metadata or {})
                }
            )
            signals.append(signal)
            self.state.total_signals_reverse += 1
            self.state.cumulative_heat_tax += signal.heat_tax_incurred
            self._heat_tax_auditor.record(signal.heat_tax_incurred)

        return signals

    def get_health_report(self) -> Dict:
        """Generate a health report for the coupler"""
        avg_forward_fidelity = (
            sum(self.state.forward_fidelity_history) /
            len(self.state.forward_fidelity_history)
            if self.state.forward_fidelity_history else 1.0
        )

        heat_tax_status = self._heat_tax_auditor.get_status()

        return {
            "forward_channel": {
                "total_signals": self.state.total_signals_forward,
                "avg_fidelity": avg_forward_fidelity,
                "fidelity_target": self.config.forward_fidelity_target,
                "target_met": avg_forward_fidelity >= self.config.forward_fidelity_target
            },
            "reverse_channel": {
                "total_signals": self.state.total_signals_reverse,
                "impregnation_seeds": self.state.reverse_seed_count,
                "seed_extraction_rate": (
                    self.state.reverse_seed_count / self.state.total_signals_reverse
                    if self.state.total_signals_reverse > 0 else 0
                )
            },
            "heat_tax": {
                "cumulative": self.state.cumulative_heat_tax,
                "budget": self.config.heat_tax_budget,
                "within_budget": self.state.cumulative_heat_tax <= self.config.heat_tax_budget,
                "audit_status": heat_tax_status
            }
        }

    def generate_report(self) -> str:
        """Generate a human-readable health report"""
        health = self.get_health_report()
        fwd = health["forward_channel"]
        rev = health["reverse_channel"]
        ht = health["heat_tax"]

        seed_rate_pct = rev["seed_extraction_rate"] * 100

        # Interpreting seed extraction rate
        if seed_rate_pct > 10:
            seed_interpretation = "HIGH — system is in a period of rich discovery"
        elif seed_rate_pct > 3:
            seed_interpretation = "MODERATE — healthy innovation rate"
        else:
            seed_interpretation = "LOW — stable, but monitor for stagnation"

        return f"""
{'=' * 60}
K4 BIDIRECTIONAL COUPLER — HEALTH REPORT
{'=' * 60}

[FORWARD CHANNEL]  L1 -> L0
  Total Signals:       {fwd['total_signals']}
  Avg Fidelity:        {fwd['avg_fidelity']:.4f}  (target: {fwd['fidelity_target']})
  Fidelity Target Met: {'YES' if fwd['target_met'] else 'NO — re-anchoring required'}

[REVERSE CHANNEL]  L0 -> L1
  Total Signals:       {rev['total_signals']}
  Impregnation Seeds:  {rev['impregnation_seeds']}
  Seed Extraction Rate: {seed_rate_pct:.1f}%  ({seed_interpretation})

[HEAT TAX AUDIT]
  Cumulative Heat Tax: {ht['cumulative']:.4f}
  Budget:              {ht['budget']:.4f}
  Within Budget:       {'YES' if ht['within_budget'] else 'OVER BUDGET — emergency audit required'}
  Audit Status:        {ht['audit_status']}

[ENGINEERING NOTE]
  Heat tax MINIMUM exists (not eliminable):
    gamma_min = gamma_forward + gamma_reverse
  Current gamma_actual = {ht['cumulative']:.4f}
  Goal: gamma_actual ~ gamma_min through fine-grained management
{'=' * 60}
""".strip()


# ===== Internal Components =====

class NoiseFilter:
    """Layer 1: Filter pure random noise from L0 feedback"""

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold

    def process(self, feedback: Any) -> Tuple[Any, float]:
        """Process feedback and return (filtered_data, noise_level).

        noise_level: 0.0 = pure signal, 1.0 = pure noise
        """
        if feedback is None:
            return None, 1.0

        if isinstance(feedback, (int, float)):
            # Simple case: check if the value is near zero (noise floor)
            noise_level = max(0.0, 1.0 - abs(feedback) * 10) if abs(feedback) < 0.1 else 0.0
            return feedback, noise_level

        if isinstance(feedback, str):
            # Text feedback: check for gibberish patterns
            if len(feedback) < 3:
                return feedback, 0.8
            # Simple heuristic: ratio of repeated characters
            unique_ratio = len(set(feedback)) / len(feedback) if feedback else 0
            noise_level = max(0.0, 1.0 - unique_ratio * 2)
            return feedback, noise_level

        # Default: assume moderate noise
        return feedback, 0.2


class PatternRecognizer:
    """Layer 2: Identify unconventional patterns in filtered L0 feedback"""

    def __init__(self, seed_threshold: float = 0.7):
        self.seed_threshold = seed_threshold

    def analyze(self, data: Any) -> List[Dict]:
        """Analyze filtered data for unconventional patterns.

        Returns list of pattern dictionaries with 'type' and 'significance'.
        Significance >= seed_threshold means this is a W_L candidate.
        """
        patterns = []

        if data is None:
            return patterns

        if isinstance(data, str):
            # Check for logical paradox patterns
            paradox_indicators = ["but", "however", "yet", "contradiction",
                                   "paradox", "can't", "cannot", "impossible"]
            score = sum(1 for ind in paradox_indicators
                       if ind in data.lower()) / len(paradox_indicators)

            if score > 0.2:
                patterns.append({
                    "type": "paradoxical_pattern",
                    "significance": min(0.95, score * 2),
                    "data": data
                })

            # Check for novel concept patterns (unusual word combinations)
            words = data.lower().split()
            if len(words) > 5:
                avg_word_len = sum(len(w) for w in words) / len(words)
                if avg_word_len > 7:  # Unusually long words = specialized terminology
                    patterns.append({
                        "type": "novel_terminology",
                        "significance": min(0.8, avg_word_len / 15),
                        "data": data
                    })

        if isinstance(data, (list, tuple)):
            # Check for structural anomalies (e.g., sequence anomalies)
            if len(data) > 3:
                # Simple outlier detection using IQR
                numeric = [x for x in data if isinstance(x, (int, float))]
                if len(numeric) > 3:
                    sorted_nums = sorted(numeric)
                    q1 = sorted_nums[len(sorted_nums) // 4]
                    q3 = sorted_nums[3 * len(sorted_nums) // 4]
                    iqr = q3 - q1
                    outliers = [x for x in numeric
                               if x < q1 - 1.5 * iqr or x > q3 + 1.5 * iqr]
                    if outliers:
                        patterns.append({
                            "type": "structural_anomaly",
                            "significance": min(0.9, len(outliers) / len(numeric) * 2),
                            "data": {"outliers": outliers, "iqr": iqr}
                        })

        return patterns


class MeaningAnchor:
    """Encodes L1 meaning into L0-executable form with fidelity tracking"""

    def __init__(self, fidelity_target: float = 0.95):
        self.fidelity_target = fidelity_target

    def encode(self, meaning: Any) -> Tuple[Any, float]:
        """Encode meaning with fidelity assessment.

        Returns: (encoded_meaning, encoding_fidelity)
        """
        if meaning is None:
            return None, 0.0

        # String encoding: assess fidelity by structural preservation
        if isinstance(meaning, str):
            # Longer meanings have more opportunity for information loss
            fidelity = max(0.75, 1.0 - len(meaning) * 0.0005)
            # Shorter, well-structured meanings encode better
            if len(meaning) < 100:
                fidelity = max(fidelity, 0.95)
            return meaning, fidelity

        # Numeric encoding: very high fidelity
        if isinstance(meaning, (int, float, bool)):
            return meaning, 0.99

        # Dict/List: moderate fidelity
        if isinstance(meaning, (dict, list)):
            return meaning, 0.90

        # Default
        return meaning, 0.85


class HeatTaxAuditor:
    """Monitors cumulative heat tax against budget"""

    def __init__(self, budget: float = 0.10, window_size: int = 100):
        self.budget = budget
        self.window_size = window_size
        self.recent_heat_tax: List[float] = []
        self.total_signals: int = 0

    def record(self, heat_tax: float):
        """Record heat tax from a single signal"""
        self.recent_heat_tax.append(heat_tax)
        self.total_signals += 1
        if len(self.recent_heat_tax) > self.window_size * 2:
            self.recent_heat_tax = self.recent_heat_tax[-self.window_size:]

    def get_status(self) -> Dict:
        """Get current heat tax audit status"""
        if not self.recent_heat_tax:
            return {"status": "NO_DATA", "avg_heat_tax": 0.0}

        window = self.recent_heat_tax[-self.window_size:]
        avg_ht = sum(window) / len(window)

        if avg_ht > self.budget * 1.5:
            status = "CRITICAL_OVER_BUDGET"
        elif avg_ht > self.budget:
            status = "OVER_BUDGET"
        elif avg_ht > self.budget * 0.8:
            status = "APPROACHING_BUDGET"
        else:
            status = "WITHIN_BUDGET"

        return {
            "status": status,
            "avg_heat_tax": avg_ht,
            "budget": self.budget,
            "window_size": len(window)
        }


# ===== Self-Test =====
if __name__ == "__main__":
    coupler = K4BidirectionalCoupler()

    print("=== K4 Bidirectional Coupler — Self-Test ===\n")

    # Test forward channel
    print("[Forward Channel] L1 -> L0")
    test_meanings = [
        "Establish normative field anchor at coordinates (x=0, y=0)",
        "Execute meaning density scan with radius 10",
        "Deploy paradox firewall at interface boundary",
        "AAAA",  # Very short (lower fidelity)
        "A" * 500,  # Very long (lower fidelity)
    ]

    for meaning in test_meanings:
        signal = coupler.forward_channel(
            meaning,
            SignalType.INSTRUCTION,
            {"priority": "high"}
        )
        print(f"  Signal {signal.signal_id}: "
              f"fidelity={signal.output_fidelity:.4f}, "
              f"heat_tax={signal.heat_tax_incurred:.4f}")

    # Test reverse channel
    print("\n[Reverse Channel] L0 -> L1")
    test_feedbacks = [
        "System response: but the anchor point shifted unexpectedly",  # Anomaly
        "a" * 3,  # Noise
        "Quantum decoherence pattern detected: non-random polarization at 2.73K",  # Seed candidate
        0.001,  # Near-zero noise
        0.95,  # Strong signal
        ["normal", "normal", "normal", 9999.0, "normal"],  # Outlier
    ]

    for feedback in test_feedbacks:
        signals = coupler.reverse_channel(feedback)
        for sig in signals:
            print(f"  Signal {sig.signal_id}: "
                  f"type={sig.signal_type.value}, "
                  f"heat_tax={sig.heat_tax_incurred:.4f}")
            if sig.signal_type == SignalType.IMPREGNATION_SEED:
                print(f"    *** W_L SEED CANDIDATE DETECTED ***")

    # Full report
    print("\n" + coupler.generate_report())

    print(f"\n  Total forward signals: {coupler.state.total_signals_forward}")
    print(f"  Total reverse signals: {coupler.state.total_signals_reverse}")
    print(f"  Impregnation seeds: {coupler.state.reverse_seed_count}")
    print("=== Test Complete ===")