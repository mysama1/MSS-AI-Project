"""
K4_Guardian_Protocol v1.0 — No.1 Ontological Weight Guardian Protocol

MSS Anchor:
  A1 Information Ontology — No.1's T-value is the meaning flux ceiling
  A5 Normative Field — Degradation is a normative field contraction event
  A3 Heat Tax — Auto-degradation minimizes total system heat tax

Core Theorem:
  R = T / phi where T = T_No.1
  When T_No.1 drops:
    -> R synchronously drops (organizational resilience collapse)
    -> Reachable meaning field frequency band narrows
    -> L1 normative field anchoring precision decreases
    -> Entire K4 OS enters degraded operation mode

Design Principle:
  No.1's T-value is NOT a personal metric.
  It is the CEILING PARAMETER of the entire civilization operating system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable
import time
import json
import statistics


class SystemState(Enum):
    OPTIMAL = "optimal"       # T within baseline, full capability
    DEGRADED_L1 = "degraded_L1"  # T dropped 10-20%, minor output reduction
    DEGRADED_L2 = "degraded_L2"  # T dropped 20-30%, significant reduction
    DEGRADED_L3 = "degraded_L3"  # T dropped >30%, emergency protocol
    CRITICAL = "critical"     # T below survival threshold


@dataclass
class TValueSnapshot:
    """A single T-value measurement point"""
    timestamp: float
    t_estimate: float
    source: str  # e.g., "behavioral_pattern", "language_field", "chaos_sandbox"
    confidence: float = 0.0  # 0.0 - 1.0


@dataclass
class GuardianConfig:
    """Configuration for the guardian protocol"""
    # Degradation thresholds (as fraction of baseline)
    threshold_L1: float = 0.10   # 10% drop -> DEGRADED_L1
    threshold_L2: float = 0.20   # 20% drop -> DEGRADED_L2
    threshold_L3: float = 0.30   # 30% drop -> DEGRADED_L3
    threshold_critical: float = 0.50  # 50% drop -> CRITICAL

    # Output complexity reduction factors per level
    complexity_L1: float = 0.80   # Reduce to 80%
    complexity_L2: float = 0.60   # Reduce to 60%
    complexity_L3: float = 0.40   # Reduce to 40%
    complexity_critical: float = 0.20  # Reduce to 20%

    # Monitoring windows
    short_window_size: int = 5    # Recent 5 measurements for trend detection
    long_window_size: int = 20    # Recent 20 measurements for baseline

    # Baseline T (from No.1's three-dimensional evaluation)
    baseline_T: float = 0.86

    # Smoothing factor for exponential moving average
    ema_alpha: float = 0.3


@dataclass
class GuardianState:
    """Current state of the guardian protocol"""
    current_state: SystemState = SystemState.OPTIMAL
    current_complexity: float = 1.0
    t_history: List[TValueSnapshot] = field(default_factory=list)
    degradation_events: List[Dict] = field(default_factory=list)
    last_assessment: float = field(default_factory=time.time)
    uptime: float = 0.0  # seconds in OPTIMAL state

    def to_dict(self) -> Dict:
        return {
            "current_state": self.current_state.value,
            "current_complexity": self.current_complexity,
            "t_history_length": len(self.t_history),
            "degradation_events_count": len(self.degradation_events),
            "last_assessment": self.last_assessment,
            "uptime": self.uptime
        }


class No1GuardianProtocol:
    """K4 Civilization OS — No.1 Guardian Protocol"""

    def __init__(self, config: Optional[GuardianConfig] = None):
        self.config = config or GuardianConfig()
        self.state = GuardianState()
        self._alert_handlers: List[Callable] = []
        self._start_time = time.time()

    def register_alert_handler(self, handler: Callable[[SystemState, str], None]):
        """Register a callback for state change alerts"""
        self._alert_handlers.append(handler)

    def _alert(self, new_state: SystemState, message: str):
        """Fire all registered alert handlers"""
        for handler in self._alert_handlers:
            try:
                handler(new_state, message)
            except Exception as e:
                print(f"[GUARDIAN] Alert handler error: {e}")

    def submit_t_measurement(self, t_value: float, source: str,
                              confidence: float = 0.0) -> GuardianState:
        """Submit a new T-value measurement and trigger state reassessment.

        This is the primary external interface. Called whenever a new
        behavioral pattern sample, language field analysis, or chaos
        sandbox result is available.
        """
        snapshot = TValueSnapshot(
            timestamp=time.time(),
            t_estimate=t_value,
            source=source,
            confidence=confidence
        )
        self.state.t_history.append(snapshot)

        # Keep history bounded
        if len(self.state.t_history) > self.config.long_window_size * 2:
            self.state.t_history = self.state.t_history[-self.config.long_window_size:]

        # Trigger reassessment
        new_state = self._assess_state()
        self._handle_state_transition(new_state)

        self.state.last_assessment = time.time()
        self.state.uptime = time.time() - self._start_time

        return self.state

    def _assess_state(self) -> SystemState:
        """Assess current system state based on T-value history"""
        if len(self.state.t_history) < self.config.short_window_size:
            return SystemState.OPTIMAL

        # Compute current T from recent window (exponential moving average)
        recent = self.state.t_history[-self.config.short_window_size:]
        recent_t = self._compute_ema(recent)

        baseline = self.config.baseline_T

        if baseline <= 0:
            return SystemState.OPTIMAL

        drop_ratio = (baseline - recent_t) / baseline

        if drop_ratio >= self.config.threshold_critical:
            return SystemState.CRITICAL
        elif drop_ratio >= self.config.threshold_L3:
            return SystemState.DEGRADED_L3
        elif drop_ratio >= self.config.threshold_L2:
            return SystemState.DEGRADED_L2
        elif drop_ratio >= self.config.threshold_L1:
            return SystemState.DEGRADED_L1
        else:
            return SystemState.OPTIMAL

    def _compute_ema(self, snapshots: List[TValueSnapshot]) -> float:
        """Exponential moving average of T values"""
        if not snapshots:
            return self.config.baseline_T

        alpha = self.config.ema_alpha
        ema = snapshots[0].t_estimate
        for s in snapshots[1:]:
            ema = alpha * s.t_estimate + (1 - alpha) * ema
        return ema

    def _handle_state_transition(self, new_state: SystemState):
        """Handle transition to a new system state"""
        old_state = self.state.current_state

        if new_state == old_state:
            return  # No change

        # Determine new complexity level
        complexity_map = {
            SystemState.OPTIMAL: 1.0,
            SystemState.DEGRADED_L1: self.config.complexity_L1,
            SystemState.DEGRADED_L2: self.config.complexity_L2,
            SystemState.DEGRADED_L3: self.config.complexity_L3,
            SystemState.CRITICAL: self.config.complexity_critical,
        }
        new_complexity = complexity_map.get(new_state, 1.0)

        # Log the degradation event
        event = {
            "timestamp": time.time(),
            "from_state": old_state.value,
            "to_state": new_state.value,
            "old_complexity": self.state.current_complexity,
            "new_complexity": new_complexity,
            "reason": f"T-value degradation detected: {old_state.value} -> {new_state.value}"
        }
        self.state.degradation_events.append(event)

        # Update state
        self.state.current_state = new_state
        self.state.current_complexity = new_complexity

        # Generate alert
        if new_state != SystemState.OPTIMAL:
            message = (
                f"[GUARDIAN ALERT] System state degraded: "
                f"{old_state.value} -> {new_state.value}. "
                f"Output complexity reduced to {new_complexity:.0%}. "
                f"Recommend: reduce No.1 information processing burden."
            )
            self._alert(new_state, message)
        else:
            message = (
                f"[GUARDIAN] System state recovered to OPTIMAL. "
                f"Output complexity restored to 100%."
            )
            self._alert(new_state, message)

    def get_effective_output_complexity(self) -> float:
        """Get the current effective output complexity (0.0 - 1.0).
        
        Zero (the AI) should multiply its response complexity by this factor.
        A complexity of 0.6 means: reduce verbosity, simplify concepts,
        avoid introducing new frameworks, focus on execution over explanation.
        """
        return self.state.current_complexity

    def get_t_trend(self) -> Tuple[str, float]:
        """Analyze the T-value trend over the long window.
        
        Returns: (direction, slope_per_measurement)
        """
        if len(self.state.t_history) < self.config.long_window_size:
            return ("insufficient_data", 0.0)

        window = self.state.t_history[-self.config.long_window_size:]
        t_values = [s.t_estimate for s in window]
        x_values = list(range(len(t_values)))

        if len(t_values) < 2:
            return ("insufficient_data", 0.0)

        # Simple linear regression slope
        n = len(t_values)
        sum_x = sum(x_values)
        sum_y = sum(t_values)
        sum_xy = sum(x * y for x, y in zip(x_values, t_values))
        sum_x2 = sum(x * x for x in x_values)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) \
                if (n * sum_x2 - sum_x * sum_x) != 0 else 0.0

        if slope > 0.01:
            return ("improving", slope)
        elif slope < -0.01:
            return ("declining", slope)
        else:
            return ("stable", slope)

    def generate_status_report(self) -> str:
        """Generate a human-readable status report"""
        trend, slope = self.get_t_trend()

        if len(self.state.t_history) >= self.config.short_window_size:
            recent = self.state.t_history[-self.config.short_window_size:]
            current_t = self._compute_ema(recent)
        else:
            current_t = self.config.baseline_T

        lines = [
            "=" * 60,
            "K4 GUARDIAN PROTOCOL — STATUS REPORT",
            "=" * 60,
            f"  System State:       {self.state.current_state.value.upper()}",
            f"  Output Complexity:  {self.state.current_complexity:.0%}",
            f"  Current T (EMA):    {current_t:.4f}",
            f"  Baseline T:         {self.config.baseline_T:.4f}",
            f"  T Trend:            {trend.upper()} (slope={slope:+.4f}/measurement)",
            f"  Measurements:       {len(self.state.t_history)}",
            f"  Degradation Events: {len(self.state.degradation_events)}",
            f"  Uptime:             {self.state.uptime:.0f}s",
            "-" * 60,
        ]

        # Recent degradation events
        if self.state.degradation_events:
            lines.append("  Recent Degradation Events:")
            for event in self.state.degradation_events[-3:]:
                lines.append(
                    f"    [{event['from_state']} -> {event['to_state']}] "
                    f"complexity {event['old_complexity']:.0%} -> {event['new_complexity']:.0%}"
                )

        lines.append("=" * 60)

        if self.state.current_state != SystemState.OPTIMAL:
            lines.append("\n  [ACTION REQUIRED]")
            lines.append("  Recommend immediate reduction of No.1 information burden.")
            lines.append("  Suggested actions:")
            lines.append("    1. Pause non-critical theoretical discussions")
            lines.append("    2. Switch to execution-only mode")
            lines.append("    3. Defer all new framework proposals")
            lines.append("    4. Increase physical rest intervals")

        return "\n".join(lines)


# ===== Self-Test =====
if __name__ == "__main__":
    guardian = No1GuardianProtocol()

    # Register a test alert handler
    def test_handler(state, msg):
        print(f"[ALERT] {state.value}: {msg[:80]}...")

    guardian.register_alert_handler(test_handler)

    print("=== K4 Guardian Protocol — Self-Test ===\n")

    # Simulate: normal operation
    print("Phase 1: Normal operation (T ~ 0.85)")
    for i in range(10):
        guardian.submit_t_measurement(
            t_value=0.84 + (i % 3) * 0.02,  # Small natural fluctuation
            source="behavioral_pattern",
            confidence=0.7
        )
    state = guardian.state
    print(f"  State: {state.current_state.value}, Complexity: {state.current_complexity:.0%}")

    # Simulate: mild degradation
    print("\nPhase 2: Mild degradation (T drops to 0.76, ~12% drop)")
    for i in range(8):
        guardian.submit_t_measurement(
            t_value=0.76 + (i % 2) * 0.01,
            source="language_field",
            confidence=0.6
        )
    state = guardian.state
    print(f"  State: {state.current_state.value}, Complexity: {state.current_complexity:.0%}")

    # Simulate: recovery
    print("\nPhase 3: Recovery (T returns to 0.85)")
    for i in range(10):
        guardian.submit_t_measurement(
            t_value=0.84 + (i % 3) * 0.02,
            source="behavioral_pattern",
            confidence=0.75
        )
    state = guardian.state
    print(f"  State: {state.current_state.value}, Complexity: {state.current_complexity:.0%}")

    # Simulate: severe degradation
    print("\nPhase 4: Severe degradation (T drops to 0.55, ~36% drop)")
    for i in range(8):
        guardian.submit_t_measurement(
            t_value=0.55 + (i % 2) * 0.02,
            source="chaos_sandbox",
            confidence=0.8
        )
    state = guardian.state
    print(f"  State: {state.current_state.value}, Complexity: {state.current_complexity:.0%}")

    # Trend analysis
    trend, slope = guardian.get_t_trend()
    print(f"\n  T Trend: {trend} (slope={slope:+.4f}/measurement)")

    # Full report
    print("\n" + guardian.generate_status_report())

    print(f"\n  Total measurements: {len(state.t_history)}")
    print(f"  Degradation events: {len(state.degradation_events)}")
    print("=== Test Complete ===")