#!/usr/bin/env python3
"""
D5-033 a≥69: New attack paths
======================
Known: a≤68 closed (Simons & de Weger 2005)
Open: a≥69 — the b = a·log₂3 approximation barrier

New paths:
  P1: Trivial b-range rejection (when b_min > b_max, no cycle possible)
  P2: 2-adic valuation structure of denom = 2^b - 3^a
  P3: Modular arithmetic sieve (eliminate candidate (a,b) pairs)
  P4: Diophantine structure of the cycle equation
  P5: Pattern detection for a≥69 up to computational limit
"""

import math, time, sys
from collections import defaultdict, Counter

def v2(n):
    """2-adic valuation (trailing zeros)"""
    if n == 0: return float('inf')
    c = 0
    while n % 2 == 0:
        n //= 2
        c += 1
    return c

def v3(n):
    """3-adic valuation"""
    if n == 0: return float('inf')
    c = 0
    while n % 3 == 0:
        n //= 3
        c += 1
    return c

# ── P1: b-range analysis ──

def analyze_b_range(a_max=200):
    """When does b_min > b_max? Shows trivially impossible regions."""
    print("P1: b-range analysis (a=1..%d)" % a_max)
    print("  a | b_min | b_max | valid? | denom_range")
    print("  " + "-" * 50)
    
    trivial_from = None
    for a in range(1, a_max + 1):
        b_min = math.ceil(a * math.log2(3))
        b_max = math.floor(a * math.log2(3.5))
        valid = b_min <= b_max
        
        if valid:
            # Show first few valid b values
            denom_min = 2**b_min - 3**a
            denom_max = 2**b_max - 3**a
            
            if a <= 20 or a % 20 == 0:
                print("  %3d | %5d | %5d |  YES   | %d .. %d" % (a, b_min, b_max, denom_min, denom_max))
        else:
            if trivial_from is None:
                trivial_from = a
                print("  ── TRIVIAL REJECTION STARTS ──")
            if a <= trivial_from + 5 or a % 20 == 0:
                print("  %3d | %5d | %5d |  NOPE  | —" % (a, b_min, b_max))
    
    if trivial_from:
        print("\n  Trivially impossible from a=%d onward (b_min > b_max)" % trivial_from)
    else:
        print("\n  All a=1..%d have valid b ranges" % a_max)


# ── P2: 2-adic valuation structure ──

def analyze_v2_structure(a_max=100):
    """Analyze v2(2^b - 3^a) for each valid (a,b) pair."""
    print("\nP2: 2-adic valuation of denom = 2^b - 3^a")
    print("  a | b   | v2(denom) | denom mod 8")
    print("  " + "-" * 45)
    
    v2_counts = Counter()
    
    for a in range(1, a_max + 1):
        b_min = math.ceil(a * math.log2(3))
        b_max = math.floor(a * math.log2(3.5))
        
        if b_min > b_max:
            continue
        
        for b in range(b_min, b_max + 1):
            denom = 2**b - 3**a
            if denom <= 0: continue
            v = min(v2(denom), 10)  # cap at 10
            v2_counts[v] += 1
            
            if a <= 15:
                print("  %3d | %4d | v2=%d     | %d" % (a, b, v, denom % 8))
    
    print("\n  v2 distribution:")
    for v, cnt in sorted(v2_counts.items()):
        bar = "█" * max(1, cnt // 2)
        print("    v2=%2d: %d %s" % (v, cnt, bar))
    
    # Key insight: v2(2^b - 3^a) is always small for valid (a,b)
    # This constrains the numerator R's divisibility


# ── P3: Modular sieve ──

def modular_sieve(a_max=200, mods=[3,5,7,11,13,17,19]):
    """
    For each modulus m, find (a,b) where denom ≡ 0 (mod m).
    If NO solution exists modulo m for a given a, that a is impossible.
    """
    print("\nP3: Modular sieve elimination")
    
    eliminated = set()
    
    for m in mods:
        # Precompute 3^a mod m for a=1..a_max and 2^b mod m for relevant b
        pow3 = [1]
        for _ in range(a_max):
            pow3.append((pow3[-1] * 3) % m)
        
        pow2_max = math.ceil(a_max * math.log2(3.5)) + 10
        pow2 = [1]
        for _ in range(pow2_max):
            pow2.append((pow2[-1] * 2) % m)
        
        a_elim = 0
        for a in range(1, a_max + 1):
            b_min = math.ceil(a * math.log2(3))
            b_max = floor_bound = math.floor(a * math.log2(3.5))
            
            has_solution = False
            for b in range(b_min, b_max + 1):
                denom_mod_m = (pow2[b] - pow3[a]) % m
                if denom_mod_m == 0:
                    has_solution = True
                    break
            
            if not has_solution:
                eliminated.add(a)
                a_elim += 1
        
        print("  mod %2d: eliminated %d values of a (1..%d)" % (m, a_elim, a_max))
    
    remaining = a_max - len(eliminated)
    print("\n  Total eliminated: %d | Remaining: %d" % (len(eliminated), remaining))
    if eliminated:
        covered = set(range(1, a_max + 1)) - eliminated
        print("  First 10 survivors: %s" % sorted(covered)[:10])


# ── P4: Diophantine structure ──

def analyze_denom_factors(a_max=80):
    """
    Find the smallest prime factor of denom = 2^b - 3^a.
    If that prime > 10^6, the cycle search is computationally hard.
    """
    print("\nP4: Denom factor analysis")
    print("  a | denom    | smallest factor")
    print("  " + "-" * 40)
    
    def smallest_factor(n):
        if n <= 0: return None
        for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]:
            if n % p == 0: return p
        # Not trivially small
        return ">47"
    
    for a in range(1, a_max + 1):
        b = math.ceil(a * math.log2(3))
        denom = 2**b - 3**a
        sf = smallest_factor(denom)
        if sf and (sf == ">47" or a <= 20):
            print("  %3d | %9d | %s" % (a, denom, sf))


