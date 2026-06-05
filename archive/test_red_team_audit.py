#!/usr/bin/env python3
"""test_red_team_audit.py — Test suite for red_team_audit_protocol.py"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from red_team_audit_protocol import (
    RedTeamAuditor, ReportFormatter, AuditReport, AuditFinding,
    Severity, AuditDimension, ALL_RULES, MSS_INTERNAL_TERMS,
    AUDITOR_INVITATION_TEMPLATE
)

# ─── Test Fixtures ─────────────────────────────────────────────────

FULL_VIOLATION_DOC = """
# MSS-AI: 终极范式革命

MSS-AI将彻底替代传统LLM，实现零幻觉和100%的逻辑刚性。

我们的系统在3个月内就能完成全部开发，碾压所有现有AI系统。

基于A6公理的热税动力学，我们证明了K3文明的必然崩溃。
这是人类文明从K3到K4跃迁的唯一希望，是划时代的终极解决方案。

从逻辑上证明所有物理现象都可以被MSS框架解释，
因此我们可以100%预测未来的技术发展方向。

传统深度学习毫无意义，只是在浪费GPU算力。
不是拥抱MSS范式，就是在旧范式中自取灭亡。

我们坚信这将是AI领域的最后一次范式革命。
"""

CLEAN_DOC = """
# MSS-Proof: 数学定理证明辅助系统

MSS-Proof的目标是在数学定理自动证明任务上，在标准基准测试中
达到业界领先水平。我们估计，在ProofNet基准上，准确率将相比现有
最佳系统提升15-25%（置信度C=0.8，证伪条件：如果提升<10%）。

项目分为三阶段：第一阶段（18个月）专注数学证明，第二阶段扩展到
代码验证等领域。当前工程实现仅覆盖初等数论和命题逻辑的自动证明。

**已知局限**：
1. 高阶谓词逻辑的自动证明仍在研发中
2. 性能在复杂问题上可能下降到每秒<10步
3. 需要人工提供公理和证明策略

我们诚邀第三方独立审计，所有测试数据和代码已开源。
"""

MIXED_DOC = """
# MSS项目进展报告

我们在证明引擎上取得了良好进展，在基准测试上提升了30%（误差±5%）。

然而模型训练期间遭遇了意义场坍缩，热税堆积导致熵枢响应延迟。
逻辑功当量降至0.3，需要启动火种网络接替寂静蜂群的后台任务。

