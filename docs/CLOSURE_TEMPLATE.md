# Problem Closure Template

## Trigger
Any theory correction, engineering failure, or proof bug fix → complete within 24h.

## Template

```markdown
# CLOSURE-YYYY-NNN: [Short title]

## 1. Status (现状层)
- Problem: [What broke / was wrong]
- Layer: [L3 Theory / L4 Engineering / L5 Materials]
- Severity: [CRITICAL / HIGH / MEDIUM / LOW]
- Date: YYYY-MM-DD

## 2. Root Cause (归因层)
- Type: [Human error / Theory gap / Tool limitation / Unknown]
- Specific cause: [One sentence]

## 3. Lessons (吸收层)
- Rule 1: [Extracted check rule]
- Rule 2: [Extracted check rule]
- ...

## 4. Systematization (落地层)
- [ ] Added to VDP rules (vdp_scan / vdp_anchor / vdp_precommit)
- [ ] Added to KB (L3 or L4)
- [ ] Added to test suite (test_*.py)
- [ ] Updated OPERATING_MANUAL.md

## 5. Recurrence check
- First occurrence → Knowledge Base entry only
- Second+ occurrence → MUST extract universal rule → VDP + test suite
- One-time debug → Log only, mark EXEMPT

## References
- Related H-IDs: [...]
- Related fixes: [...]
```
