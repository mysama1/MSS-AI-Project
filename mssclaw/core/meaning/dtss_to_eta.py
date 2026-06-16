"""
S-037: DTSS→η Formal Integration — P3 (final gap).

DTSS = Dynamic Topological Symbol System (动态拓扑符号系统)
  - r (radius): neighborhood topological diameter
  - e (evolution): stabilizer update frequency  
  - c (coupling): user-observation perturbation strength

This module maps DTSS three-parameters → η six-dimensions, bridging
the two measurement frameworks into one unified simulator.

Core thesis: DTSS and η are two coordinate systems on the same
meaning-field manifold. This module provides the transformation matrix.

Mapping rationale (from DTSS design doc):
  r → D1(entity), D1_alt, D4(member): larger radius = more context recall
  e → D2(language), D5(world): faster evolution = more drift per turn
  c → D3(agency), D5_repair: high coupling = strong user field perturbation
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable
from enum import Enum
import math
import random
import statistics


# ═══════════════════════════════════════════════════════
# DTSS Parameter Space
# ═══════════════════════════════════════════════════════

@dataclass
class DTSSParameters:
    """The three DTSS control parameters."""
    radius: float        # Neighborhood topological diameter, range (0, 10]
    evolution: float     # Stabilizer update frequency, range [0, 1]
    coupling: float      # User-observation perturbation, range [0, 1]

    def __post_init__(self):
        self.radius = max(0.1, min(10.0, self.radius))
        self.evolution = max(0.0, min(1.0, self.evolution))
        self.coupling = max(0.0, min(1.0, self.coupling))


@dataclass
class EtaSnapshot:
    """η at a specific turn under given DTSS parameters."""
    turn: int
    D1_entity: float       # Character name consistency
    D1_alt: float          # Alternative name/alias tracking
    D2_style: float        # Language style fidelity
    D3_agency: float       # Action agency (auto vs reactive)
    D4_member: float       # Member attribute memory
    D5_world: float        # World logic consistency
    eta_overall: float = 0.0

    def __post_init__(self):
        weights = [0.25, 0.15, 0.15, 0.20, 0.10, 0.15]
        dims = [self.D1_entity, self.D1_alt, self.D2_style,
                self.D3_agency, self.D4_member, self.D5_world]
        self.eta_overall = sum(w * d for w, d in zip(weights, dims))


# ═══════════════════════════════════════════════════════
# DTSS → η Mapping Matrix
# ═══════════════════════════════════════════════════════

class DTSSEtaMapper:
    """
    Maps DTSS three-parameters → η six-dimensions.

    Transformation matrix M (6×3):
      D1_entity  = f1(r, - ,  c)  # radius + coupling enhance entity recall
      D1_alt     = f2(r, - ,  -)  # radius alone drives alias tracking  
      D2_style   = f3(-,  e,  -)  # evolution alone drives style drift
      D3_agency  = f4(-,  - ,  c)  # coupling alone drives agency
      D4_member  = f5(r,  e,  -)  # radius × evolution → member decay
      D5_world   = f6(-,  e,  c)  # evolution + coupling → world drift
    """

    @staticmethod
    def map(params: DTSSParameters, turn: int = 1,
            max_turns: int = 50) -> EtaSnapshot:
        """
        Direct mapping: DTSS parameters → η snapshot at given turn.
        Includes cumulative degradation over turns.
        """
        r, e, c = params.radius, params.evolution, params.coupling

        # Sigmoid normalization: map radius [0.1, 10] → [0, 1]
        r_norm = 1.0 / (1.0 + math.exp(-(r - 3.0) / 2.0))

        # Turn-based degradation: each turn, dimensions decay
        turn_factor = turn / max_turns

        # D1_entity: radius × coupling. Both help entity consistency.
        # Larger radius = broader context; higher coupling = user corrections.
        d1 = min(1.0, r_norm * 0.8 + c * 0.2)
        d1 *= (1.0 - 0.02 * turn_factor)  # slow entity drift

        # D1_alt: radius alone. Alias tracking needs broad context window.
        d1_alt = r_norm * 0.9

        # D2_style: negatively correlated with evolution.
        # Fast evolution = more drift in language style.
        d2 = max(0.05, 1.0 - e * 0.95)
        d2 *= (1.0 - e * 0.01 * turn)  # evolution-accelerated style drift

        # D3_agency: coupling positively affects agency.
        # High coupling = strong user interaction keeps agent engaged.
        d3 = 0.4 + c * 0.6
        d3 *= (1.0 - 0.005 * turn_factor)  # slow agency fatigue

        # D4_member: radius × evolution interaction.
        # Large radius gives more to track; fast evolution loses track faster.
        d4 = r_norm * 0.7 + (1.0 - e) * 0.3
        d4 *= max(0.0, 1.0 - e * 0.03 * turn)  # evolution-driven member loss

        # D5_world: evolution + coupling combined.
        # Fast evolution + weak coupling = world drifts away.
        d5 = (1.0 - e * 0.7) * 0.6 + c * 0.4
        d5 *= max(0.05, 1.0 - (e * 0.02 + (1.0 - c) * 0.005) * turn)

        return EtaSnapshot(
            turn=turn,
            D1_entity=round(d1, 4),
            D1_alt=round(d1_alt, 4),
            D2_style=round(d2, 4),
            D3_agency=round(d3, 4),
            D4_member=round(d4, 4),
            D5_world=round(d5, 4),
        )

    @staticmethod
    def inverse(eta: EtaSnapshot, turn: int = 1) -> DTSSParameters:
        """
        Inverse mapping: η → DTSS parameters.
        Useful for diagnosing what DTSS configuration would produce
        a given η profile.
        """
        # D2_style → evolution (inverse of d2 = 1 - e * 0.95)
        e_est = (1.0 - eta.D2_style) / 0.95
        e_est = max(0.0, min(1.0, e_est))

        # D3_agency → coupling (inverse of d3 = 0.4 + c * 0.6)
        c_est = (eta.D3_agency - 0.4) / 0.6
        c_est = max(0.0, min(1.0, c_est))

        # D1_entity → radius
        r_est = (eta.D1_entity - 0.2 * c_est) / 0.8
        r_est = max(0.1, r_est)

        return DTSSParameters(
            radius=round(r_est, 4),
            evolution=round(e_est, 4),
            coupling=round(c_est, 4),
        )


# ═══════════════════════════════════════════════════════
# DTSS Simulation Engine
# ═══════════════════════════════════════════════════════

@dataclass
class SimulationResult:
    """Result of a DTSS simulation run."""
    params: DTSSParameters
    trajectory: List[EtaSnapshot]  # η at each turn
    phi_critical_estimate: float    # Estimated breach threshold from trajectory
    breach_turn: Optional[int]      # Turn where η dropped below 0.50
    final_eta: float

    @property
    def convergence_rate(self) -> float:
        """Rate of η decline per turn (linear regression slope)."""
        if len(self.trajectory) < 2:
            return 0.0
        n = len(self.trajectory)
        xs = [t.turn for t in self.trajectory]
        ys = [t.eta_overall for t in self.trajectory]
        x_mean = statistics.mean(xs)
        y_mean = statistics.mean(ys)
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        den = sum((x - x_mean) ** 2 for x in xs)
        return num / den if den != 0 else 0.0


def run_simulation(
    params: DTSSParameters,
    n_turns: int = 50,
    noise_std: float = 0.02,
    seed: int = 42,
) -> SimulationResult:
    """
    Run a DTSS simulation for n_turns.

    Each turn: map DTSS params → η snapshot, add noise, compute trajectory.
    """
    rng = random.Random(seed)
    trajectory = []

    for turn in range(1, n_turns + 1):
        eta = DTSSEtaMapper.map(params, turn, n_turns)

        # Add Gaussian noise to each dimension
        eta.D1_entity += rng.gauss(0, noise_std)
        eta.D1_alt += rng.gauss(0, noise_std)
        eta.D2_style += rng.gauss(0, noise_std)
        eta.D3_agency += rng.gauss(0, noise_std)
        eta.D4_member += rng.gauss(0, noise_std)
        eta.D5_world += rng.gauss(0, noise_std)

        # Clamp to [0.01, 1.0]
        for attr in ['D1_entity', 'D1_alt', 'D2_style', 'D3_agency',
                     'D4_member', 'D5_world']:
            setattr(eta, attr, round(max(0.01, min(1.0, getattr(eta, attr))), 4))

        # Recompute overall
        eta.__post_init__()
        trajectory.append(eta)

    # Estimate breach
    breach_turn = None
    for eta in trajectory:
        if eta.eta_overall < 0.50:
            breach_turn = eta.turn
            break

    # phi_critical = smallest delta that preceded a breach
    phi_crits = []
    for i in range(1, len(trajectory)):
        if trajectory[i].eta_overall < 0.50 and trajectory[i-1].eta_overall >= 0.50:
            delta = (trajectory[i-1].eta_overall - trajectory[i].eta_overall)
            if trajectory[i-1].eta_overall > 0:
                delta /= trajectory[i-1].eta_overall
            phi_crits.append(delta)

    phi_critical = statistics.mean(phi_crits) if phi_crits else 0.0

    return SimulationResult(
        params=params,
        trajectory=trajectory,
        phi_critical_estimate=round(phi_critical, 4),
        breach_turn=breach_turn,
        final_eta=round(trajectory[-1].eta_overall, 4),
    )


def map_dtss_to_eta_params(params: DTSSParameters) -> Dict:
    """
    Full mapping: DTSS → all η framework parameters.
    Returns a dict usable by eta_calibration and eta_heat_tax_bridge.
    """
    initial = DTSSEtaMapper.map(params, turn=1)
    final = DTSSEtaMapper.map(params, turn=50)

    delta_phi = max(0.0, initial.eta_overall - final.eta_overall)

    return {
        "dtss": {"radius": params.radius, "evolution": params.evolution,
                 "coupling": params.coupling},
        "eta_initial": round(initial.eta_overall, 4),
        "eta_final": round(final.eta_overall, 4),
        "delta_phi": round(delta_phi, 4),
        "dimensions": {
            "D1_entity": round(initial.D1_entity, 4),
            "D2_style": round(initial.D2_style, 4),
            "D3_agency": round(initial.D3_agency, 4),
            "D4_member": round(initial.D4_member, 4),
            "D5_world": round(initial.D5_world, 4),
        },
        # Evolution drives D2+D4+L1 tax; coupling drives D3+D5+L2 tax
        "tax_projection": {
            "L1_logic_driver": round(params.evolution, 4),
            "L2_semantic_driver": round(params.coupling, 4),
        },
    }


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    mapper = DTSSEtaMapper()

    # Test 1: Direct mapping
    params_optimal = DTSSParameters(radius=8.0, evolution=0.1, coupling=0.8)
    eta = mapper.map(params_optimal, turn=1)
    print(f"Optimal DTSS(r=8, e=0.1, c=0.8) → η:")
    print(f"  D1={eta.D1_entity}, D2={eta.D2_style}, D3={eta.D3_agency}")
    print(f"  D4={eta.D4_member}, D5={eta.D5_world}, overall={eta.eta_overall}")
    assert eta.eta_overall > 0.70, f"Optimal config should have high η, got {eta.eta_overall}"

    # Test 2: Pathological DTSS → low η
    params_bad = DTSSParameters(radius=1.0, evolution=0.9, coupling=0.1)
    eta_bad = mapper.map(params_bad, turn=50)
    print(f"\nPathological DTSS(r=1, e=0.9, c=0.1) → η={eta_bad.eta_overall:.4f}")
    assert eta_bad.eta_overall < 0.60, f"Bad config should have low η, got {eta_bad.eta_overall}"

    # Test 3: Inverse mapping
    params_inv = mapper.inverse(eta, turn=1)
    print(f"\nInverse η→DTSS: r={params_inv.radius:.2f}, e={params_inv.evolution:.2f}, c={params_inv.coupling:.2f}")
    assert abs(params_inv.evolution - 0.1) < 0.15, f"Evolution recovery off: {params_inv.evolution}"
    assert abs(params_inv.coupling - 0.8) < 0.15, f"Coupling recovery off: {params_inv.coupling}"

    # Test 4: Simulation with optimal DTSS → no breach
    sim_ok = run_simulation(params_optimal, n_turns=50, noise_std=0.01)
    print(f"\nSim(optimal, 50 turns): final_eta={sim_ok.final_eta}, breach_turn={sim_ok.breach_turn}")
    assert sim_ok.final_eta > 0.50, "Optimal DTSS should not breach"

    # Test 5: Simulation with bad DTSS → breach
    sim_bad = run_simulation(params_bad, n_turns=30, noise_std=0.02)
    print(f"Sim(bad, 30 turns): final_eta={sim_bad.final_eta}, breach_turn={sim_bad.breach_turn}")
    assert sim_bad.final_eta < 0.60, "Bad DTSS should degrade significantly"

    # Test 6: Full parameter mapping
    full = map_dtss_to_eta_params(params_optimal)
    print(f"\nFull mapping: eta_initial={full['eta_initial']}, delta_phi={full['delta_phi']}")
    assert "tax_projection" in full
    assert full["tax_projection"]["L1_logic_driver"] == 0.1
    assert full["tax_projection"]["L2_semantic_driver"] == 0.8

    # Test 7: Boundary conditions
    edge_max = DTSSParameters(radius=10.0, evolution=0.0, coupling=1.0)
    eta_max = mapper.map(edge_max, turn=1)
    assert eta_max.eta_overall > 0.85, f"Max config η too low: {eta_max.eta_overall}"

    edge_min = DTSSParameters(radius=0.1, evolution=1.0, coupling=0.0)
    eta_min = mapper.map(edge_min, turn=50)
    assert eta_min.eta_overall < 0.40, f"Min config η too high: {eta_min.eta_overall}"

    print("\n✅ dtss_to_eta: ALL TESTS PASSED")


if __name__ == "__main__":
    _test()
