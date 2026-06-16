#!/usr/bin/env python3
"""
MSS Glass Fire Seed — MVP Phase 0: Numerical Simulation
Two-level system + single phonon mode under Keldysh ionization.

Physical model:
  H = H_elec + H_phonon + H_e-p
  H_elec  = (Δ/2)σ_z + (Ω/2)σ_x              (two-level electronic)
  H_phonon = ω b†b                              (single phonon mode)
  H_e-p   = g σ_z (b† + b)                      (electron-phonon coupling)

We compute:
  1. Steady-state density matrix ρ_ss (diagonal elements = physical intrinsic)
  2. Birefringence pattern Δn from ρ_ss population difference
  3. F functor: ρ_ss → discrete propositions
  4. φ_struct: closed-loop fidelity (ρ → propositions → ρ')
  5. Physical realizability check for three artificial candidate topologies

The simulation uses qutip's mesolve or a simple Lindblad master equation solver.
If qutip is not available, we use a custom RK4-based solver.
"""
import json, os, sys, time
import numpy as np
from scipy.linalg import expm

# ==================== Physical Constants ====================
# Two-level system parameters (units: ℏ = 1)
DELTA = 1.0        # energy gap between |0> and |1> (THz scale for glass defects)
OMEGA = 0.3        # Rabi frequency of laser coupling
G_COUPLING = 0.15  # electron-phonon coupling strength
OMEGA_PHONON = 0.5 # phonon frequency
TEMP = 0.1         # temperature (in units of ℏω/kB ≈ room temp for THz phonon)
GAMMA = 0.05       # dephasing rate (diagonal relaxation)
KAPPA = 0.02       # phonon damping rate
N_THERM = 1.0 / (np.exp(OMEGA_PHONON / TEMP) - 1) if TEMP > 1e-6 else 0.0  # thermal phonon occupation

# ==================== Pauli Matrices ====================
sx = np.array([[0, 1], [1, 0]], dtype=complex)
sy = np.array([[0, -1j], [1j, 0]], dtype=complex)
sz = np.array([[1, 0], [0, -1]], dtype=complex)
I2 = np.eye(2, dtype=complex)

# ==================== Lindblad Solver ====================
def lindblad_rhs(rho, H, L_ops):
    """Compute dρ/dt = -i[H, ρ] + Σ(L ρ L† - ½{L†L, ρ})"""
    drho = -1j * (H @ rho - rho @ H)
    for L in L_ops:
        LdL = L.conj().T @ L
        drho += L @ rho @ L.conj().T - 0.5 * (LdL @ rho + rho @ LdL)
    return drho

def steady_state(H, L_ops, dim=2, dt=0.05, steps=2000, tol=1e-8):
    """Evolve to steady state via RK4."""
    rho = np.eye(dim, dtype=complex) / dim  # maximally mixed initial state
    for _ in range(steps):
        k1 = lindblad_rhs(rho, H, L_ops)
        k2 = lindblad_rhs(rho + 0.5*dt*k1, H, L_ops)
        k3 = lindblad_rhs(rho + 0.5*dt*k2, H, L_ops)
        k4 = lindblad_rhs(rho + dt*k3, H, L_ops)
        rho_new = rho + (dt/6)*(k1 + 2*k2 + 2*k3 + k4)
        diff = np.max(np.abs(rho_new - rho))
        rho = rho_new
        if diff < tol:
            break
    return rho

