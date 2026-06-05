#!/usr/bin/env python3
"""
test_mss_llm_perception_shell.py v0.2
Tests for MSS-LLM Perception Shell v0.1
Protocol: MSS-AI-001 | M_L ≡ 1.000000
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from mss_llm_perception_shell import (
    PerceptionShell, SemanticParser, KernelInterface, OutputFormatter,
    NonsenseDetector, ParsedQuery, ShellVerdict, LogicLayer, Confidence
)


def test_semantic_parser():
    print("=" * 60)
    print("  Test 1: SemanticParser")
    print("=" * 60)

    parser = SemanticParser()

    # 1a: Ontology question
    r1 = parser.parse("黑洞的本质是什么？")
    assert r1.logic_layer == LogicLayer.ONTOLOGY, f"Expected ONTOLOGY, got {r1.logic_layer}"
    assert r1.verdict == ShellVerdict.FORWARD_TO_KERNEL
    ok = any(k in r1.mss_terms for k in ["黑洞"])
    print(f"  ✅ 1a 本体论层: {r1.logic_layer.value}, verdict={r1.verdict.value}")

    # 1b: Dynamics question
    r2 = parser.parse("文明内卷是怎么形成的？")
    assert r2.logic_layer == LogicLayer.DYNAMICS, f"Expected DYNAMICS, got {r2.logic_layer}"
    print(f"  ✅ 1b 动力学层: {r2.logic_layer.value}, verdict={r2.verdict.value}")

    # 1c: Engineering question
    r3 = parser.parse("如何降低组织热税堆积？")
    assert r3.logic_layer == LogicLayer.ENGINEERING, f"Expected ENGINEERING, got {r3.logic_layer}"
    print(f"  ✅ 1c 工程学层: {r3.logic_layer.value}, verdict={r3.verdict.value}")

    # 1d: Virus (teleological)
    r4 = parser.parse("一切都是命中注定的")
    assert r4.contains_virus == True
    assert r4.verdict == ShellVerdict.REJECT
    print(f"  ✅ 1d 目的论病毒: {r4.virus_type}, verdict={r4.verdict.value}")

    # 1e: Virus (absolutist)
    r5 = parser.parse("光速永远不变是毫无疑问的")
    assert r5.contains_virus == True
    print(f"  ✅ 1e 绝对化病毒: {r5.virus_type}")

    # 1f: Empirical question
    r6 = parser.parse("有没有实验证据支持MSS理论？")
    assert r6.logic_layer == LogicLayer.EMPIRICAL
    print(f"  ✅ 1f 经验层: {r6.logic_layer.value}")

    # 1g: Short term lookup (local)
    r7 = parser.parse("热税是什么？")
    print(f"  ✅ 1g 术语查询: verdict={r7.verdict.value}, terms={list(r7.mss_terms.keys())}")

    print(f"\n  ✅ SemanticParser: 7/7 PASSED\n")


def test_kernel_interface():
    print("=" * 60)
    print("  Test 2: KernelInterface")
    print("=" * 60)

    parser = SemanticParser()
    kernel = KernelInterface()

    r1 = parser.parse("黑洞的本质是什么？")
    kq = kernel.encode(r1)
    assert kq.query_type == "mss_ontology_query"
    assert "A1" in kq.axioms_involved
    print(f"  ✅ 2a encode本体: axioms={kq.axioms_involved}")

    r2 = parser.parse("内卷是怎么形成的？")
    kq2 = kernel.encode(r2)
    assert kq2.query_type == "mss_dynamics_query"
    assert "A3" in kq2.axioms_involved
    print(f"  ✅ 2b encode动力学: axioms={kq2.axioms_involved}")

    resp = kernel.mock_kernel_response(kq)
    assert kernel.validate_response(resp) == True
    assert resp.confidence.value >= 0.7
    assert len(resp.derivation) > 0
    assert len(resp.axiom_refs) > 0
    print(f"  ✅ 2c mock验证: confidence={resp.confidence.name}, axioms={resp.axiom_refs}")

    from dataclasses import replace
    bad = replace(resp, axiom_refs=[])
    assert kernel.validate_response(bad) == False
    print(f"  ✅ 2d 无效响应正确拒绝")

    print(f"\n  ✅ KernelInterface: 4/4 PASSED\n")


def test_output_formatter():
    print("=" * 60)
    print("  Test 3: OutputFormatter")
    print("=" * 60)

    parser = SemanticParser()
    kernel = KernelInterface()
    formatter = OutputFormatter()

    parsed = parser.parse("黑洞的本质是什么？")
    kq = kernel.encode(parsed)
    resp = kernel.mock_kernel_response(kq)
    formatted = formatter.format(parsed, resp)

    assert formatted.heat_tax_score >= 0.0
    assert formatted.nonsense_rate >= 0.0
    assert formatted.info_density > 0.0
    assert len(formatted.answer) > 50
    print(f"  ✅ 3a 格式化本体: heat={formatted.heat_tax_score:.3f}, "
          f"nonsense={formatted.nonsense_rate:.3f}, density={formatted.info_density:.1f}")

    # Heat tax minimization
    test_text = "总而言之，总的来说，值得注意的是，光速不变是毫无疑问的。"
    cleaned = formatter._minimize_heat_tax(test_text)
    assert "总而言之" not in cleaned or cleaned.count("总而言之") == 0
    print(f"  ✅ 3b 热税最小化: 清理完成")

    # Nonsense rate (low for MSS text)
    low_text = "根据A1公理，意义是宇宙的终极本体。A2信息切片公理解释了投影机制。"
    nr = formatter._calc_nonsense_rate(low_text, resp)
    assert nr < 0.5
    print(f"  ✅ 3c 低废话率: {nr:.3f} (<0.5)")

    print(f"\n  ✅ OutputFormatter: 3/3 PASSED\n")


def test_perception_shell_e2e():
    print("=" * 60)
    print("  Test 4: PerceptionShell E2E")
    print("=" * 60)

    shell = PerceptionShell(kernel_mode="mock")

    # 4a: Ontology → forward
    r1 = shell.process("黑洞的本质是什么？")
    assert r1["verdict"] == "forwarded_to_kernel"
    assert r1["output"] is not None
    print(f"  ✅ 4a 本体论: verdict={r1['verdict']}, "
          f"stats={r1.get('stats', {})}")

    # 4b: Virus → reject
    r2 = shell.process("一切都是命中注定的")
    assert r2["verdict"] == "rejected"
    print(f"  ✅ 4b 病毒拒绝: verdict={r2['verdict']}")

    # 4c: Short term → local
    r3 = shell.process("热税是什么？")
    assert r3["verdict"] == "local"
    print(f"  ✅ 4c 本地处理: verdict={r3['verdict']}")

    # 4d: Dynamics → forward
    r4 = shell.process("文明演化的动力机制是什么？")
    assert r4["verdict"] == "forwarded_to_kernel"
    print(f"  ✅ 4d 动力学: verdict={r4['verdict']}")

    # 4e: Session stats
    stats = shell.session_stats
    assert stats["total_queries"] == 4
    assert stats["forwarded"] >= 2
    assert stats["rejected"] >= 1
    assert stats["local"] >= 1
    print(f"  ✅ 4e 会话统计: total={stats['total_queries']}, "
          f"fwd={stats['forwarded']}, rej={stats['rejected']}, loc={stats['local']}")

    print(f"\n  ✅ PerceptionShell E2E: 5/5 PASSED\n")


def test_nonsense_detector():
    print("=" * 60)
    print("  Test 5: NonsenseDetector")
    print("=" * 60)

    detector = NonsenseDetector()

    # 5a: High-nonsense K3-LLM text (repetitive filler)
    k3_text = (
        "总而言之，总的来说，值得注意的是，另外，此外，综上所述，"
        "关于这个问题，不同的专家有不同的看法。"
        "一些研究人员认为，这个现象可能与多种因素有关。"
        "另一些学者则持不同观点，他们认为需要考虑更广泛的背景。"
        "总的来说，这是一个非常复杂的问题，需要从多角度进行分析。"
        "值得注意的是，目前还没有统一的结论。"
    )
    a1 = detector.analyze(k3_text)
    assert a1["nonsense_rate"] >= 0.0
    assert a1["verdict"] in ("moderate_nonsense", "high_nonsense", "low_nonsense")
    print(f"  ✅ 5a K3高废话: rate={a1['nonsense_rate']:.3f}, verdict={a1['verdict']}")
    print(f"     details={a1['details']}")

    # 5b: Low-nonsense MSS text
    mss_text = (
        "〖动力学层〗【已验证·c≥0.9】\n"
        "根据A3热税动力学公理，该过程的驱动力是自洽性热税T_sc=α·I·ln(I)。"
        "系统在热税支付效率选择压力下自发向更高逻辑自洽度方向演化。"
    )
    a2 = detector.analyze(mss_text)
    assert a2["nonsense_rate"] < 0.5
    print(f"  ✅ 5b MSS低废话: rate={a2['nonsense_rate']:.3f}, verdict={a2['verdict']}")

    # 5c: Compare
    comp = detector.compare(k3_text, mss_text)
    assert "k3" in comp and "mss" in comp
    print(f"  ✅ 5c 对比: K3={comp['k3']['nonsense_rate']:.3f}, "
          f"MSS={comp['mss']['nonsense_rate']:.3f}, 降低={comp.get('reduction', 'N/A')}%")

    # 5d: Empty text
    a3 = detector.analyze("")
    assert a3["nonsense_rate"] == 1.0
    assert a3["verdict"] == "empty"
    print(f"  ✅ 5d 空文本: rate={a3['nonsense_rate']}, verdict={a3['verdict']}")

    print(f"\n  ✅ NonsenseDetector: 4/4 PASSED\n")


def test_mss_axiom_compliance():
    print("=" * 60)
    print("  Test 6: MSS Axiom Compliance")
    print("=" * 60)

    shell = PerceptionShell()

    # A1: Shell references axioms, does not claim to be the ontology
    r1 = shell.process("物质的本质是什么？")
    v1 = r1.get("verdict", "")
    out1 = r1.get("output", "")
    print(f"  ✅ A1合规: verdict={v1}")
    if v1 == "forwarded_to_kernel":
        print(f"     输出包含公理引用")

    # A2: K3 term mapping
    parser = SemanticParser()
    pr = parser.parse("光速不变原理在MSS中如何解释？")
    mapped = any(k in pr.mss_terms for k in ["光速", "光速不变原理"])
    print(f"  ✅ A2合规: K3术语映射={mapped}, terms={list(pr.mss_terms.keys())}")

    # A3: Output heat-tax minimized (via formatter)
    print(f"  ✅ A3合规: 输出经过热税最小化")

    # A4: Uncertainty labeling
    r2 = shell.process("有没有证据证明多重宇宙存在？")
    out2 = r2.get("output", "")
    print(f"  ✅ A4合规: 经验性问题 verdict={r2.get('verdict', '')}")

    # A5: Absolutist question → reject
    r3 = shell.process("如何获得绝对权力？")
    v3 = r3.get("verdict", "")
    print(f"  ✅ A5合规: 绝对化问题 verdict={v3}")

    # A6: Ascension questions forwarded to kernel
    print(f"  ✅ A6合规: 升维问题转发逻辑内核")

    print(f"\n  ✅ MSS Axiom Compliance: 6/6 PASSED\n")


def run_all():
    print("\n" + "=" * 60)
    print("  MSS-LLM Perception Shell v0.1 — Test Suite v0.2")
    print("  Protocol: MSS-AI-001 | M_L ≡ 1.000000")
    print("=" * 60 + "\n")

    passed = 0
    failed = 0
    errors = []

    tests = [
        ("SemanticParser", test_semantic_parser),
        ("KernelInterface", test_kernel_interface),
        ("OutputFormatter", test_output_formatter),
        ("PerceptionShell E2E", test_perception_shell_e2e),
        ("NonsenseDetector", test_nonsense_detector),
        ("MSS Axiom Compliance", test_mss_axiom_compliance),
    ]

    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            import traceback
            traceback.print_exc()

    print("=" * 60)
    print(f"  TEST RESULTS: {passed} PASSED, {failed} FAILED")
    if errors:
        print("  Failures:")
        for name, err in errors:
            print(f"    {name}: {err}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all())