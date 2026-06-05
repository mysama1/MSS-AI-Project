# CLOSURE-2026-001: Dark Matter Arbitrary Percentage Assignment

## 1. Status (现状层)
- Problem: 75%/20%/5% dark matter split had no derivation
- Layer: L3 Theory (leaked from L4 engineering intuition)
- Severity: HIGH
- Date: 2026-06-04

## 2. Root Cause (归因层)
- Type: Theory gap + layer confusion
- Specific cause: L4 engineering "rule of thumb" (most/less/trace) was stated as
  L3 theory quantitative claim without any mathematical derivation, then propagated
  to public-facing document claiming to replace LCDM.

## 3. Lessons (吸收层)
- Rule 1: NO arbitrary percentage assignments without derivation → L3 gate
- Rule 2: Every quantitative claim MUST cite either: (a) MSS derivation,
  (b) K3 measurement, (c) explicitly labeled as "estimate with no derivation"
- Rule 3: "Replace LCDM" claims require CMB/BAO/SNIa quantitative predictions
  → if absent, must say "supplementary interpretation" not "replacement"

## 4. Systematization (落地层)
- [x] Added to KB: H474 → H475 (v1 → v2 correction)
- [x] VDP anchor guard: number claims now check for derivation source
- [ ] VDP precommit: add "NO_ARBITRARY_RATIO" rule pattern (TODO)
- [x] Documented in: H477 (KB management SOP section 1-3)

## 5. Recurrence check
- Second occurrence: Collatz inequality direction error (3 sessions, 3 fixes)
  → This pattern reinforces need for universal rule extraction
  → Separate CLOSURE-2026-002 needed for Collatz

## References
- H474: Dark matter v1 (flawed)
- H475: Dark matter v2 (corrected)
- H477: KB management SOP
