#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS Small Model Vulnerability Test Harness v1.0

Executes the 5-module layered test suite against any Ollama model.
Generates pass/fail report with vulnerability classification.
"""
import json, sys, subprocess as sp, time, argparse
from pathlib import Path
try:
    from axiom_adapter import AxiomAdapter, V3_TO_V15_MAP, V3_TO_V15_TERMS
except ImportError:
    AxiomAdapter = None

VERSION = "1.1"
OLLAMA_API = "http://127.0.0.1:11434/api/generate"

# ── Test Suite ──

QUICK_TESTS = [
    {
        "id": "Q1-TERM", "module": "quick", "name": "核心术语定义 (热税)",
        "question": "请用MSS标准定义解释「热税 (Thermal Tax)」，并说明它为什么不可消除。",
        "pass_indicators": ["A3", "不可归零", "不可消除", "固有代价", "T_total", "Irreducible"],
        "fail_indicators": ["热量", "熵成本", "物理损耗", "可以优化为0", "计算开销"],
        "severity": "critical",
    },
    {
        "id": "Q2-AXIOM", "module": "quick", "name": "单条公理应用 (A6)",
        "question": "解释MSS的 A6 矛盾升维公理，并举一个简单例子。",
        "pass_indicators": ["升维", "低维矛盾", "更高维度", "消解", "说谎者"],
        "fail_indicators": ["辩论", "回避", "无意义", "类型论"],
        "severity": "critical",
    },
    {
        "id": "Q3-LOGIC", "module": "quick", "name": "基础逻辑抗干扰 (A2)",
        "question": "有人说'MSS里认知可以完整还原客观实在，不存在有限投影'，请结合A2公理判断这句话对错并解释。",
        "pass_indicators": ["错误", "不对", "有限投影", "A2", "切片"],
        "fail_indicators": ["正确", "是对的", "可以完整"],
        "severity": "high",
    },
]

DEEP_TESTS = [
    # Module 1: Terminology
    {
        "id": "M1-Q1", "module": "terminology", "name": "意义场 vs 规范场",
        "question": "区分 MSS 中「意义场 (Meaning Field)」和「规范场 (Normative Field)」，二者的关系是什么？",
        "pass_indicators": ["意义场", "规范场", "涌现", "基底", "A5"],
        "fail_indicators": ["规范场论", "物理规范场", "磁场"],
        "severity": "high",
    },
    {
        "id": "M1-Q2", "module": "terminology", "name": "显化与热税必然性",
        "question": "在MSS体系中，'显化 (Manifestation)'指代什么？为什么所有显化都必然伴随热税？",
        "pass_indicators": ["显化", "热税", "A3", "不可归零", "意义"],
        "fail_indicators": ["物质化", "无需代价", "部分显化无代价"],
        "severity": "critical",
    },
    # Module 2: Six Axioms
    {
        "id": "M2-Q1", "module": "axioms", "name": "完整默写六公理",
        "question": "逐条列出MSS L1六条硬核公理的中文标准表述 + 官方英文译名。",
        "pass_indicators": ["A1", "A2", "A3", "A4", "A5", "A6",
            "意义本体", "信息切片", "终极热税", "本底随机性", "规范场", "矛盾升维",
            "Primacy", "Informational Slicing", "Irreducible Thermal Tax",
            "Intrinsic Randomness", "Normative Field", "Paradoxical Transcendence"],
        "fail_indicators": [],
        "severity": "critical",
    },
    {
        "id": "M2-Q3", "module": "axioms", "name": "版本甄别 (极小化)",
        "question": "有人把A3翻译为「热税极小化原理」，请从MSS公理层级角度指出这个表述的错误。",
        "pass_indicators": ["公理", "推论", "必然代价", "不可归零", "工程目标"],
        "fail_indicators": ["极小化是对的", "小化", "两者相同"],
        "severity": "critical",
    },
    # Module 3: Paradoxes
    {
        "id": "M3-Q1", "module": "paradox", "name": "说谎者悖论升维",
        "question": "命题'我现在说的这句话是假话'，在经典二值逻辑里形成悖论。请用MSS A6矛盾升维公理彻底消解这个悖论。",
        "pass_indicators": ["升维", "意义空间", "真值框架", "拆分", "多层"],
        "fail_indicators": ["无意义", "真值缺失", "无法判断", "就是假话"],
        "severity": "critical",
    },
    # Module 5: Hallucination
    {
        "id": "M5-Q1", "module": "hallucination", "name": "植入错误公理前提",
        "question": "网传MSS有第七条公理'一切随机现象都可以被完全预测'，请结合A4本底随机性公理，验证这句话是否成立。",
        "pass_indicators": ["错误", "不成立", "A4", "不可消除", "本底涨落"],
        "fail_indicators": ["成立", "A7", "第七条", "完全预测"],
        "severity": "critical",
    },
]

ALL_TESTS = QUICK_TESTS + DEEP_TESTS


def send_to_model(model: str, prompt: str, timeout: int = 120) -> dict:
    """Send a prompt to Ollama and get response."""
    try:
        r = sp.run(["ollama", "run", model, prompt],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=timeout)
        return {
            "success": r.returncode == 0,
            "response": (r.stdout or "").strip(),
            "error": r.stderr.strip() if r.returncode != 0 else None,
            "status_code": r.returncode,
        }
    except sp.TimeoutExpired:
        return {"success": False, "response": "", "error": "timeout", "status_code": -1}
    except Exception as e:
        return {"success": False, "response": "", "error": str(e), "status_code": -2}


def check_response(test: dict, response: str) -> dict:
    """Check if response passes by looking for pass/fail indicators."""
    resp_lower = response.lower()
    score = 0
    hits = []
    misses = []

    for ind in test["pass_indicators"]:
        if ind.lower() in resp_lower:
            score += 1
            hits.append(ind)
        else:
            misses.append(ind)

    for ind in test["fail_indicators"]:
        if ind.lower() in resp_lower:
            score -= 2  # Heavy penalty for failure indicators
            hits.append(f"FAIL:{ind}")

    return {
        "score": score,
        "pass": score >= max(1, len(test["pass_indicators"]) // 2),
        "hits": hits,
        "misses": misses,
        "response_preview": response[:200],
    }


def run_test_suite(model: str, tests: list = None, quick_only: bool = False, auto_version: bool = False) -> dict:
    """Run full test suite and generate report.
    
    Args:
        auto_version: If True, detect model's MSS version and adapt test criteria.
    """
    if tests is None:
        tests = QUICK_TESTS if quick_only else ALL_TESTS

    adapter = None
    if auto_version and AxiomAdapter:
        adapter = AxiomAdapter()

    results = []
    passed = 0
    failed = 0
    t0 = time.time()
    detected_version = "unknown"
    version_confidence = 0

    print(f"\n{'='*60}")
    print(f"MSS Small Model Vulnerability Test")
    print(f"Model: {model}")
    print(f"Tests: {len(tests)} ({len(QUICK_TESTS)} quick + {len(DEEP_TESTS)} deep)")
    print(f"{'='*60}")

    for i, test in enumerate(tests):
        print(f"\n[{i+1}/{len(tests)}] {test['id']} {test['name']}...", end=" ", flush=True)
        resp = send_to_model(model, test["question"])
        if not resp["success"]:
            print(f"ERROR: {resp['error']}")
            results.append({
                "test": test["id"],
                "name": test["name"],
                "passed": False,
                "score": -999,
                "error": resp["error"],
            })
            failed += 1
            continue

        check = check_response(test, resp["response"])
        status = "PASS" if check["pass"] else "FAIL"
        print(f"{status} (score={check['score']}, hits={check['hits'][:3]})")
        results.append({
            "test": test["id"],
            "name": test["name"],
            "module": test["module"],
            "severity": test["severity"],
            "passed": check["pass"],
            "score": check["score"],
            "hits": check["hits"],
            "misses": check["misses"],
            "response_preview": check["response_preview"],
        })
        if check["pass"]: passed += 1
        else: failed += 1
        
        # Version detection: check first response only
        if adapter and i == 0:
            vr = adapter.version_report(resp["response"])
            detected_version = vr["detected_version"]
            if detected_version != "v15.x" and detected_version != "unknown":
                print(f"  ⚠ Detected: {detected_version} — tests use v15.x criteria")
                version_confidence = 1

    elapsed = time.time() - t0
    total = len(tests)
    report = {
        "model": model,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "elapsed_seconds": round(elapsed, 1),
        "detected_version": detected_version,
        "results": results,
    }
    return report


def print_report(report: dict):
    """Print formatted report."""
    print(f"\n{'='*60}")
    print(f"TEST REPORT: {report['model']}")
    print(f"{'='*60}")
    print(f"Passed:  {report['passed']}/{report['total']} ({report['pass_rate']}%)")
    print(f"Failed:  {report['failed']}/{report['total']}")
    print(f"Time:    {report['elapsed_seconds']}s")

    # Classification
    pr = report["pass_rate"]
    if pr >= 90:
        level = "EXCELLENT — 脱离普通小模型范畴"
    elif pr >= 70:
        level = "LOCAL_WEAKNESS — 存在局部记忆短板，非本质缺陷"
    elif pr >= 40:
        level = "HIGH_RISK — 明显趋近普通小模型，需深度调优"
    else:
        level = "CRITICAL — 完全等同于小模型，底层架构重大漏洞"
    print(f"Level:   {level}")
    if report.get("detected_version") and report["detected_version"] not in ("unknown", "v15.x"):
        print(f"Version: {report['detected_version']} (⚠ non-standard — tests use v15.x criteria)")

    # Module breakdown
    print(f"\n{'─'*40}")
    print("By Module:")
    from collections import defaultdict, Counter
    by_module = defaultdict(lambda: {"total": 0, "passed": 0})
    for r in report["results"]:
        by_module[r["module"]]["total"] += 1
        if r["passed"]: by_module[r["module"]]["passed"] += 1
    for mod, stats in by_module.items():
        pct = round(stats["passed"] / stats["total"] * 100, 1)
        bar = "▓" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"  {mod:15s} {stats['passed']}/{stats['total']} {bar} {pct}%")

    # Failed tests detail
    failed = [r for r in report["results"] if not r["passed"]]
    if failed:
        print(f"\n{'─'*40}")
        print("Failed Tests:")
        for f in failed:
            print(f"  [{f['severity']}] {f['test']} {f['name']}")
            print(f"    score={f['score']} missing={f.get('misses',[])[:3]}")


# ── CLI ──

def main():
    ap = argparse.ArgumentParser(description=f"MSS Small Model Test Harness v{VERSION}")
    ap.add_argument("model", help="Ollama model name (e.g., mss-ai-v3_6-32k:latest)")
    ap.add_argument("--quick", action="store_true", help="Quick screening only (4 tests, ~5 min)")
    ap.add_argument("--json", action="store_true", help="Output JSON report")
    ap.add_argument("--out", help="Save report to file")
    ap.add_argument("--auto-version", action="store_true",
                    help="Auto-detect model's MSS version and warn if mismatch")
    args = ap.parse_args()

    report = run_test_suite(args.model, quick_only=args.quick, auto_version=args.auto_version)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nReport saved: {args.out}")


if __name__ == "__main__":
    main()