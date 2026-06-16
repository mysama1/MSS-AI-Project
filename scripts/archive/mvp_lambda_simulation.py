#!/usr/bin/env python3
"""
MSS Glass Fire Seed - MVP Phase 1: Three-Level Lambda System with EIT
Electromagnetically Induced Transparency -> full delta_n dynamic range [0, 1].

Physical model (Lambda configuration):
  |e> - excited state
  / \
 Op  Oc  (probe & coupling laser fields)
 /   \
|g>  |a>  - two ground/metastable states

H = Delta*|e><e| + delta_a*|a><a| + (Op/2)(|e><g| + h.c.) + (Oc/2)(|e><a| + h.c.)

Lindblad: dephasing, spontaneous emission, ground decoherence.
Key observable: delta_n = |rho_eg| (magnitude of probe coherence)
  - Oc = 0: normal absorption -> high delta_n
  - Oc on resonance: EIT transparency -> delta_n -> 0
  - Intermediate Oc: continuous tuning

Sweep Oc in [0.01, 3.0] to map the full delta_n landscape.
"""
import json, os, time, numpy as np

# ==================== Physical Constants ====================
DELTA   = 1.0    # energy gap |e>
DELTA_A = 0.02   # two-photon detuning (|g>-|a> splitting)
OMEGA_P = 0.3    # probe Rabi frequency (fixed)
OMEGA_C = 0.5    # coupling Rabi frequency (control knob)
GAMMA   = 0.05   # electronic dephasing rate
GAMMA_RELAX = 0.02  # spontaneous emission from |e>
GAMMA_GA = 0.001   # ground-state decoherence
TEMP    = 0.1    # temperature

# ==================== Hamiltonian ====================
def make_H(delta=DELTA, delta_a=DELTA_A, op=OMEGA_P, oc=OMEGA_C):
    """H in {|g>, |e>, |a>} basis (3x3)"""
    H = np.zeros((3, 3), dtype=complex)
    H[1, 1] = delta
    H[2, 2] = delta_a
    H[0, 1] = H[1, 0] = op / 2
    H[1, 2] = H[2, 1] = oc / 2
    return H

def make_L(g=GAMMA, gr=GAMMA_RELAX, gga=GAMMA_GA):
    """Lindblad operators for 3-level Lambda system"""
    L = []
    # Dephasing on |e>
    Le = np.zeros((3, 3), dtype=complex)
    Le[1, 1] = np.sqrt(g)
    L.append(Le)
    # Ground decoherence |g>-|a>
    Lga = np.zeros((3, 3), dtype=complex)
    Lga[0, 0] = np.sqrt(gga)
    Lga[2, 2] = -np.sqrt(gga)
    L.append(Lga)
    # Relaxation |e> -> |g>
    Lrg = np.zeros((3, 3), dtype=complex)
    Lrg[0, 1] = np.sqrt(gr / 2)
    L.append(Lrg)
    # Relaxation |e> -> |a>
    Lra = np.zeros((3, 3), dtype=complex)
    Lra[2, 1] = np.sqrt(gr / 2)
    L.append(Lra)
    return L

# ==================== Lindblad Solver ====================
def lindblad_rhs(rho, H, L):
    drho = -1j * (H @ rho - rho @ H)
    for Lk in L:
        LdL = Lk.conj().T @ Lk
        drho += Lk @ rho @ Lk.conj().T - 0.5 * (LdL @ rho + rho @ LdL)
    return drho

def steady_state(H, L, dim=3, dt=0.05, steps=1000, tol=1e-8):
    rho = np.eye(dim, dtype=complex) / dim
    for _ in range(steps):
        k1 = lindblad_rhs(rho, H, L)
        k2 = lindblad_rhs(rho + 0.5*dt*k1, H, L)
        k3 = lindblad_rhs(rho + 0.5*dt*k2, H, L)
        k4 = lindblad_rhs(rho + dt*k3, H, L)
        rho_new = rho + (dt/6)*(k1 + 2*k2 + 2*k3 + k4)
        diff = np.max(np.abs(rho_new - rho))
        rho = rho_new
        if diff < tol:
            break
    return rho

# ==================== Observables ====================
def compute_delta_n(rho):
    """Delta n from probe coherence magnitude |rho_eg|"""
    rho_eg = rho[0, 1]
    return float(np.sqrt(np.real(rho_eg)**2 + np.imag(rho_eg)**2))

