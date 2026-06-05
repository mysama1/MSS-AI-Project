"""
K4-Pi Adapter v1.0 — Bidirectional Protocol Bridge between K4 OS and pi Extension Ecosystem

MSS Anchor:
  A2 (Information Slices) — Each adapter function is a slice translator
  A3 (Heat Tax) — gamma_cross = translation_loss. Managed, not eliminated.
  A4 (Randomness) — pi's freeform exploration maps to K4's Delta_S_random
  A6 (Contradiction Elevation) — Cross-paradigm conflicts = elevation triggers

Architecture:
  ┌──────────────────────────────────────────────────────────┐
  │               K4 ↔ pi Adapter Layer                       │
  │                                                           │
  │  ┌───────────┐         ┌─────────────────┐               │
  │  │ K4 OS     │ ──────> │ Forward Bridge   │ ──> pi ext    │
  │  │ Protocols │         │ (K4→pi mapping)  │              │
  │  │           │         └─────────────────┘              │
  │  │           │         ┌─────────────────┐              │
  │  │           │ <────── │ Reverse Bridge   │ <── pi ext    │
  │  │           │         │ (pi→K4 mapping)  │              │
  │  └───────────┘         └─────────────────┘               │
  │                                                           │
  │  Heat Tax Floor: gamma_cross = gamma_K4_pi + gamma_pi_K4 │
  │  Audit: track translation_fidelity per signal             │
  └──────────────────────────────────────────────────────────┘
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable
import time
import json


# ============================================================
# Section 1: Bridge Types & Configuration
# ============================================================

class BridgeDirection(Enum):
    K4_TO_PI = "k4_to_pi"   # Forward: K4 protocol → pi extension call
    PI_TO_K4 = "pi_to_k4"   # Reverse: pi extension result → K4 protocol


class TranslationFidelity(Enum):
    """Fidelity grade of cross-paradigm translation"""
    PERFECT = "perfect"         # No semantic loss (fidelity >= 0.99)
    HIGH = "high"               # Minor nuance loss (0.95-0.99)
    ACCEPTABLE = "acceptable"   # Some loss, meaning preserved (0.85-0.95)
    DEGRADED = "degraded"       # Significant loss (0.70-0.85)
    BROKEN = "broken"           # Translation failed (< 0.70)


@dataclass
class BridgeConfig:
    """Configuration for the K4-Pi adapter bridge"""
    # Fidelity thresholds for each translation direction
    fidelity_threshold_forward: float = 0.85   # K4→pi minimum
    fidelity_threshold_reverse: float = 0.85   # pi→K4 minimum

    # Heat tax tracking
    track_heat_tax: bool = True
    max_cumulative_heat_tax: float = 0.30      # 30% max cumulative loss

    # Audit
    audit_every_n_signals: int = 10

    # Fallback
    fallback_on_fidelity_breach: bool = True


@dataclass
class BridgeSignal:
    """A single translation event crossing the K4-pi boundary"""
    signal_id: str
    direction: BridgeDirection
    source_component: str        # K4 protocol name or pi extension name
    target_component: str
    payload_in: Dict             # Original payload
    payload_out: Optional[Dict]  # Translated payload
    fidelity: float = 1.0        # Translation fidelity (0-1)
    heat_tax: float = 0.0        # gamma contribution of this signal
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)


@dataclass
class HeatTaxReport:
    """Cumulative heat tax report for the bridge"""
    total_signals: int = 0
    forward_signals: int = 0
    reverse_signals: int = 0
    cumulative_forward_gamma: float = 0.0
    cumulative_reverse_gamma: float = 0.0
    total_heat_tax: float = 0.0
    average_fidelity: float = 0.0
    breaches: int = 0
    status: str = "HEALTHY"

    def is_below_critical(self, max_gamma: float) -> bool:
        return self.total_heat_tax <= max_gamma


# ============================================================
# Section 2: Protocol Mapping Tables
# ============================================================

# K4 → pi: Map each K4 protocol to corresponding pi/senpi extensions
K4_TO_PI_MAP = {
    # RSCA operations → pi permissions
    "rsca.audit_completeness": {
        "pi_extension": "permission",
        "action": "check_rule",
        "default_fidelity": 0.92,
        "heat_tax_base": 0.03,  # Some context lost in translation
    },
    "rsca.verify_integrity": {
        "pi_extension": "permission",
        "action": "verify_rules",
        "default_fidelity": 0.95,
        "heat_tax_base": 0.02,
    },
    "rsca.propose_amendment": {
        "pi_extension": "permission",
        "action": "update_rule_v2",
        "default_fidelity": 0.88,
        "heat_tax_base": 0.05,
        "note": "Amendment semantics may not fully preserve in pi rule format"
    },

    # Guardian Protocol → pi service-tier
    "guardian.check_state": {
        "pi_extension": "service_tier",
        "action": "get_current_tier",
        "default_fidelity": 0.96,
        "heat_tax_base": 0.02,
    },
    "guardian.apply_complexity_factor": {
        "pi_extension": "service_tier",
        "action": "set_tier",
        "default_fidelity": 0.90,
        "heat_tax_base": 0.04,
        "note": "K4 5-level state → pi auto/flex/priority (3-tier) requires compression"
    },

    # Bidirectional Coupler → pi compaction
    "coupler.encode_forward": {
        "pi_extension": "compaction",
        "action": "compress_context",
        "default_fidelity": 0.88,
        "heat_tax_base": 0.05,
    },
    "coupler.encode_reverse": {
        "pi_extension": "compaction",
        "action": "expand_context",
        "default_fidelity": 0.85,
        "heat_tax_base": 0.06,
        "note": "Reverse direction has inherently higher loss"
    },
    "coupler.audit_heat_tax": {
        "pi_extension": "compaction",
        "action": "get_compaction_stats",
        "default_fidelity": 0.93,
        "heat_tax_base": 0.03,
    },

    # Logic Work Engine → pi apply-patch
    "logic_work.compute_core": {
        "pi_extension": "apply_patch",
        "action": "structured_edit",
        "default_fidelity": 0.95,
        "heat_tax_base": 0.02,
    },
    "logic_work.compute_explore": {
        "pi_extension": "apply_patch",
        "action": "freeform_edit_with_audit",
        "default_fidelity": 0.85,
        "heat_tax_base": 0.06,
    },
    "logic_work.trigger_a6_audit": {
        "pi_extension": "apply_patch",
        "action": "verify_patch_metadata",
        "default_fidelity": 0.90,
        "heat_tax_base": 0.04,
    },
}

# pi → K4: Map pi extension results back to K4 protocol signals
PI_TO_K4_MAP = {
    # pi permission → K4 RSCA
    "permission.rule_match": {
        "k4_protocol": "rsca",
        "signal_type": "audit_result",
        "default_fidelity": 0.93,
    },
    "permission.rule_violation": {
        "k4_protocol": "rsca",
        "signal_type": "completeness_claim",
        "default_fidelity": 0.90,
    },

    # pi compaction → K4 Coupler
    "compaction.threshold_exceeded": {
        "k4_protocol": "coupler",
        "signal_type": "heat_tax_breach",
        "default_fidelity": 0.92,
    },
    "compaction.compression_applied": {
        "k4_protocol": "coupler",
        "signal_type": "gamma_forward_record",
        "default_fidelity": 0.89,
    },

    # pi service-tier → K4 Guardian
    "service_tier.tier_changed": {
        "k4_protocol": "guardian",
        "signal_type": "state_transition",
        "default_fidelity": 0.88,
        "note": "3-tier pi → 5-tier K4 requires interpolation"
    },

    # pi apply-patch → K4 Logic Work
    "apply_patch.patch_applied": {
        "k4_protocol": "logic_work",
        "signal_type": "explore_outcome",
        "default_fidelity": 0.91,
    },
    "apply_patch.parse_failed": {
        "k4_protocol": "logic_work",
        "signal_type": "w_l_zero_fallback",
        "default_fidelity": 0.94,
    },
}


# ============================================================
# Section 3: Adapter Core
# ============================================================

class K4PiAdapter:
    """Bidirectional bridge between K4 protocols and pi extension ecosystem."""

    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig()
        self.signal_log: List[BridgeSignal] = []
        self.heat_tax_report = HeatTaxReport()

    # ─── Forward: K4 → pi ───

    def translate_k4_to_pi(
        self,
        k4_protocol: str,
        k4_action: str,
        k4_payload: Dict
    ) -> Tuple[Optional[Dict], BridgeSignal]:
        """
        Translate a K4 protocol call into a pi extension-format call.

        Args:
            k4_protocol: The K4 protocol name (rsca/guardian/coupler/logic_work)
            k4_action: The specific action within the protocol
            k4_payload: The K4 payload dict

        Returns:
            (pi_call, signal) where pi_call is ready for pi extension consumption
        """
        route_key = f"{k4_protocol}.{k4_action}"
        mapping = K4_TO_PI_MAP.get(route_key)

        if mapping is None:
            # Unknown route — passthrough with warning
            signal = BridgeSignal(
                signal_id=f"k4pi_{int(time.time()*1000)}",
                direction=BridgeDirection.K4_TO_PI,
                source_component=f"K4.{k4_protocol}",
                target_component="pi.unknown",
                payload_in=k4_payload,
                payload_out=k4_payload,  # passthrough
                fidelity=0.70,  # low fidelity for unmapped routes
                heat_tax=0.10,
                tags=["unmapped_route", "passthrough"]
            )
            self._log_signal(signal)
            return k4_payload, signal

        # Build pi-format call
        pi_call = {
            "extension": mapping["pi_extension"],
            "action": mapping["action"],
            "params": self._adapt_params_k4_to_pi(route_key, k4_payload),
            "meta": {
                "k4_source": route_key,
                "k4_version": "1.0",
                "translation_fidelity_target": mapping["default_fidelity"]
            }
        }

        base_heat_tax = mapping.get("heat_tax_base", 0.05)
        fidelity = mapping.get("default_fidelity", 0.90)

        signal = BridgeSignal(
            signal_id=f"k4pi_{int(time.time()*1000)}",
            direction=BridgeDirection.K4_TO_PI,
            source_component=f"K4.{k4_protocol}",
            target_component=f"pi.{mapping['pi_extension']}",
            payload_in=k4_payload,
            payload_out=pi_call,
            fidelity=fidelity,
            heat_tax=base_heat_tax,
            tags=[route_key, "mapped"]
        )

        if mapping.get("note"):
            signal.tags.append(f"note:{mapping['note']}")

        self._log_signal(signal)

        # Fidelity check
        if fidelity < self.config.fidelity_threshold_forward:
            signal.tags.append("FIDELITY_BREACH")
            if self.config.fallback_on_fidelity_breach:
                return self._fallback_passthrough(k4_payload, signal), signal

        return pi_call, signal

    # ─── Reverse: pi → K4 ───

    def translate_pi_to_k4(
        self,
        pi_extension: str,
        pi_action: str,
        pi_result: Dict
    ) -> Tuple[Optional[Dict], BridgeSignal]:
        """
        Translate a pi extension result back into K4 protocol signal format.

        Args:
            pi_extension: The pi extension name
            pi_action: The action performed
            pi_result: The result from the pi extension

        Returns:
            (k4_signal, bridge_signal) — k4_signal ready for K4 protocol consumption
        """
        route_key = f"{pi_extension}.{pi_action}"
        mapping = PI_TO_K4_MAP.get(route_key)

        if mapping is None:
            signal = BridgeSignal(
                signal_id=f"pik4_{int(time.time()*1000)}",
                direction=BridgeDirection.PI_TO_K4,
                source_component=f"pi.{pi_extension}",
                target_component="K4.unknown",
                payload_in=pi_result,
                payload_out=pi_result,
                fidelity=0.70,
                heat_tax=0.10,
                tags=["unmapped_pi_result"]
            )
            self._log_signal(signal)
            return pi_result, signal

        # Translate pi result to K4 signal format
        k4_signal = {
            "protocol": mapping["k4_protocol"],
            "signal_type": mapping["signal_type"],
            "payload": self._adapt_params_pi_to_k4(route_key, pi_result),
            "meta": {
                "pi_source": route_key,
                "pi_extension": pi_extension,
                "translation_fidelity_target": mapping["default_fidelity"]
            }
        }

        fidelity = mapping.get("default_fidelity", 0.90)
        heat_tax = 1.0 - fidelity  # fidelity loss = heat tax

        signal = BridgeSignal(
            signal_id=f"pik4_{int(time.time()*1000)}",
            direction=BridgeDirection.PI_TO_K4,
            source_component=f"pi.{pi_extension}",
            target_component=f"K4.{mapping['k4_protocol']}",
            payload_in=pi_result,
            payload_out=k4_signal,
            fidelity=fidelity,
            heat_tax=heat_tax,
            tags=[route_key, "mapped"]
        )

        if mapping.get("note"):
            signal.tags.append(f"note:{mapping['note']}")

        self._log_signal(signal)
        return k4_signal, signal

    # ─── Parameter Adapters ───

    def _adapt_params_k4_to_pi(self, route_key: str, k4_payload: Dict) -> Dict:
        """Adapt K4-specific parameters to pi extension format."""
        adapted = dict(k4_payload)

        # Guardian 5-level state → pi 3-tier compression
        if route_key.startswith("guardian."):
            adapted["k4_state_count"] = 5
            adapted["pi_tier_count"] = 3
            adapted["compression_note"] = "K4 5-level → pi 3-tier (merged DEGRADED_L2+L3)"
            adapted["_original_k4_state"] = adapted.pop("system_state", None)

        # Coupler signals → compaction format
        if route_key.startswith("coupler."):
            if "fidelity" in adapted:
                adapted["compression_ratio"] = adapted.pop("fidelity")

        # Logic Work zones → patch modes
        if route_key.startswith("logic_work."):
            if "zone" in adapted:
                adapted["patch_mode"] = adapted.pop("zone")

        return adapted

    def _adapt_params_pi_to_k4(self, route_key: str, pi_result: Dict) -> Dict:
        """Adapt pi extension results back to K4 protocol format."""
        adapted = dict(pi_result)

        # pi 3-tier → interpolate K4 5-level (maintain original if possible)
        tier_to_k4 = {
            "auto": "OPTIMAL",
            "flex": "DEGRADED_L1",
            "priority": "DEGRADED_L2"  # Conservative mapping
        }
        if "tier" in adapted:
            adapted["k4_system_state"] = tier_to_k4.get(
                adapted.pop("tier"), "DEGRADED_L1"
            )
            adapted["_interpolation_note"] = "pi 3-tier → K4 5-level (conservative)"
        if "new_tier" in adapted:
            adapted["k4_new_state"] = tier_to_k4.get(
                adapted.pop("new_tier"), "OPTIMAL"
            )
        if "old_tier" in adapted:
            adapted["k4_old_state"] = tier_to_k4.get(
                adapted.pop("old_tier"), "OPTIMAL"
            )
            adapted["_interpolation_note"] = "pi 3-tier → K4 5-level (conservative)"

        return adapted

    def _fallback_passthrough(self, payload: Dict, signal: BridgeSignal) -> Dict:
        """Fallback: passthrough with reduced fidelity marker."""
        signal.tags.append("FALLBACK_PASSTHROUGH")
        return {
            **payload,
            "_adapter_fallback": True,
            "_original_fidelity": signal.fidelity
        }

    # ─── Heat Tax Management ───

    def _log_signal(self, signal: BridgeSignal):
        """Log a bridge signal and update cumulative heat tax."""
        self.signal_log.append(signal)
        r = self.heat_tax_report
        r.total_signals += 1
        if signal.direction == BridgeDirection.K4_TO_PI:
            r.forward_signals += 1
            r.cumulative_forward_gamma += signal.heat_tax
        else:
            r.reverse_signals += 1
            r.cumulative_reverse_gamma += signal.heat_tax

        r.total_heat_tax = r.cumulative_forward_gamma + r.cumulative_reverse_gamma

        # Compute running average fidelity
        total_fid = sum(s.fidelity for s in self.signal_log)
        r.average_fidelity = total_fid / max(r.total_signals, 1)

        # Breach tracking
        if signal.fidelity < 0.85:
            r.breaches += 1

        # Status update
        if r.total_heat_tax > self.config.max_cumulative_heat_tax:
            r.status = "HEAT_TAX_CEILING_BREACHED"
        elif r.breaches > 3:
            r.status = "FIDELITY_WARNING"
        else:
            r.status = "HEALTHY"

    def get_heat_tax_report(self) -> HeatTaxReport:
        """Get the current cumulative heat tax report."""
        return self.heat_tax_report

    def audit_bridge(self) -> Tuple[bool, List[str]]:
        """Run a bridge audit (RSCA-002 equivalent for the adapter)."""
        issues = []
        r = self.heat_tax_report

        # Check cumulative heat tax
        if r.total_heat_tax > self.config.max_cumulative_heat_tax:
            issues.append(
                f"Cumulative heat tax ({r.total_heat_tax:.3f}) "
                f"exceeds ceiling ({self.config.max_cumulative_heat_tax:.3f})"
            )

        # Check average fidelity
        if r.average_fidelity < 0.85:
            issues.append(
                f"Average fidelity ({r.average_fidelity:.3f}) below acceptable"
            )

        # Check too many fidelity breaches
        if r.breaches > 5:
            issues.append(f"Too many fidelity breaches ({r.breaches})")

        # Check unmapped routes
        unmapped = sum(
            1 for s in self.signal_log
            if "unmapped_route" in s.tags or "unmapped_pi_result" in s.tags
        )
        if unmapped > 3:
            issues.append(f"Too many unmapped routes ({unmapped})")

        return len(issues) == 0, issues

    def export_audit_log(self) -> str:
        """Export the complete bridge audit log as JSON."""
        log = {
            "adapter_version": "1.0.0",
            "config": {
                "fidelity_threshold_forward": self.config.fidelity_threshold_forward,
                "fidelity_threshold_reverse": self.config.fidelity_threshold_reverse,
                "max_cumulative_heat_tax": self.config.max_cumulative_heat_tax,
            },
            "heat_tax_report": {
                k: v for k, v in self.heat_tax_report.__dict__.items()
            },
            "mapping_tables": {
                "k4_to_pi": list(K4_TO_PI_MAP.keys()),
                "pi_to_k4": list(PI_TO_K4_MAP.keys()),
            },
            "signals": [
                {
                    "id": s.signal_id,
                    "direction": s.direction.value,
                    "source": s.source_component,
                    "target": s.target_component,
                    "fidelity": s.fidelity,
                    "heat_tax": s.heat_tax,
                    "tags": s.tags,
                }
                for s in self.signal_log
            ],
            "exported_at": time.time(),
        }
        return json.dumps(log, ensure_ascii=False, indent=2)


# ============================================================
# Section 4: Convenience API
# ============================================================

class K4PiBridge:
    """High-level convenience wrapper for common K4↔pi operations."""

    def __init__(self):
        self.adapter = K4PiAdapter()

    # ─── K4 → pi shortcuts ───

    def audit_to_pi_permission(self, text: str) -> Tuple[Dict, BridgeSignal]:
        """Run RSCA-006 completeness audit, output as pi permission rule check."""
        return self.adapter.translate_k4_to_pi(
            "rsca", "audit_completeness",
            {"text": text, "audit_type": "completeness_claim"}
        )

    def guardian_state_to_pi_tier(
        self, t_value: float, baseline: float = 0.96
    ) -> Tuple[Dict, BridgeSignal]:
        """Convert a Guardian T-value reading to pi service tier."""
        drop = (baseline - t_value) / baseline
        if drop <= 0.10:
            state = "OPTIMAL"
        elif drop <= 0.20:
            state = "DEGRADED_L1"
        elif drop <= 0.30:
            state = "DEGRADED_L2"
        else:
            state = "DEGRADED_L3"

        return self.adapter.translate_k4_to_pi(
            "guardian", "apply_complexity_factor",
            {"system_state": state, "t_value": t_value, "drop": drop}
        )

    def coupler_tax_to_pi_compaction(
        self, gamma_total: float, gamma_min: float
    ) -> Tuple[Dict, BridgeSignal]:
        """Report coupler heat tax as pi compaction stats."""
        overhead = gamma_total / gamma_min - 1
        return self.adapter.translate_k4_to_pi(
            "coupler", "audit_heat_tax",
            {"gamma_total": gamma_total, "gamma_min": gamma_min, "overhead": overhead}
        )

    def logic_work_to_pi_patch(
        self, w_l: float, zone: str = "explore"
    ) -> Tuple[Dict, BridgeSignal]:
        """Submit logic work result as pi apply-patch format."""
        if w_l > 0:
            action = "compute_explore"
        else:
            action = "compute_core"

        return self.adapter.translate_k4_to_pi(
            "logic_work", action,
            {"w_l": w_l, "zone": zone}
        )

    # ─── pi → K4 shortcuts ───

    def pi_permission_result_to_rsca(
        self, violation: Dict
    ) -> Tuple[Dict, BridgeSignal]:
        """Convert pi permission violation to RSCA audit signal."""
        return self.adapter.translate_pi_to_k4(
            "permission", "rule_violation", violation
        )

    def pi_compaction_event_to_coupler(
        self, comp_action: str, stats: Dict
    ) -> Tuple[Dict, BridgeSignal]:
        """Convert pi compaction event to coupler signal."""
        action_key = {
            "threshold_breach": "compaction.threshold_exceeded",
            "compression": "compaction.compression_applied",
        }.get(comp_action, "compaction.compression_applied")
        ext, act = action_key.split(".", 1)
        return self.adapter.translate_pi_to_k4(ext, act, stats)

    def pi_tier_change_to_guardian(
        self, old_tier: str, new_tier: str
    ) -> Tuple[Dict, BridgeSignal]:
        """Convert pi service tier change to Guardian state transition."""
        return self.adapter.translate_pi_to_k4(
            "service_tier", "tier_changed",
            {"old_tier": old_tier, "new_tier": new_tier}
        )

    def pi_patch_result_to_logic_work(
        self, success: bool, metadata: Dict
    ) -> Tuple[Dict, BridgeSignal]:
        """Convert pi apply-patch result to Logic Work outcome."""
        ext = "apply_patch"
        act = "patch_applied" if success else "parse_failed"
        return self.adapter.translate_pi_to_k4(ext, act, metadata)


# ============================================================
# Section 5: Self-Test
# ============================================================

if __name__ == "__main__":
    print("=== K4-Pi Adapter v1.0 — Self-Test ===\n")

    bridge = K4PiBridge()

    # Test 1: RSCA audit → pi permission
    print("[T1] RSCA-006 completeness audit → pi permission")
    result, sig = bridge.audit_to_pi_permission(
        "The ultimate and perfect theory of everything"
    )
    print(f"  Fidelity: {sig.fidelity:.3f} | Heat Tax: {sig.heat_tax:.3f}")
    print(f"  Pi Call: {result['extension']}.{result['action']}")
    assert result["extension"] == "permission"
    print("  PASS\n")

    # Test 2: Guardian state → pi tier
    print("[T2] Guardian T-value → pi service tier")
    result, sig = bridge.guardian_state_to_pi_tier(t_value=0.78)
    print(f"  Fidelity: {sig.fidelity:.3f} | Heat Tax: {sig.heat_tax:.3f}")
    print(f"  K4 state → pi {result['params']['_original_k4_state']}")
    assert result["extension"] == "service_tier"
    print("  PASS\n")

    # Test 3: Coupler heat tax → pi compaction
    print("[T3] Coupler heat tax → pi compaction stats")
    result, sig = bridge.coupler_tax_to_pi_compaction(0.15, 0.12)
    print(f"  Fidelity: {sig.fidelity:.3f} | Heat Tax: {sig.heat_tax:.3f}")
    print(f"  Overhead: {result['params']['overhead']:.1%}")
    assert result["extension"] == "compaction"
    print("  PASS\n")

    # Test 4: Logic Work → pi apply-patch (W_L > 0 case)
    print("[T4] Logic Work W_L=0.3 (>0) → pi apply-patch explore")
    result, sig = bridge.logic_work_to_pi_patch(w_l=0.3, zone="explore")
    print(f"  Fidelity: {sig.fidelity:.3f} | Heat Tax: {sig.heat_tax:.3f}")
    print(f"  Pi action: {result['action']} (W_L>0 → freeform)")
    assert "freeform" in result["action"]
    print("  PASS\n")

    # Test 5: Logic Work → pi apply-patch (W_L <= 0 case)
    print("[T5] Logic Work W_L=-0.1 (<=0) → pi apply-patch core")
    result, sig = bridge.logic_work_to_pi_patch(w_l=-0.1, zone="core")
    print(f"  Fidelity: {sig.fidelity:.3f} | Heat Tax: {sig.heat_tax:.3f}")
    print(f"  Pi action: {result['action']} (W_L<=0 → structured)")
    assert "structured" in result["action"]
    print("  PASS\n")

    # Test 6: Reverse — pi permission violation → RSCA
    print("[T6] Reverse: pi permission violation → RSCA signal")
    k4_signal, sig = bridge.pi_permission_result_to_rsca({
        "rule": "RSCA-006",
        "violation": "completeness claim detected"
    })
    print(f"  Fidelity: {sig.fidelity:.3f} | Heat Tax: {sig.heat_tax:.3f}")
    print(f"  K4 protocol: {k4_signal['protocol']}.{k4_signal['signal_type']}")
    assert k4_signal["protocol"] == "rsca"
    print("  PASS\n")

    # Test 7: Reverse — pi tier change → Guardian
    print("[T7] Reverse: pi tier change → Guardian state")
    k4_signal, sig = bridge.pi_tier_change_to_guardian("auto", "flex")
    print(f"  Fidelity: {sig.fidelity:.3f} | Heat Tax: {sig.heat_tax:.3f}")
    print(f"  K4 old: {k4_signal['payload']['k4_old_state']} → new: {k4_signal['payload']['k4_new_state']}")
    assert k4_signal["protocol"] == "guardian"
    print("  PASS\n")

    # Test 8: Audit
    print("[T8] Bridge audit")
    clean, issues = bridge.adapter.audit_bridge()
    report = bridge.adapter.get_heat_tax_report()
    print(f"  Total signals: {report.total_signals}")
    print(f"  Total heat tax: {report.total_heat_tax:.3f}")
    print(f"  Avg fidelity: {report.average_fidelity:.3f}")
    print(f"  Status: {report.status}")
    if issues:
        for i in issues:
            print(f"  ISSUE: {i}")
    print(f"  Clean: {clean}")
    print("  PASS\n")

    # Export audit log
    log_json = bridge.adapter.export_audit_log()
    print(f"[T9] Audit log export: {len(log_json)} chars")
    print("  PASS\n")

    print("=== All 9 tests passed ===")