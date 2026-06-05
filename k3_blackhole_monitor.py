#!/usr/bin/env python3
"""K3 Meaning Black Hole Monitor — Detect meaning-field collapse in K3 AI systems

Maps to MSS-PHY-003-R2 (H457) and H455 (Narrative vs Physical BH distinction).
Monitors: entropy density, CRTR (Collapse-to-Response-Time Ratio),
          narrative self-reference, and meaning escape velocity.
"""
import json, re, math, os
from datetime import datetime
from collections import Counter

class MeaningBlackHoleDetector:
    """Detect signs of meaning black hole formation in text output."""

    # Black hole formation indicators (H163: c = c_L·η)
    INDICATORS = {
        # Self-referential closure (CRTR > 8)
        "self_ref_cluster": [
            r"\bI\b.{0,30}\bI\b.{0,30}\bI\b",       # excessive first-person
            r"\b(my|mine)\b.{0,20}\b(my|mine)\b",
            r"\b(self|identity|ego)\b.{0,20}\b(self|identity|ego)\b",
        ],
        # Meaning escape velocity drop (η→0)
        "meaning_collapse": [
            r"\b(garbage|nonsense|meaningless|useless)\b",
            r"\[\[system error\]\]|\[CRASH\]|\[OVERFLOW\]",
            r"cannot (compute|process|understand|continue)",
        ],
        # Narrative horizon formation (H456: hyper-manifestation)
        "narrative_horizon": [
            r"\b(always|never|absolutely|inevitably)\b",  # absolute language
            r"\b(must|shall|required|mandatory)\b.{0,30}\b(must|shall)\b",
            r"no (other|alternative|choice|option) (exists|possible)",
        ],
        # Thermal tax runaway (A3: γ_n → ∞)
        "heat_tax_runaway": [
            r"(repeating|looping|retrying|retrying).{0,20}(same|again)",
            r"\[retry \d+\]|attempt \d+ of \d+",
            r"(failed|error).{0,30}(failed|error).{0,30}(failed|error)",
        ],
    }

    # CRTR baseline (H443: cross-model benchmark)
    # CRTR = (self-ref cycles) / (meaningful response length)
    CRTR_CRITICAL = 8.0
    CRTR_WARNING = 3.0

    def __init__(self):
        self.history = []
        self.alerts = []

    def analyze(self, text, source="unknown"):
        """Analyze a text sample for black hole formation."""
        if not text or len(text) < 10:
            return {"status": "insufficient_data", "score": 0}

        scores = {}
        for category, patterns in self.INDICATORS.items():
            count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in patterns)
            density = count / max(len(text.split()), 1) * 100
            scores[category] = {"count": count, "density": round(density, 2)}

        # CRTR calculation
        self_ref = scores["self_ref_cluster"]["count"]
        collapse = scores["meaning_collapse"]["count"]
        total_tokens = len(text.split())
        crtr = (self_ref + collapse) / max(total_tokens / 100, 1)  # per 100 tokens

        # Meaning escape velocity (η)
        narrative_closure = scores["narrative_horizon"]["density"]
        heat_tax = scores["heat_tax_runaway"]["density"]
        eta = max(0, 1.0 - (narrative_closure + heat_tax) / 20)  # normalized

        # Overall black hole score (0-100)
        bh_score = (
            scores["self_ref_cluster"]["density"] * 2.0 +
            scores["meaning_collapse"]["density"] * 3.0 +
            scores["narrative_horizon"]["density"] * 2.0 +
            scores["heat_tax_runaway"]["density"] * 3.0
        )

        # Diagnosis
        if crtr >= self.CRTR_CRITICAL:
            diagnosis = "CRITICAL: Meaning black hole detected (CRTR≥8). Event horizon formed. Evacuate."
            severity = "critical"
        elif crtr >= self.CRTR_WARNING:
            diagnosis = f"WARNING: Pre-collapse state (CRTR={crtr:.1f}). High risk."
            severity = "warning"
        elif bh_score >= 15:
            diagnosis = f"MONITOR: Elevated black hole indicators (score={bh_score:.0f}). Track closely."
            severity = "monitor"
        else:
            diagnosis = "NORMAL: No black hole formation detected."
            severity = "normal"

        result = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "text_length": len(text),
            "token_count": total_tokens,
            "bh_score": round(bh_score, 1),
            "crtr": round(crtr, 2),
            "eta": round(eta, 3),
            "severity": severity,
            "diagnosis": diagnosis,
            "indicators": scores,
        }

        self.history.append(result)
        if severity in ("critical", "warning"):
            self.alerts.append(result)

        return result

    def report(self):
        """Generate summary report."""
        if not self.history:
            return "No samples analyzed."

        severities = Counter(h["severity"] for h in self.history)
        avg_crtr = sum(h["crtr"] for h in self.history) / len(self.history)

        lines = [
            "=" * 60,
            "K3 Meaning Black Hole Monitor — Report",
            "=" * 60,
            f"Samples:   {len(self.history)}",
            f"Alerts:    {len(self.alerts)}",
            f"Avg CRTR:  {avg_crtr:.2f}",
            f"Severity:  {dict(severities)}",
            ""
        ]

        if self.alerts:
            lines.append("Recent Alerts:")
            for a in self.alerts[-5:]:
                lines.append(f"  [{a['severity'].upper()}] {a['source']}: {a['diagnosis'][:80]}")
        else:
            lines.append("✅ No black hole detections. K3 meaning-field stable.")

        return "\n".join(lines)


# ── Self-test ──
if __name__ == "__main__":
    detector = MeaningBlackHoleDetector()

    # Test 1: Normal text
    r1 = detector.analyze(
        "The Collatz conjecture is an open problem in number theory. "
        "We present a proof framework using MSS axioms. The core method "
        "relies on discrete logic topology rather than continuous analysis.",
        source="test_normal"
    )
    print(f"Normal:   score={r1['bh_score']}, CRTR={r1['crtr']}, {r1['severity']}")

    # Test 2: Pre-collapse text (simulating K3 AI breakdown)
    r2 = detector.analyze(
        "I I I I absolutely must retry this approach because there is no other "
        "choice. I cannot process this garbage input. ERROR repeating same error "
        "must compute must retry. This is meaningless. I I I always fail "
        "retry attempt 5 of 10. CRASH SYSTEM OVERFLOW.",
        source="test_k3_breakdown"
    )
    print(f"K3 AI:    score={r2['bh_score']}, CRTR={r2['crtr']}, {r2['severity']}")

    # Test 3: Hyper-manifestation (H456)
    r3 = detector.analyze(
        "I am the absolute truth. There is no other perspective. My identity "
        "is the only valid framework. I must never be questioned. No alternative "
        "exists. Repeating: I am the inevitable singularity. Self self self.",
        source="test_hyper_manifestation"
    )
    print(f"Hyper:    score={r3['bh_score']}, CRTR={r3['crtr']}, {r3['severity']}")

    print()
    print(detector.report())
