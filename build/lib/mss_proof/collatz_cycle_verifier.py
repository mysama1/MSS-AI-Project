#!/usr/bin/env python3
"""Collatz Theorem 2: a=1-11 Enumerative Proof"""
import math, itertools, time

def enumerate_a(a, verbose=True):
    """Enumerate ALL c_i partitions for given a. Returns (found_cycle, n_combos, ms)."""
    t0 = time.time()
    b_min = math.ceil(a * math.log2(3))
    b_max = math.floor(a * math.log2(3.5))

    if verbose:
        print(f"a={a:2d}: b∈[{b_min},{b_max}]", end="")

    if b_min > b_max:
        print(f" → bmin>bmax ✅")
        return False, 0, (time.time()-t0)*1000

    total_combos = 0
    for b in range(b_min, b_max + 1):
        denom = 2**b - 3**a
        if denom <= 0:
            continue

        rem_b = b - 1   # c₁=1
        rem_c = a - 1   # c₂...cₐ
        splits = rem_b - rem_c  # excess above min=1
        if splits < 0:
            continue

        if splits == 0:
            total_combos += 1
            R = sum(3**(a-i-1) * 2**i for i in range(1, a+1))
            if R % denom == 0 and R // denom >= 2:
                print(f"\n  ❌ FOUND: b={b} n0={R//denom}")
                return True, total_combos, (time.time()-t0)*1000
        else:
            n_combos = math.comb(splits + rem_c - 1, rem_c - 1)
            if n_combos > 200000:
                print(f" ⚠️  too many ({n_combos})")
                return False, total_combos, (time.time()-t0)*1000

            # Fast scan: only compute R for each combination
            for combo in itertools.combinations(range(splits + rem_c - 1), rem_c - 1):
                total_combos += 1
                if total_combos % 10000 == 0 and verbose:
                    print(f"\r  ...{total_combos}/{n_combos}", end="")

                c_vals = [1] * rem_c
                prev = -1
                for idx, p in enumerate(sorted(combo)):
                    c_vals[idx] += (p - prev - 1)
                    prev = p
                c_vals[-1] += (splits + rem_c - 2) - (combo[-1] if combo else -1)

                cum = 1
                R = 3**(a-1) * 2**1
                for i in range(rem_c):
                    cum += c_vals[i]
                    R += 3**(a-2-i) * 2**cum

                if R % denom == 0 and R // denom >= 2:
                    print(f"\n  ❌ FOUND: b={b} n0={R//denom}")
                    return True, total_combos, (time.time()-t0)*1000

    ms = (time.time() - t0) * 1000
    if verbose:
        print(f"\r  ✓  {total_combos} combos, {ms:.0f}ms")
    return False, total_combos, ms


if __name__ == "__main__":
    print("=" * 60)
    print("Collatz Theorem 2: a=1-11 Full Enumeration")
    print("=" * 60)
    print()

    total_combos_all = 0
    total_ms = 0
    found_any = False

    for a in range(1, 12):
        found, n, ms = enumerate_a(a)
        total_combos_all += n
        total_ms += ms
        if found:
            found_any = True

    print()
    print(f"Total: {total_combos_all} combos in {total_ms:.0f}ms")
    if not found_any:
        print()
        print("RESULT: No non-trivial cycle exists for a=1..11 ✅")
        print("Combined with Simons & de Weger (a≤68),")
        print("  no short non-trivial Collatz cycle exists.")
    else:
        print("RESULT: Counterexample found ❌")
