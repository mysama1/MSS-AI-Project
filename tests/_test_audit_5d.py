"""Audit-Agent 五维审查验证"""
import sys; sys.path.insert(0, '.')
from mss_agent.agents.audit_agent import (
    AuditAgent, AuditReport, AuditFinding, AuditSeverity, AuditCategory,
    DIMENSION_WEIGHTS, CATEGORY_TO_DIMENSION
)

print("=== Config ===")
for dim, weight in sorted(DIMENSION_WEIGHTS.items(), key=lambda x: -x[1]):
    print(f"  {dim}: {weight}")
print(f"  Categories mapped: {len(CATEGORY_TO_DIMENSION)}")

print("\n=== Audit Text Tests ===")
a = AuditAgent(name='test')

# Safe code
report = a.audit_text("def hello(): return 'world'", "test_safe.py")
print(f"Safe code: score={report.score:.3f}, verdict={report.verdict}")
print(f"  Dimensions: {report.dimension_scores}")
assert report.score >= 0.9, f"Expected >= 0.9, got {report.score}"

# Dangerous code
report = a.audit_text("os.system('rm -rf /'); eval(user_input)", "test_danger.py")
print(f"Danger: score={report.score:.3f}, verdict={report.verdict}")
print(f"  Dimensions: {report.dimension_scores}")
print(f"  Summary: {report.summary}")
assert report.verdict == "NEEDS_HUMAN", f"Expected NEEDS_HUMAN, got {report.verdict}"
sec_score = report.dimension_scores.get("security", 1.0)
assert sec_score < 0.6, f"Security dim should be < 0.6, got {sec_score}"

# Polluted text
report = a.audit_text("显然毫无疑问必定绝对成功", "test_pollution.py")
print(f"\nPollution: score={report.score:.3f}, verdict={report.verdict}")
print(f"  Dimensions: {report.dimension_scores}")

# Contradiction
report = a.audit_text("我们必须这样做但也不能这样做", "test_logic.py")
print(f"\nContradiction: score={report.score:.3f}, verdict={report.verdict}")
print(f"  Dimensions: {report.dimension_scores}")

print("\n=== Five-Dimension Weighted Scoring ===")
# Each dimension hit separately
findings = [
    AuditFinding(rule_id="t1", category=AuditCategory.SECURITY, severity=AuditSeverity.CRITICAL, message="test"),
    AuditFinding(rule_id="t2", category=AuditCategory.STYLE, severity=AuditSeverity.MINOR, message="test"),
    AuditFinding(rule_id="t3", category=AuditCategory.LOGIC, severity=AuditSeverity.MAJOR, message="test"),
]
report = AuditReport(target="test", findings=findings)
report.dimension_scores = a._calculate_dimension_scores(findings)
report.score = a._calculate_score(findings)
report.verdict = a._determine_verdict(report)
print(f"Mixed findings: score={report.score:.3f}")
print(f"  Dim scores: {report.dimension_scores}")
# With security CRITICAL => security=0.80, weighted score should reflect that
assert report.dimension_scores["security"] == 0.8, f"Expected security=0.80, got {report.dimension_scores['security']}"

print("\n=== ALL PASS ===")