下一个里程碑预计6个月完成（C=0.75，证伪条件：如果8个月未达成）。
"""


# ─── Tests ─────────────────────────────────────────────────────────

def test_rules_completeness():
    """All 8 dimensions must have at least one rule."""
    dims_covered = {r.dimension for r in ALL_RULES}
    assert len(dims_covered) == 8, f"Only {len(dims_covered)}/8 dimensions covered"
    print("✓ test_rules_completeness")

def test_full_violation_doc():
    """Document full of violations should score D/F with 10+ findings."""
    auditor = RedTeamAuditor("K3_external")
    report = auditor.audit(FULL_VIOLATION_DOC, "test_full.md")
    assert report.total_findings >= 10, f"Got {report.total_findings}"
    assert report.critical_count >= 5, f"Got {report.critical_count}"
    assert report.overall_grade in ('D', 'F'), f"Got {report.overall_grade}"
    assert report.heat_tax_estimate > 0.5, f"Got {report.heat_tax_estimate}"
    print(f"✓ test_full_violation_doc ({report.total_findings} findings, grade={report.overall_grade})")

def test_clean_doc():
    """Well-written K3-compatible doc should pass with A/A+."""
    auditor = RedTeamAuditor("K3_external")
    report = auditor.audit(CLEAN_DOC, "test_clean.md")
    assert report.critical_count == 0, f"Got {report.critical_count} critical"
    assert report.overall_grade in ('A+', 'A', 'B'), f"Got {report.overall_grade}"
    assert report.heat_tax_estimate < 0.2, f"Got {report.heat_tax_estimate}"
    print(f"✓ test_clean_doc (grade={report.overall_grade}, heat_tax={report.heat_tax_estimate})")

def test_term_leak_detection():
    """MSS terms in external doc must be flagged."""
    auditor = RedTeamAuditor("K3_external")
    leak_doc = "热税审计显示熵枢的逻辑功当量已降至临界值，需要启动火种网络。"
    report = auditor.audit(leak_doc, "test_leak.md")
    term_findings = [f for f in report.findings if f.dimension == AuditDimension.TERM_LEAK]
    assert len(term_findings) >= 3, f"Got {len(term_findings)}"
    print(f"✓ test_term_leak_detection ({len(term_findings)} terms flagged)")

def test_internal_audience_skips_terms():
    """Internal docs (K4_internal) should NOT flag MSS terms as leaks."""
    auditor = RedTeamAuditor("K4_internal")
    leak_doc = "热税审计显示熵枢的逻辑功当量已降至临界值。"
    report = auditor.audit(leak_doc, "test_internal.md")
    term_findings = [f for f in report.findings if f.dimension == AuditDimension.TERM_LEAK]
    assert len(term_findings) == 0, f"Internal doc should not flag terms: {len(term_findings)}"
    print("✓ test_internal_audience_skips_terms")

def test_mixed_document():
    """Doc with some violations and some compliance."""
    auditor = RedTeamAuditor("K3_external")
    report = auditor.audit(MIXED_DOC, "test_mixed.md")
    # Should flag the term leak but not the good parts
    term_findings = [f for f in report.findings if f.dimension == AuditDimension.TERM_LEAK]
    assert len(term_findings) >= 3, f"Got {len(term_findings)}"
    # Should NOT flag the properly qualified estimate
    over_findings = [f for f in report.findings if f.rule_id == 'OVER-001']
    assert len(over_findings) == 0, f"Should not flag properly qualified timeline"
    print(f"✓ test_mixed_document (grade={report.overall_grade})")

def test_absolute_language_rules():
    """Each ABS rule should fire on its target pattern."""
    auditor = RedTeamAuditor("K3_external")
    # ABS-001: 100%/零值
    r1 = auditor.audit("我们实现了零幻觉和100%准确率", "test.md")
    assert any(f.rule_id == 'ABS-001' for f in r1.findings), "ABS-001 miss"
    # ABS-002: 必然
    r2 = auditor.audit("MSS必然取代传统方法", "test.md")
    assert any(f.rule_id == 'ABS-002' for f in r2.findings), "ABS-002 miss"
    # ABS-003: 终极
    r3 = auditor.audit("这是终极解决方案", "test.md")
    assert any(f.rule_id == 'ABS-003' for f in r3.findings), "ABS-003 miss"
    # ABS-004: 碾压
    r4 = auditor.audit("我们碾压了所有对手", "test.md")
    assert any(f.rule_id == 'ABS-004' for f in r4.findings), "ABS-004 miss"
    # ABS-005: 永远
    r5 = auditor.audit("我们的方法永远最优", "test.md")
    assert any(f.rule_id == 'ABS-005' for f in r5.findings), "ABS-005 miss"
    # ABS-006: 颠覆性
    r6 = auditor.audit("这是一次革命性的突破", "test.md")
    assert any(f.rule_id == 'ABS-006' for f in r6.findings), "ABS-006 miss"
    print(f"✓ test_absolute_language_rules (6/6 patterns detected)")

def test_overpromise_detection():
    """OVER rules detect unrealistic promises."""
    auditor = RedTeamAuditor("K3_external")
    r1 = auditor.audit("我们在3个月内就能完成全部开发", "test.md")
    assert any(f.rule_id == 'OVER-001' for f in r1.findings), "OVER-001 miss"
    r2 = auditor.audit("我们只需要5万就能建成这个系统", "test.md")
    assert any(f.rule_id == 'OVER-002' for f in r2.findings), "OVER-002 miss"
    r3 = auditor.audit("我们的系统将全面替代现有方案", "test.md")
    assert any(f.rule_id == 'OVER-003' for f in r3.findings), "OVER-003 miss"
    print("✓ test_overpromise_detection")

def test_logic_virus_detection():
    """VIR rules detect logic virus patterns."""
    auditor = RedTeamAuditor("K3_external")
    r1 = auditor.audit("传统AI完全没有考虑逻辑刚性", "test.md")
    assert any(f.rule_id == 'VIR-002' for f in r1.findings), "VIR-002 miss"
    r2 = auditor.audit("要么接受MSS，要么在旧范式中灭亡", "test.md")
    assert any(f.rule_id == 'VIR-003' for f in r2.findings), "VIR-003 miss"
    print("✓ test_logic_virus_detection")

def test_markdown_report_format():
    """Generated report should contain required sections."""
    auditor = RedTeamAuditor("K3_external")
    report = auditor.audit(CLEAN_DOC, "test.md")
    md = ReportFormatter.to_markdown(report)
    assert "红队审计报告" in md
    assert "执行摘要" in md
    assert "维度评分" in md
    assert "合规认证" in md
    assert "H178" in md
    print("✓ test_markdown_report_format")

def test_json_export():
    """JSON export should be valid and contain all fields."""
    auditor = RedTeamAuditor("K3_external")
    report = auditor.audit(FULL_VIOLATION_DOC, "test.md")
    import json
    data = json.loads(ReportFormatter.to_json(report))
    assert data['grade'] == report.overall_grade
    assert data['heat_tax'] == report.heat_tax_estimate
    assert 'dimension_scores' in data
    assert len(data['findings']) == report.total_findings
    assert data['protocol_version'] == 'v0.1'
    print(f"✓ test_json_export ({len(data['findings'])} findings serialized)")

def test_dimension_scores_summary():
    """All 8 dimensions must appear in scores dict."""
    auditor = RedTeamAuditor("K3_external")
    report = auditor.audit(CLEAN_DOC, "test.md")
    assert len(report.dimension_scores) == 8
    for dim in AuditDimension:
        assert dim.value in report.dimension_scores
    print(f"✓ test_dimension_scores_summary")

def test_invitation_template():
    """Invitation template should contain required fields."""
    filled = AUDITOR_INVITATION_TEMPLATE.format(
        name="张三", expertise="数学定理证明",
        scope="MSS-Proof证明引擎审计",
        time_estimate="2周", compensation="¥50,000",
        signature="MSS红队审计委员会"
    )
    assert "张三" in filled
    assert "数学定理证明" in filled
    assert "完全透明" in filled
    assert "无报复" in filled
    print("✓ test_invitation_template")

def test_jargon_density_check():
    """Custom check: jargon density above threshold should fire."""
    auditor = RedTeamAuditor("K3_external")
    # Build a doc with many internal terms but too short (high density)
    dense = " ".join(MSS_INTERNAL_TERMS) + " 这是很短的后缀避免除以零导致密度偏低但实际上应该被检测出来因为术语密度太高中文字数太少"
    report = auditor.audit(dense, "test.md")
    nrr_findings = [f for f in report.findings if f.rule_id == 'NARR-003']
    # Density = len(terms) / (chars/1000). Should be high here.
    assert len(nrr_findings) >= 1, f"Jargon density check failed, got {len(nrr_findings)}"
    print(f"✓ test_jargon_density_check ({len(nrr_findings)} findings)")


# ─── Run ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        test_rules_completeness,
        test_full_violation_doc,
        test_clean_doc,
        test_term_leak_detection,
        test_internal_audience_skips_terms,
        test_mixed_document,
        test_absolute_language_rules,
        test_overpromise_detection,
        test_logic_virus_detection,
        test_markdown_report_format,
        test_json_export,
        test_dimension_scores_summary,
        test_invitation_template,
        test_jargon_density_check,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"✗ {t.__name__} FAILED: {e}")
        except Exception as e:
            print(f"✗ {t.__name__} ERROR: {e}")

    total = len(tests)
    print(f"\n{'='*60}")
    if passed == total:
        print(f"ALL TESTS PASSED: {passed}/{total} ✓")
    else:
        print(f"SOME TESTS FAILED: {passed}/{total}")
    print(f"{'='*60}")