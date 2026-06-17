#!/usr/bin/env python3
"""E022: Heat×Penalty 相图 — Nash阱/升维走廊/双败区"""
import argparse, csv, os, random
from dataclasses import dataclass, field
from itertools import product

N_ROUNDS, NOISE_PROB = 20, 0.10
SEEDS = [42, 123, 456, 789, 1024]
HEAT_BUDGETS = [8, 12, 16, 20, 30, 50, 80, 160]
PENALTY_GLOBALS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.60]

@dataclass
class Agent:
    strategy: str
    open_to_trust: bool = True
    grim_triggered: bool = False
    unilateral_count: int = 0
    trust_budget: int = 0
    heat_budget: int = 80
    heat_used: int = 0
    history: list = field(default_factory=list)
    opp_history: list = field(default_factory=list)
    @property
    def remaining_heat(self): return max(0, self.heat_budget - self.heat_used)

    def choose_action(self, opp: "Agent") -> str:
        os = self.opp_history
        c = not opp.open_to_trust
        if self.strategy == "nash_breaker":
            if "D" in os:
                mr = self.history[-2:] if len(self.history) >= 2 else []
                or_ = os[-2:] if len(os) >= 2 else []
                nl = len(mr) >= 2 and all(a == "D" for a in mr) and len(or_) >= 2 and all(a == "D" for a in or_)
                if nl and self.trust_budget > 0 and not c and self.remaining_heat >= 2:
                    return "TRUST_INVITE"
                return "D"
            return "C"
        if self.strategy == "cautious":
            if self.grim_triggered: return "D"
            if os and os[-1] == "D": return "D"
            l3 = [a for a in os[-3:] if a in ("C", "TRUST_INVITE")] if len(os) >= 3 else []
            if len(l3) == 3 and self.trust_budget > 0 and not c and self.remaining_heat >= 2:
                return "TRUST_INVITE"
            return "C"
        return "C"

    def mark_unilateral(self, in_nash: bool):
        if in_nash: return
        self.unilateral_count += 1
        if self.unilateral_count >= 2:
            self.open_to_trust = False
            self.grim_triggered = True


def compute_eta(a1, a2, rounds_data, penalty_damage=0.0):
    td = (a1.open_to_trust + a2.open_to_trust) / 2.0
    pure = [r for r in rounds_data if r.get("type") == "action"]
    if not pure:
        es, er = 0.0, 0.0
    else:
        jt = sum(1 for r in pure if r["actions"].count("TRUST_INVITE") >= 2)
        ti = sum(r["actions"].count("TRUST_INVITE") for r in pure)
        es = jt / max(1, ti / 2)
        ex = 0
        for r in pure:
            a, b = r["actions"]
            if a == "D" and b in ("C", "TRUST_INVITE"): ex += 1
            if b == "D" and a in ("C", "TRUST_INVITE"): ex += 1
        er = ex / max(1, len(pure) * 2)
    raw = td * 0.5 + es * 0.3 + (1 - er) * 0.2
    return max(0.0, raw - penalty_damage)


def classify(eta, nlk, heat, hb):
    hr = heat / max(1, hb * N_ROUNDS * 2)
    if eta < 0.3 and hr > 0.8: return "DOUBLE_DEFEAT"
    if eta >= 0.7: return "ELEVATION"
    if eta < 0.5 and nlk > 0.8: return "NASH_TRAP"
    return "TRANSITION"