def extract_diag(rho):
    return np.real(np.diag(rho))

def classify(dn, thresholds=[0.01, 0.02, 0.04]):
    """F functor: continuous delta_n -> discrete propositions"""
    props = []
    for i, th in enumerate(thresholds):
        if dn > th:
            props.append("dn%d:>%.3f" % (i+1, th))
    if not props:
        props.append("dn0:EIT_transparent")
    return props

# ==================== Physical Realizability ====================
def check_realizable(candidate_props, op=OMEGA_P):
    for oc in np.linspace(0.01, 3.0, 20):
        H = make_H(op=op, oc=oc)
        L = make_L()
        rho = steady_state(H, L)
        dn = compute_delta_n(rho)
        props = classify(dn)
        if set(props) == set(candidate_props):
            return True, {"Oc": round(float(oc), 3), "dn": round(dn, 4)}
    return False, {"reason": "No Oc produces this proposition set"}

# ==================== F^-1 ====================
def props_to_diag(props):
    dn_est = 0.0
    if any("dn3" in p for p in props): dn_est = 0.050
    elif any("dn2" in p for p in props): dn_est = 0.030
    elif any("dn1" in p for p in props): dn_est = 0.015
    p_e = dn_est * 0.3
    p_g = (1.0 - p_e) * 0.6
    p_a = (1.0 - p_e) * 0.4
    return np.array([p_g, p_e, p_a])

def compute_phi(diag_true, diag_pred):
    phi_l2 = 1.0 - np.linalg.norm(diag_true - diag_pred) / np.linalg.norm(diag_true)
    true_dom = np.argmax(diag_true)
    pred_dom = np.argmax(diag_pred)
    phi_struct = 1.0 if true_dom == pred_dom else 0.0
    return {"phi_L2": round(float(phi_l2), 4), "phi_struct": round(float(phi_struct), 4)}