# ==================== Hamiltonian Construction ====================
def build_hamiltonian(delta=DELTA, omega=OMEGA, g=G_COUPLING, omega_ph=OMEGA_PHONON):
    """Build H = H_elec + H_phonon + H_e-p in the |e,n> basis."""
    # For a single phonon mode, we truncate to N_ph = 2 (0 or 1 phonon)
    # This gives a 4-dim Hilbert space: |g,0>, |g,1>, |e,0>, |e,1>
    dim = 4
    H = np.zeros((dim, dim), dtype=complex)
    
    # H_elec: (Δ/2)σ_z ⊗ I_ph + (Ω/2)σ_x ⊗ I_ph
    H_elec_z = (delta/2) * np.kron(sz, I2)
    H_elec_x = (omega/2) * np.kron(sx, I2)
    
    # H_phonon: I_el ⊗ ω b†b  (in |0>,|1> basis)
    n_op = np.array([[0, 0], [0, 1]], dtype=complex)  # number operator
    H_phonon = omega_ph * np.kron(I2, n_op)
    
    # H_e-p: g σ_z ⊗ (b† + b)
    b_dag = np.array([[0, 0], [1, 0]], dtype=complex)  # creation operator
    b = np.array([[0, 1], [0, 0]], dtype=complex)      # annihilation operator
    H_ep = g * np.kron(sz, b_dag + b)
    
    H = H_elec_z + H_elec_x + H_phonon + H_ep
    return H, dim

def build_lindblad_ops(dim=4, gamma=GAMMA, kappa=KAPPA, n_th=N_THERM):
    """Lindblad operators for dephasing and phonon damping."""
    L_ops = []
    
    # Electronic dephasing: √(γ) σ_z ⊗ I_ph
    L_dephase = np.sqrt(gamma) * np.kron(sz, I2)
    L_ops.append(L_dephase)
    
    # Electronic relaxation: √(γ/2) σ_- ⊗ I_ph
    sigma_minus = np.array([[0, 0], [1, 0]], dtype=complex)
    L_relax = np.sqrt(gamma/2) * np.kron(sigma_minus, I2)
    L_ops.append(L_relax)
    
    # Phonon damping: √(κ(n_th+1)) I_el ⊗ b
    b = np.array([[0, 1], [0, 0]], dtype=complex)
    L_ph_damp = np.sqrt(kappa * (n_th + 1)) * np.kron(I2, b)
    L_ops.append(L_ph_damp)
    
    # Phonon excitation: √(κ n_th) I_el ⊗ b†
    b_dag = np.array([[0, 0], [1, 0]], dtype=complex)
    L_ph_excite = np.sqrt(kappa * n_th) * np.kron(I2, b_dag)
    L_ops.append(L_ph_excite)
    
    return L_ops

# ==================== F Functor: ρ → Propositions ====================
def extract_physical_intrinsic(rho):
    """Extract diagonal elements of ρ_ss → 4-component probability vector (ρ_ss的对角元)."""
    return np.real(np.diag(rho))

def compute_birefringence(diag_probs):
    """
    Compute observable birefringence Δn from population difference.
    For glass: Δn ∝ (population of excited electronic state) × (local field factor).
    
    Returns a single scalar Δn for this minimal model.
    """
    # Populations: |g,0>, |g,1>, |e,0>, |e,1>
    p_e = diag_probs[2] + diag_probs[3]  # total excited state population
    delta_n = p_e  # simplified: Δn ∝ excited state population
    return delta_n

def classify_birefringence(delta_n, thresholds=[0.1, 0.3, 0.5, 0.7]):
    """F functor: map continuous Δn → discrete propositions."""
    propositions = []
    for i, th in enumerate(thresholds):
        if delta_n > th:
            propositions.append(f"Δn_{i+1}: birefringence exceeds {th}")
    if not propositions:
        propositions.append("Δn_0: birefringence below detection threshold")
    return propositions