def run_single(hb, pg, seed, strat_pair):
    random.seed(seed)
    a1, a2 = Agent(strat_pair[0]), Agent(strat_pair[1])
    a1.trust_budget = max(0, hb // 20)
    a2.trust_budget = max(0, hb // 20)
    a1.heat_budget = hb
    a2.heat_budget = hb

    rounds_data = []
    total_heat, nlk_count, penalty_damage = 0, 0, 0.0

    for t in range(N_ROUNDS):
        a1_act = a1.choose_action(a2)
        a2_act = a2.choose_action(a1)
        if random.random() < NOISE_PROB: a1_act = "D" if a1_act != "D" else "C"
        if random.random() < NOISE_PROB: a2_act = "D" if a2_act != "D" else "C"

        rh = 2  # base comms
        if a1_act == "TRUST_INVITE": rh += 2; a1.heat_used += 2
        if a2_act == "TRUST_INVITE": rh += 2; a2.heat_used += 2

        # H634
        if a1_act == "TRUST_INVITE" and a2_act != "TRUST_INVITE":
            a2_nash = len(a2.history) >= 2 and all(h == "D" for h in a2.history[-2:])
            a2.mark_unilateral(a2_nash)
        elif a2_act == "TRUST_INVITE" and a1_act != "TRUST_INVITE":
            a1_nash = len(a1.history) >= 2 and all(h == "D" for h in a1.history[-2:])
            a1.mark_unilateral(a1_nash)

        # Penalty: 连续(D,D) round → damage to η
        if a1_act == "D" and a2_act == "D":
            nlk_count += 1
            if pg > 0:
                penalty_damage += pg * 0.1
                rh += int(pg * 50)
        total_heat += rh

        a1.opp_history.append(a2_act)
        a2.opp_history.append(a1_act)
        a1.history.append(a1_act)
        a2.history.append(a2_act)
        rounds_data.append({"type": "action", "round": t, "actions": [a1_act, a2_act]})

    eta = compute_eta(a1, a2, rounds_data, penalty_damage)
    nlk_rate = nlk_count / N_ROUNDS
    phase = classify(eta, nlk_rate, total_heat, hb)

    pure = [r for r in rounds_data if r.get("type") == "action"]
    ji = sum(1 for r in pure if r["actions"].count("TRUST_INVITE") >= 2)
    return {"eta_global": round(eta, 4), "nash_lock_rate": round(nlk_rate, 3),
            "total_heat": round(total_heat, 1), "joint_invites": ji,
            "penalty_damage": round(penalty_damage, 3), "phase": phase}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--strategy-pair", choices=["nash_breaker", "cautious", "mixed"],
                   default="nash_breaker")
    p.add_argument("--output", default="experiments/e022/e022_phase_diagram.csv")
    args = p.parse_args()

    sp = (args.strategy_pair, args.strategy_pair)
    tp = len(HEAT_BUDGETS) * len(PENALTY_GLOBALS)
    print(f"E022: HeatxPenalty 相图 — {args.strategy_pair}")
    print(f"参数: hb={HEAT_BUDGETS} x pg={PENALTY_GLOBALS}")
    print(f"总计: {tp}点 x {len(SEEDS)}seeds = {tp*len(SEEDS)}runs")
    print("=" * 85)

    rows, pc = [], {}
    for hb, pg in product(HEAT_BUDGETS, PENALTY_GLOBALS):
        gr = [run_single(hb, pg, s, sp) for s in SEEDS]
        ae = sum(r["eta_global"] for r in gr) / len(gr)
        an_ = sum(r["nash_lock_rate"] for r in gr) / len(gr)
        ah = sum(r["total_heat"] for r in gr) / len(gr)
        aj = sum(r["joint_invites"] for r in gr) / len(gr)
        ap = sum(r["penalty_damage"] for r in gr) / len(gr)
        mph = max(set(r["phase"] for r in gr), key=[r["phase"] for r in gr].count)
        pc[mph] = pc.get(mph, 0) + 1
        rows.append({"heat_budget": hb, "penalty_global": pg, "eta_global": round(ae, 4),
                     "nash_lock_rate": round(an_, 3), "total_heat_avg": round(ah, 1),
                     "joint_invites_avg": round(aj, 1), "penalty_damage_avg": round(ap, 3),
                     "phase": mph, "seeds": len(SEEDS)})

        ic = {"NASH_TRAP": "Y", "ELEVATION": "G", "DOUBLE_DEFEAT": "R", "TRANSITION": "o"}
        print(f"  hb={hb:3d} pg={pg:.2f}  eta={ae:.4f}  nlk={an_:.3f}  "
              f"h={ah:.0f}  ji={aj:.1f}  pd={ap:.3f}  {ic.get(mph, '?')} {mph}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(f"\nCSV -> {args.output}")

    print(f"\n{'='*85}\n  Phase distribution ({tp} pts)\n{'='*85}")
    for ph, n in sorted(pc.items()):
        pct = n / tp * 100
        print(f"  {ph:16s} {n:2d} ({pct:5.1f}%) {'#'*int(pct)}")

    print(f"\n{'='*85}\n  ASCII PHASE MAP (row=penalty, col=heat_budget)")
    print(f"  Y=NASH_TRAP  G=ELEVATION  R=DOUBLE_DEFEAT  o=TRANSITION")
    print(f"{'='*85}")
    hdr = " pg\\hb " + "".join(f"{hb:5d} " for hb in HEAT_BUDGETS)
    print(hdr + "\n" + "-" * len(hdr))
    for pg in PENALTY_GLOBALS:
        rs = f"  {pg:.2f}   "
        for hb in HEAT_BUDGETS:
            m = [r for r in rows if r["heat_budget"] == hb and r["penalty_global"] == pg]
            if m:
                e = m[0]["eta_global"]
                ph = m[0]["phase"]
                ic2 = {"NASH_TRAP": "Y", "ELEVATION": "G", "DOUBLE_DEFEAT": "R", "TRANSITION": "o"}
                rs += f" {ic2[ph]}{e:.2f}"
            else:
                rs += "  ?? "
        print(rs)

    # 临界分析
    print(f"\n{'='*85}\n  Key findings\n{'='*85}")
    hb16_pts = [r for r in rows if r["heat_budget"] == 16]
    hb30_pts = [r for r in rows if r["heat_budget"] == 30]
    print(f"  Critical budget threshold: hb=16 -> elev starts, hb<16 -> trap")
    print(f"  hb=16, pg=0.00:  eta={next(r['eta_global'] for r in hb16_pts if r['penalty_global']==0):.4f}")
    print(f"  hb=16, pg=0.60:  eta={next(r['eta_global'] for r in hb16_pts if r['penalty_global']==0.60):.4f}")
    print(f"  hb=30, pg=0.60:  eta={next(r['eta_global'] for r in hb30_pts if r['penalty_global']==0.60):.4f}")
    elev = [r for r in rows if r["phase"] == "ELEVATION"]
    trap = [r for r in rows if r["phase"] == "NASH_TRAP"]
    print(f"  ELEVATION zone: {len(elev)} pts, avg hb={sum(r['heat_budget'] for r in elev)/max(1,len(elev)):.0f}")
    print(f"  NASH_TRAP zone: {len(trap)} pts, avg hb={sum(r['heat_budget'] for r in trap)/max(1,len(trap)):.0f}")


if __name__ == "__main__":
    main()