# ── P5: Pattern detection for a≥69 ──

def detect_patterns(a_start=69, a_end=120):
    """
    For a≥69, check the structure of the b-range.
    Look for arithmetic patterns in: b_min growth, b_range size, denom parity.
    """
    print("\nP5: Pattern detection a=%d..%d" % (a_start, a_end))
    
    data = []
    for a in range(a_start, a_end + 1):
        b_min = math.ceil(a * math.log2(3))
        b_max = math.floor(a * math.log2(3.5))
        valid = b_min <= b_max
        if valid:
            denom = 2**b_min - 3**a
            data.append((a, b_min, b_max, b_max - b_min + 1, denom, v3(denom)))
    
    if not data:
        print("  No valid (a,b) pairs — all trivially impossible!")
        return
    
    # Print first 10 entries
    print("  a  | b_min | b_max | range | denom       | v3(denom)")
    print("  " + "-" * 55)
    for a, bmin, bmax, rng, den, v3d in data[:15]:
        print("  %3d | %5d | %5d | %3d   | %11d | %d" % (a, bmin, bmax, rng, den, v3d))
    
    if len(data) > 15:
        print("  ... (%d more)" % (len(data) - 15))
    
    # Analyze range growth
    ranges = [r for _, _, _, r, _, _ in data]
    avg_range = sum(ranges) / len(ranges)
    print("\n  Avg b-range size: %.1f" % avg_range)
    print("  b-range grows ~O(log a)? %s" % ("YES" if ranges[-1] / ranges[0] < 2 else "NO"))
    
    # Check for trivial rejection boundary
    # When does b_min > b_max happen?
    for a in range(a_end, a_end + 50):
        b_min = math.ceil(a * math.log2(3))
        b_max = math.floor(a * math.log2(3.5))
        if b_min > b_max:
            print("\n  ⚡ Trivial rejection boundary: a=%d (b_min=%d > b_max=%d)" % (a, b_min, b_max))
            break
    else:
        print("\n  No trivial rejection up to a=%d" % (a_end + 49))


# ── Main ──

def main():
    print("=" * 60)
    print("D5-033 a≥69: New Attack Paths Explorer")
    print("=" * 60)
    
    # P1: b-range
    analyze_b_range(200)
    
    # P2: 2-adic
    analyze_v2_structure(100)
    
    # P3: modular sieve
    modular_sieve(200)
    
    # P4: factor analysis
    analyze_denom_factors(50)
    
    # P5: a≥69 patterns
    detect_patterns(69, 150)
    
    print("\n" + "=" * 60)
    print("Summary: D5-033 a≥69 exploration")
    print("  All attempts fail on: b = a·log₂3 approximation error")
    print("  DOI: 10.5281/zenodo.20537026 (v0.4 — honest)")

if __name__ == "__main__":
    main()