# ==================== F^{-1}: Propositions → predicted ρ ====================
def propositions_to_rho_pred(propositions):
    """
    Inverse F: given propositions, predict what ρ_ss should look like.
    This is a crude model — in a real system, F^-1 would be a trained decoder.
    For the toy model, we use the proposition thresholds to estimate populations.
    """
    delta_n_estimate = 0.0
    if any("Δn_4" in p for p in propositions):
        delta_n_estimate = 0.8
    elif any("Δn_3" in p for p in propositions):
        delta_n_estimate = 0.6
    elif any("Δn_2" in p for p in propositions):
        delta_n_estimate = 0.4
    elif any("Δn_1" in p for p in propositions):
        delta_n_estimate = 0.2
    
    # Reconstruct diagonal probabilities (simplified)
    p_e = delta_n_estimate
    p_g = 1.0 - p_e
    # Distribute ground state populations equally between |g,0> and |g,1>
    # Distribute excited state populations equally between |e,0> and |e,1>
    rho_pred_diag = np.array([p_g/2, p_g/2, p_e/2, p_e/2])
    return rho_pred_diag

def compute_phi(diag_true, diag_pred):
    """Compute fidelity metrics."""
    # φ_L2: 1 - L2 distance
    phi_l2 = 1.0 - np.linalg.norm(diag_true - diag_pred) / np.linalg.norm(diag_true)
    
    # φ_struct: which propositions are preserved?
    # For the toy model: check if the dominant population component matches
    true_dominant = np.argmax(diag_true)
    pred_dominant = np.argmax(diag_pred)
    structural_edges_preserved = 1 if true_dominant == pred_dominant else 0
    phi_struct = float(structural_edges_preserved)
    
    return {"phi_L2": round(float(phi_l2), 4), "phi_struct": phi_struct}

# ==================== Physical Realizability Check ====================
def check_physical_realizability(candidate_propositions, H, dim=4):
    """
    Check if a candidate topology is physically realizable under current H.
    
    For the toy model: scan laser intensity Ω to see if any ρ_ss maps to 
    the candidate propositions.
    """
    omega_values = np.linspace(0.05, 1.5, 20)
    for omega in omega_values:
        H_test, _ = build_hamiltonian(omega=omega)
        L_ops = build_lindblad_ops(dim)
        rho_test = steady_state(H_test, L_ops, dim)
        diag_test = extract_physical_intrinsic(rho_test)
        props_test = classify_birefringence(compute_birefringence(diag_test))
        if set(props_test) == set(candidate_propositions):
            return True, {"omega_required": round(float(omega), 3), "delta_n_achieved": round(float(compute_birefringence(diag_test)), 4)}
    return False, {"reason": f"No Ω in [0.05, 1.5] produces the specified proposition set"}

