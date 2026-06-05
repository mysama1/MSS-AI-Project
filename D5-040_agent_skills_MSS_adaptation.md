# D5-040: MSS Code Review Skill — Adapted from agent-skills

**Source**: github.com/addyosmani/agent-skills (37.7k stars)
**Adaptation Date**: 2026-05-31
**Status**: P0 — Phase 1 complete (framework adapted)

---

## MSS Review: Three-Axis Framework

### MSS Adaptation: K3 "Correctness" → MSS "Logical Rigidity"

**K3 baseline**: Does the code do what it claims?
- Matches spec, edge cases handled, error paths, tests pass
- Off-by-one errors, race conditions, state inconsistency detection

**MSS upgrade**: Is every claim **axiom-anchored**?
1. Every function return type → anchored to a specific MSS axiom (A1-A6)
2. No floating logic: every conditional branch → traceable to a formal premise
3. No "probably works" — all input/output contracts verifiable
4. Off-by-one errors → quantized as "heat tax leakage" (γ leak)
5. Race conditions → diagnosed as "meaning field desynchronization"

### MSS Adaptation: K3 "Readability" → MSS "Meaning Fidelity"

**K3 baseline**: Can another engineer understand this code?
- Descriptive naming, straightforward control flow, minimal cleverness
- Dead code removal, appropriate comments

**MSS upgrade**: Does the code's **surface form** match its **meaning intent**?
1. Function name → function meaning: iff name says "calculate_X" then return type must be X
2. MeaningContract decorator: every public function declares input/output meaning
3. Dead code → meaningless code → violates A2 (Informational Slicing)
4. Comments must explain *why* (meaning intent), not *what* (surface description)
5. Anti-pattern detection: "meaning theft" (function says compute but has side effects)

### MSS Adaptation: K3 "Performance" → MSS "Thermal Tax Index"

**K3 baseline**: No N+1 queries, unbounded loops, missing pagination
- Async where appropriate, no unnecessary re-renders

**MSS upgrade**: Quantify computational cost as **thermal tax (γ)**:
1. γ = (CPU cycles × κ) + (memory allocation × τ₀)
2. O(n²) complexity → γ ∝ n²·κ — flagged if γ > γ_threshold
3. N+1 patterns → γ multiplier detected (× N)
4. Unbounded loops → potential thermal tax singularity → P0
5. Meaningless recalculations → "hot spot" thermal tax accumulation

---

## MSS Review Process

### Multi-Role Architecture (from agent-skills)

| Role | K3 Role | MSS Role |
|:---|:---|:---|
| Logical Rigidity Auditor | ~ Architect | Verifies A1-A6 axiom anchoring |
| Thermal Tax Auditor | ~ Performance | Quantifies γ per function/loop |
| Meaning Fidelity Checker | ~ Readability | Verifies surface↔meaning match |

### Quality Gates (MSS-Adapted)

| Gate | K3 Threshold | MSS Threshold |
|:---|:---|:---|
| P0 Block | Security vuln / crash bug | Logical rigidity failure (axiom violation) |
| P1 Must-Fix | Major bug / perf regress | High γ (γ > 10) / severe meaning mismatch |
| P2 Should-Fix | Minor issue / style | Moderate γ (3 < γ < 10) / ambiguous naming |

### Approval Standard (MSS-Adapted)
**Approve if**: Δ(代码健康度) > 0    AND    γ_total < γ_budget
**Reject if**: γ_total > γ_budget    OR    any P0 logical rigidity failure

---

## MSS Review Output Format

```json
{
  "file": "<path>",
  "mss_score": 0-100,
  "logical_rigidity": {
    "score": 0-100,
    "axiom_anchors": ["A3", "A6"],
    "issues": [{
      "level": "P0",
      "axiom": "A1",
      "description": "Unanchored claim: 'users will always...'",
      "fix": "Add explicit input validation contract"
    }]
  },
  "thermal_tax": {
    "gamma_total": "float",
    "hot_spots": ["func_name:line"],
    "gamma_budget_remaining": "float"
  },
  "meaning_fidelity": {
    "score": 0-100,
    "meaning_contracts": ["func_name"],
    "violations": ["func_name: line"]
  }
}
```

---

## Implementation Status

### ✅ Completed (D5-040 Phase 1)
- [x] Agent-skills repo cloned: `E:\AI_Workspace\agent-skills`
- [x] Five-axis → Three-axis MSS mapping defined
- [x] MSS review process and quality gates defined
- [x] Output format standardized

### ⏳ Next (D5-040 Phase 2)
- [ ] Create `E:\AI_Workspace\MSS-AI\project\skills\mss-code-review\SKILL.md`
- [ ] Implement MSS review runner (Python + AST)
- [ ] Integrate with mss_meaning_audit_v02.py
- [ ] Test on active MSS project files

### Reference Files
- `E:\AI_Workspace\agent-skills\skills\code-review-and-quality\SKILL.md` — Source
- `E:\AI_Workspace\MSS-AI\project\tools\mss_meaning_audit_v02.py` — Integration target