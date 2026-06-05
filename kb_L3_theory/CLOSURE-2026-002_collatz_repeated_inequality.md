# CLOSURE-2026-002: Collatz Inequality Direction & False Completeness

## 1. Status (现状层)
- Problem: Three separate sessions produced the same type of error:
  1. R1: a>=7 inequality direction wrong (3.5^a > 2·3^a-2^a, not <)
  2. R2: continuity-of-T argument for discrete Collatz map
  3. R3: "complete proof" claim while a>=69 was still open
- Layer: L3 Theory
- Severity: CRITICAL
- Date: 2026-06-04

## 2. Root Cause (归因层)
- Type: Human error + no checkpoint mechanism
- Specific cause: Each fix addressed the immediate error but did not extract
  the general pattern: "heat-tax balance b=a·log₂3 is inequality not equality
  when additive correction R exists." No universal rule was written after
  R1 or R2, so R3 repeated the same structural mistake in different form.

## 3. Lessons (吸收层)
- Rule 1: ANY inequality direction claim → must verify with 3 test values
  (small integer, large integer, boundary value)
- Rule 2: "Complete proof" claim → must pass pre-commit check:
  (a) all cases enumerated OR (b) all cases proven by induction OR
  (c) remaining cases explicitly listed as open
- Rule 3: Additive correction terms (like R in b=a·log₂3+R) cannot be
  assumed negligible — must be bounded or shown irrelevant
- Rule 4: Discrete maps (Collatz) → no continuity arguments allowed

## 4. Systematization (落地层)
- [x] LaTeX v0.5: Step 5 explicit boundary, removed "complete proof"
- [x] H460: Collatz fix R0 → honest boundary
- [x] H462: Full closure audit a=4-14, a>=69 open
- [x] H463: Honesty update documented
- [ ] VDP precommit: add "NO_CONTINUITY_ON_DISCRETE" rule
- [ ] VDP precommit: add "INEQUALITY_3POINT_CHECK" rule
- [ ] VDP precommit: add "COMPLETENESS_GATE" rule

## 5. Recurrence check
- THIRD occurrence → Critical: universal rule extraction required
- Pattern: "heat tax inequality + additive correction" is a recurring
  cognitive trap → needs specific VDP rule
- Next occurrence should trigger automated rejection by precommit

## References
- H460, H462, H463: Collatz fix chain
- D5-033_arxiv_draft.tex v0.1→v0.5: LaTeX evolution
- CLOSURE-2026-001: same "no derivation, arbitrary claim" pattern