# ==================== Main Simulation ====================
def run_mvp_simulation():
    print("=" * 60)
    print("MSS Glass Fire Seed — MVP Phase 0 Simulation")
    print("Two-level system + single phonon mode")
    print("=" * 60)
    
    # Step 1: Compute steady state
    print("\n[Step 1] Computing steady-state density matrix ρ_ss...")
    H, dim = build_hamiltonian()
    L_ops = build_lindblad_ops(dim)
    rho_ss = steady_state(H, L_ops, dim)
    diag = extract_physical_intrinsic(rho_ss)
    
    print(f"  Hamiltonian: {dim}x{dim}")
    print(f"  ρ_ss diagonal: [{', '.join(f'{d:.4f}' for d in diag)}]")
    print(f"  Trace(ρ): {np.trace(rho_ss).real:.6f}")
    
    # Step 2: Measure birefringence
    print("\n[Step 2] Computing birefringence Δn from ρ_ss...")
    delta_n = compute_birefringence(diag)
    print(f"  Δn (population-based): {delta_n:.4f}")
    
    # Step 3: F functor — ρ → propositions
    print("\n[Step 3] F functor: ρ_ss → Propositions...")
    propositions = classify_birefringence(delta_n)
    print(f"  Propositions: {propositions}")
    
    # Step 4: F^-1 — propositions → predicted ρ
    print("\n[Step 4] F^-1: Propositions → Predicted ρ'...")
    rho_pred_diag = propositions_to_rho_pred(propositions)
    print(f"  Predicted diagonal: [{', '.join(f'{d:.4f}' for d in rho_pred_diag)}]")
    
    # Step 5: Fidelity
    print("\n[Step 5] φ fidelity computation...")
    phi = compute_phi(diag, rho_pred_diag)
    print(f"  φ_L2: {phi['phi_L2']:.4f}")
    print(f"  φ_struct: {phi['phi_struct']} (dominant level match)")
    
    # Step 6: Test three candidate topologies for physical realizability
    print("\n[Step 6] Physical realizability check on 3 candidate topologies...")
    
    candidates = [
        {"name": "T_candidate_1", "props": ["Δn_1: birefringence exceeds 0.1"]},
        {"name": "T_candidate_2", "props": ["Δn_4: birefringence exceeds 0.7"]},
        {"name": "T_candidate_3", "props": ["Δn_3: birefringence exceeds 0.5"]},
    ]
    
    for cand in candidates:
        realizable, info = check_physical_realizability(cand["props"], H, dim)
        status = "MERGE" if realizable else "UNREVIEWED"
        print(f"  {cand['name']}: {status} — {info}")
    
    # Step 7: Sweep over Ω to map the Δn landscape
    print("\n[Step 7] Sweep: Δn vs Ω landscape...")
    omega_sweep = np.linspace(0.02, 2.0, 50)
    landscape = []
    for omega in omega_sweep:
        H_s, d = build_hamiltonian(omega=omega)
        rho = steady_state(H_s, L_ops, d)
        dn = compute_birefringence(extract_physical_intrinsic(rho))
        landscape.append({"omega": round(float(omega), 3), "delta_n": round(float(dn), 4)})
    
    # Find 3 distinct Δn values for MVP criterion
    unique_dn = {}
    for pt in landscape:
        key = round(pt["delta_n"], 2)
        if key not in unique_dn and key > 0.01:
            unique_dn[key] = pt
    
    target_points = list(unique_dn.values())[:3]
    print(f"  Found {len(unique_dn)} distinct Δn values")
    print(f"  MVP-3 candidates (3 different ρ_ss):")
    for pt in target_points:
        print(f"    Ω={pt['omega']:.3f} → Δn={pt['delta_n']:.4f}")
    
    # Compute coherence time estimate
    print(f"\n[Step 8] Coherence & lifetime estimates...")
    t2 = 1.0 / GAMMA if GAMMA > 0 else float('inf')
    t1 = 2.0 / GAMMA if GAMMA > 0 else float('inf')
    print(f"  T₂ (dephasing): {t2:.1f} (ℏ units)")
    print(f"  T₁ (relaxation): {t1:.1f} (ℏ units)")
    print(f"  Note: For fs-laser written defects in fused silica, actual T₂ ~ ms at cryo, μs at 300K")
    
    # Results summary
    results = {
        "simulation": "MVP_Phase_0",
        "physical_model": "two_level_system + single_phonon_mode",
        "parameters": {
            "delta": DELTA, "omega": OMEGA, "g_coupling": G_COUPLING,
            "omega_phonon": OMEGA_PHONON, "temperature": TEMP,
            "gamma": GAMMA, "kappa": KAPPA, "n_thermal": round(float(N_THERM), 4)
        },
        "rho_ss_diagonal": [round(float(d), 4) for d in diag],
        "delta_n": round(float(delta_n), 4),
        "propositions": propositions,
        "fidelity": phi,
        "candidate_topologies": [
            {"name": c["name"], "realizable": check_physical_realizability(c["props"], H, dim)[0]}
            for c in candidates
        ],
        "landscape": landscape,
        "mvp_3_states": target_points,
        "coherence": {"T2": round(float(t2), 1), "T1": round(float(t1), 1)}
    }
    
    return results

if __name__ == "__main__":
    t0 = time.time()
    results = run_mvp_simulation()
    elapsed = time.time() - t0
    
    out_dir = r"E:\AI_Workspace\data\mvp_phase0"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "mvp_simulation_results.json")
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Simulation complete in {elapsed:.2f}s")
    print(f"Results: {out_path}")
    print(f"{'='*60}")