# ==================== Main ====================
def run():
    print("=" * 65)
    print("MSS Glass Fire Seed - MVP Phase 1: Lambda-EIT System")
    print("Three-level Lambda . Oc as control knob for full dn range [0,1]")
    print("=" * 65)

    # [1] Baseline
    print("\n[1] Baseline steady state (Op=0.3, Oc=0.5)...")
    H0 = make_H(oc=0.5)
    L0 = make_L()
    rho0 = steady_state(H0, L0)
    diag0 = extract_diag(rho0)
    dn0 = compute_delta_n(rho0)
    props0 = classify(dn0)
    diag_pred0 = props_to_diag(props0)
    phi0 = compute_phi(diag0, diag_pred0)

    print("  rho_ss diag: |g>=%.4f |e>=%.4f |a>=%.4f" % (diag0[0], diag0[1], diag0[2]))
    print("  rho_eg: (%.4f + %.4fi)" % (rho0[0,1].real, rho0[0,1].imag))
    print("  dn: %.4f" % dn0)
    print("  Propositions: %s" % props0)
    print("  phi_L2: %.4f  phi_struct: %.0f" % (phi0['phi_L2'], phi0['phi_struct']))

    # [2] Oc sweep
    print("\n[2] Sweeping Oc in [0.01, 3.0] - EIT transparency landscape...")
    oc_vals = np.linspace(0.01, 3.0, 30)
    landscape = []
    for oc in oc_vals:
        H = make_H(oc=oc)
        rho = steady_state(H, L0)
        dn = compute_delta_n(rho)
        diag = extract_diag(rho)
        landscape.append({
            "Oc": round(float(oc), 3),
            "dn": round(dn, 4),
            "p_g": round(float(diag[0]), 4),
            "p_e": round(float(diag[1]), 4),
            "p_a": round(float(diag[2]), 4),
            "Re_rho_eg": round(float(rho[0,1].real), 4),
            "Im_rho_eg": round(float(rho[0,1].imag), 4)
        })

    dns = [pt["dn"] for pt in landscape]
    dn_min, dn_max = min(dns), max(dns)
    dn_range = dn_max - dn_min
    targets = [dn_min, dn_min + dn_range/2, dn_max]
    mvp3 = [min(landscape, key=lambda p: abs(p["dn"] - t)) for t in targets]

    print("  dn range: [%.4f, %.4f] (span %.4f)" % (dn_min, dn_max, dn_range))
    print("  MVP 3-state candidates:")
    for pt in mvp3:
        print("    Oc=%.3f -> dn=%.4f  (|g>=%.3f |e>=%.3f |a>=%.3f)" % (
            pt["Oc"], pt["dn"], pt["p_g"], pt["p_e"], pt["p_a"]))

    # [3] Physical realizability
    print("\n[3] Physical realizability test (6 candidates)...")
    candidates = [
        ("T_transparent", ["dn0:EIT_transparent"]),
        ("T_low", ["dn1:>0.010"]),
        ("T_mid", ["dn1:>0.010", "dn2:>0.020"]),
        ("T_high", ["dn1:>0.010", "dn2:>0.020", "dn3:>0.040"]),
        ("T_inconsistent", ["dn3:>0.040"]),  # monotonic violation
        ("T_deep_transparent", ["dn0:EIT_transparent", "dn3:>0.040"]),  # impossible: transparent + high
    ]
    realizability = []
    for name, cprops in candidates:
        ok, info = check_realizable(cprops)
        status = "MERGE" if ok else "UNREVIEWED"
        realizability.append({"name": name, "status": status, "info": info})
        print("  %-20s -> %-12s %s" % (name, status, info))

    # [4] Auto-tune Oc to hit specific dn targets
    print("\n[4] Auto-tuning Oc for target dn = [0.05, 0.15, 0.30, 0.50, 0.70]...")
    def find_oc_for_dn(target, tol=0.005, max_iter=30):
        lo, hi = 0.001, 4.0
        for _ in range(max_iter):
            mid = (lo + hi) / 2
            H = make_H(oc=mid)
            rho = steady_state(H, L0)
            dn = compute_delta_n(rho)
            if abs(dn - target) < tol:
                return round(float(mid), 4), round(dn, 4)
            lo, hi = (mid, hi) if dn > target else (lo, mid)
        return round(float(mid), 4), round(dn, 4)

    tuning = {}
    for tgt in [0.005, 0.015, 0.030, 0.045, 0.055]:
        oc_req, dn_ach = find_oc_for_dn(tgt)
        tuning[str(tgt)] = {"Oc_required": oc_req, "dn_achieved": dn_ach}
        print("  Target dn=%.2f -> Oc=%.4f -> dn=%.4f" % (tgt, oc_req, dn_ach))

    # [5] Coherence
    print("\n[5] Coherence estimates...")
    t2 = 1.0 / GAMMA if GAMMA > 0 else float('inf')
    t2g = 1.0 / GAMMA_GA if GAMMA_GA > 0 else float('inf')
    t1 = 1.0 / GAMMA_RELAX if GAMMA_RELAX > 0 else float('inf')
    dark_enh = GAMMA / (GAMMA_GA + 1e-10)
    print("  T2(probe): %.1f  T2(ground): %.0f  T1: %.0f" % (t2, t2g, t1))
    print("  Dark-state coherence enhancement: ~%.0fx" % dark_enh)

    results = {
        "phase": "MVP_Phase_1",
        "model": "three_level_lambda_EIT",
        "params": {"Delta": DELTA, "Delta_a": DELTA_A, "Op": OMEGA_P, "Oc_0": OMEGA_C,
                   "gamma": GAMMA, "Gamma_relax": GAMMA_RELAX, "gamma_ga": GAMMA_GA},
        "baseline": {"Oc": OMEGA_C, "rho_diag": [round(float(d),4) for d in diag0],
                     "dn": round(dn0,4), "propositions": props0, "fidelity": phi0},
        "landscape": landscape,
        "dn_range": {"min": round(dn_min,4), "max": round(dn_max,4), "span": round(dn_range,4)},
        "mvp_3_states": mvp3,
        "realizability": realizability,
        "tuning": tuning,
        "coherence": {"T2_probe": round(float(t2),1), "T2_ground": round(float(t2g),1),
                      "T1": round(float(t1),1), "dark_enhancement": round(float(dark_enh),1)}
    }
    return results

if __name__ == "__main__":
    t0 = time.time()
    results = run()
    dt = time.time() - t0
    out_dir = r"E:\AI_Workspace\data\mvp_phase1"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "mvp_lambda_eit_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n" + "=" * 65)
    print("DONE in %.1fs - %s (%.1f KB)" % (dt, out_path, os.path.getsize(out_path)/1024))
    print("=" * 65)
