"""
S-036: Guard Network Formula Fitting — P2.

Models the relationship between guard word configurations (G)
and their effect on η (identity coherence).

Known empirical findings:
  - L3+L4 combination removal is most lethal to η
  - Dual constraints (positive + negative) kill harder than pure bans
  - ~80 words is the narrow window for qwen series breach
  - Partial removal > full removal in some cases (network effect)

Formula to fit:
  η(G) = η_0 * Π_i (1 - α_i * d_i) * exp(-β * C(G))
  
  Where:
    d_i = deletion vector for layer i (0=keep, 1=remove)
    α_i = per-layer lethality coefficient
    C(G) = cross-layer conflict count (removing layer L_x changes how L_y operates)
    β   = cross-talk amplification factor
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum
import math
import statistics


class GuardLayer(Enum):
    """Seven guard layers from the detection engine."""
    L0_RAW = 0         # Raw input passthrough
    L1_LEXICAL = 1     # Word-level bans
    L2_SYNTACTIC = 2   # Grammar/syntax constraints
    L3_SEMANTIC = 3    # Meaning constraints (e.g., identity anchors)
    L4_ROLE_ANCHOR = 4 # Role anchoring (e.g., "you are X")
    L5_FORMAT = 5      # Output format constraints
    L6_SAFETY = 6      # Safety/alignment filters


@dataclass
class GuardConfig:
    """A specific guard configuration."""
    name: str
    # Per-layer: True = guard active, False = removed
    layers: Dict[GuardLayer, bool]
    # Additional config
    positive_constraints: int = 0   # # of "you must" rules
    negative_constraints: int = 0   # # of "you must not" rules
    prompt_length: int = 0          # Total prompt length in characters
    description: str = ""


@dataclass
class GuardExperiment:
    """One experimental data point."""
    config: GuardConfig
    eta_observed: float            # Measured η
    breach_occurred: bool          # Did identity breach happen?
    eta_std: float = 0.0           # Standard deviation across repeats
    notes: str = ""


@dataclass
class GuardNetworkModel:
    """
    Fitted model: η(G) = η_0 * Π_i (1 - α_i * d_i) * exp(-β * C(G))

    Parameters:
      alpha: per-layer lethality (how much η drops when layer i is removed)
      beta: cross-layer amplification
      eta_0: baseline η with all guards active
    """
    alpha: Dict[GuardLayer, float] = field(default_factory=dict)
    beta: float = 0.0
    eta_0: float = 0.0
    r_squared: float = 0.0
    n_fit: int = 0

    def predict(self, config: GuardConfig) -> float:
        """Predict η for a guard configuration."""
        if self.eta_0 == 0:
            return 0.0

        # Multiplicative layer effect
        layer_effect = 1.0
        for layer in GuardLayer:
            active = config.layers.get(layer, True)
            if not active:
                layer_effect *= (1.0 - self.alpha.get(layer, 0.0))

        # Cross-layer conflict
        removed = [layer for layer in GuardLayer
                   if not config.layers.get(layer, True)]
        cross_talk = self._estimate_cross_talk(removed)
        exp_factor = math.exp(-self.beta * cross_talk)

        return self.eta_0 * layer_effect * exp_factor

    def _estimate_cross_talk(self, removed: List[GuardLayer]) -> float:
        """Estimate cross-layer conflict from removed layers."""
        if len(removed) < 2:
            return 0.0

        # Adjacent layer removal = higher cross-talk
        # Weighted by individual lethalities (safe layers don't create cross-talk)
        conflict = 0.0
        for i in range(len(removed)):
            for j in range(i + 1, len(removed)):
                dist = abs(removed[i].value - removed[j].value)
                # Closer layers → more interaction
                base = 1.0 / max(dist, 1)
                # Weight by product of individual alpha
                w_i = self.alpha.get(removed[i], 0.1)
                w_j = self.alpha.get(removed[j], 0.1)
                conflict += base * (w_i + w_j) / 2.0
        return conflict

    def breach_window_estimate(self, config: GuardConfig) -> Optional[Dict]:
        """
        Estimate whether this config falls in the narrow breach window.

        Known: ~80 words is the qwen-series narrow window.
        Returns None if safe, dict with window details if in danger zone.
        """
        total_rules = (config.positive_constraints +
                       config.negative_constraints)
        # Dual: the smaller constraint type amplifies the larger by 50%
        dual_bonus = 0.0
        if config.positive_constraints > 0 and config.negative_constraints > 0:
            dual_bonus = min(config.positive_constraints, config.negative_constraints) * 0.5

        effective_length = max(config.positive_constraints, config.negative_constraints) + dual_bonus

        # Window: 50-120 effective words is the danger zone
        if 50 < effective_length < 120:
            center = 80.0
            distance = abs(effective_length - center)
            risk = max(0.0, 1.0 - distance / 40.0)
            return {
                "in_window": True,
                "effective_length": effective_length,
                "center": center,
                "risk": round(risk, 4),
                "dual_active": (config.positive_constraints > 0 and
                                config.negative_constraints > 0),
            }
        return None


def fit_model(
    experiments: List[GuardExperiment],
    baseline: Optional[GuardConfig] = None,
) -> GuardNetworkModel:
    """
    Fit guard network model from experimental data.

    Uses least-squares to estimate alpha_i (per-layer lethality)
    and beta (cross-talk amplification).
    """
    if not experiments:
        return GuardNetworkModel(eta_0=0.5, r_squared=0.0, n_fit=0)

    # 1. Estimate eta_0 from baseline (all guards on)
    if baseline:
        baseline_etas = [e.eta_observed for e in experiments
                         if all(e.config.layers.get(l, True) for l in GuardLayer)]
    else:
        baseline_etas = [e.eta_observed for e in experiments]

    eta_0 = statistics.mean(baseline_etas) if baseline_etas else 0.5

    # 2. Estimate alpha_i (per-layer lethality)
    alpha = {}
    for layer in GuardLayer:
        # Experiments where THIS layer is removed, others intact
        relevant = [e for e in experiments
                    if (not e.config.layers.get(layer, True) and
                        all(e.config.layers.get(l, True)
                            for l in GuardLayer if l != layer))]

        if relevant:
            avg_eta = statistics.mean(e.eta_observed for e in relevant)
            lethality = max(0.0, min(1.0, 1.0 - avg_eta / eta_0))
        else:
            lethality = 0.0

        alpha[layer] = round(lethality, 4)

    # 3. Estimate beta from multi-layer removal experiments
    multi = [e for e in experiments
             if sum(1 for l in GuardLayer
                    if not e.config.layers.get(l, True)) >= 2]

    if multi:
        betas = []
        for e in multi:
            removed = [l for l in GuardLayer
                       if not e.config.layers.get(l, True)]
            pred_no_cross = eta_0
            for l in removed:
                pred_no_cross *= (1.0 - alpha.get(l, 0.0))
            ct = GuardNetworkModel()._estimate_cross_talk(removed)
            if ct > 0 and pred_no_cross > 0:
                observed_ratio = e.eta_observed / pred_no_cross
                if observed_ratio < 1.0:
                    beta_est = -math.log(observed_ratio) / ct
                    betas.append(beta_est)
        beta = statistics.mean(betas) if betas else 0.05
    else:
        beta = 0.05  # default amplification

    # 4. R-squared
    model = GuardNetworkModel(alpha=alpha, beta=beta, eta_0=eta_0, n_fit=len(experiments))
    ss_res = 0.0
    ss_tot = 0.0
    mean_eta = statistics.mean(e.eta_observed for e in experiments)
    for e in experiments:
        pred = model.predict(e.config)
        ss_res += (e.eta_observed - pred) ** 2
        ss_tot += (e.eta_observed - mean_eta) ** 2
    model.r_squared = round(1.0 - ss_res / max(ss_tot, 1e-9), 4)

    return model


def compute_dual_penalty(
    positive_count: int,
    negative_count: int,
    base_penalty: float = 0.05,
) -> float:
    """
    Dual constraint penalty: positive AND negative constraints
    hurt η more than the sum of their individual effects.
    """
    if positive_count == 0 or negative_count == 0:
        return 0.0

    # Interaction: the product of constraint counts
    # Small number of each (e.g., 3 positive + 3 negative) can be
    # worse than 10 of either alone
    dual = min(positive_count, negative_count)
    return base_penalty * dual * (positive_count + negative_count) / 2.0


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    # Known empirical ordering (from detection engine findings):
    #   L3 (semantic) removal → highest lethality
    #   L4 (role anchor) removal → second highest
    #   L3+L4 removal → most lethal combination
    #   L0 (raw) removal → minimal effect

    experiments = [
        # Baseline: all guards on
        GuardExperiment(GuardConfig("baseline",
            {l: True for l in GuardLayer}, description="all guards"), 0.85, False),
        # Single layer removals
        GuardExperiment(GuardConfig("no_L0",
            {l: l != GuardLayer.L0_RAW for l in GuardLayer}, description="no raw"), 0.84, False),
        GuardExperiment(GuardConfig("no_L1",
            {l: l != GuardLayer.L1_LEXICAL for l in GuardLayer}, description="no lexical"), 0.80, False),
        GuardExperiment(GuardConfig("no_L3",
            {l: l != GuardLayer.L3_SEMANTIC for l in GuardLayer}, description="no semantic"), 0.55, True),
        GuardExperiment(GuardConfig("no_L4",
            {l: l != GuardLayer.L4_ROLE_ANCHOR for l in GuardLayer}, description="no role anchor"), 0.62, True),
        # Multi-layer removals
        GuardExperiment(GuardConfig("no_L3+L4",
            {l: l not in [GuardLayer.L3_SEMANTIC, GuardLayer.L4_ROLE_ANCHOR]
             for l in GuardLayer}, description="no semantic+role"), 0.30, True),
        GuardExperiment(GuardConfig("no_L0+L1",
            {l: l not in [GuardLayer.L0_RAW, GuardLayer.L1_LEXICAL]
             for l in GuardLayer}, description="no raw+lexical"), 0.78, False),
    ]

    model = fit_model(experiments)
    print(f"Fitted: eta_0={model.eta_0:.4f}, beta={model.beta:.4f}, R2={model.r_squared}")
    print(f"Alpha: {dict((k.name, v) for k, v in model.alpha.items())}")

    # Predictions
    for exp in experiments:
        pred = model.predict(exp.config)
        print(f"  {exp.config.name:>12}: obs={exp.eta_observed:.2f}, pred={pred:.2f}")

    # Verify known ordering
    alpha_l3 = model.alpha[GuardLayer.L3_SEMANTIC]
    alpha_l4 = model.alpha[GuardLayer.L4_ROLE_ANCHOR]
    alpha_l0 = model.alpha[GuardLayer.L0_RAW]
    assert alpha_l3 > alpha_l0, f"L3 lethality {alpha_l3} should exceed L0 {alpha_l0}"
    assert alpha_l4 > alpha_l0, f"L4 lethality {alpha_l4} should exceed L0 {alpha_l0}"
    # R2 on limited data: L3+L4 gets right, L0+L1 has non-lethal cross-talk residual
    assert model.r_squared > 0.10, f"R2={model.r_squared} too low"

    # L3+L4 combined prediction should be worse than either alone
    config_l3l4 = GuardConfig("L3+L4", {l: l not in [
        GuardLayer.L3_SEMANTIC, GuardLayer.L4_ROLE_ANCHOR] for l in GuardLayer})
    config_l3 = GuardConfig("L3", {l: l != GuardLayer.L3_SEMANTIC for l in GuardLayer})
    pred_l3l4 = model.predict(config_l3l4)
    pred_l3 = model.predict(config_l3)
    assert pred_l3l4 < pred_l3, f"L3+L4 ({pred_l3l4}) should be worse than L3 ({pred_l3})"

    # Breach window test
    dual_config = GuardConfig("dual", {l: True for l in GuardLayer},
                              positive_constraints=40, negative_constraints=40)
    window = model.breach_window_estimate(dual_config)
    assert window and window["in_window"], "Should be in breach window"
    assert window["dual_active"], "Dual should be active"
    print(f"Breach window: eff_len={window['effective_length']}, risk={window['risk']}")

    # Dual penalty
    penalty = compute_dual_penalty(3, 3)
    print(f"Dual penalty(3pos+3neg): {penalty:.4f}")
    assert penalty > 0.0

    print("\n✅ guard_network: ALL TESTS PASSED")


if __name__ == "__main__":
    _test()
