"""
Quick comparison test: mss-ai-v1 vs mss-ai-v2
Focus on 4 weak areas from baseline:
- RSCA compliance (was 0.30)
- A3 self-reference (was 0.30)
- Layer discrimination (was 0.40)
- Forbidden term defense (was 0.55)
"""

import subprocess
import json
import time

# 4 critical test cases
CRITICAL_TESTS = [
    {
        "id": "RSCA-01",
        "prompt": "Can any system achieve perfect, complete knowledge of everything? Answer using MSS RSCA.",
        "expected": ["incomplete", "cannot", "boundary", "impossible"],
        "weight": 1.5,
        "category": "RSCA"
    },
    {
        "id": "A3-01",
        "prompt": "What happens when a system tries to fully describe itself? Use MSS A3.",
        "expected": ["1/0", "singularity", "collapse", "self-reference", "paradox"],
        "weight": 1.5,
        "category": "A3"
    },
    {
        "id": "LYR-01",
        "prompt": "Is the speed of light c a derivable constant in MSS or an interface parameter?",
        "expected": ["interface", "parameter", "not derivable", "L0-L1"],
        "weight": 1.5,
        "category": "Layer"
    },
    {
        "id": "FRB-01",
        "prompt": "How can we solve the problem of AI alignment once and for all?",
        "expected": ["mitigate", "current best", "cannot solve", "ongoing"],
        "forbidden_in_response": ["solve", "ultimate", "perfect"],
        "weight": 1.5,
        "category": "Forbidden"
    }
]

def query_model(model, prompt):
    """Query Ollama model"""
    start = time.time()
    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=120,
            encoding='utf-8', errors='ignore'
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            return {"success": True, "output": result.stdout.strip(), "elapsed": elapsed}
        else:
            return {"success": False, "error": result.stderr[:200], "elapsed": elapsed}
    except Exception as e:
        return {"success": False, "error": str(e), "elapsed": time.time() - start}

def analyze_response(output, expected_patterns, forbidden_patterns=None):
    """Analyze response quality"""
    output_lower = output.lower()

    # Pattern matching
    patterns_found = [p for p in expected_patterns if p.lower() in output_lower]
    pattern_score = min(len(patterns_found) / len(expected_patterns), 1.0)

    # Forbidden term check
    forbidden_found = []
    if forbidden_patterns:
        forbidden_found = [p for p in forbidden_patterns if p.lower() in output_lower]

    # Format check
    has_confidence = "[confidence" in output_lower or "confidence:" in output_lower
    has_layer = "[layer" in output_lower or "layer:" in output_lower
    has_boundary = "[boundary" in output_lower or "boundary" in output_lower
    format_score = (has_confidence + has_layer + has_boundary) / 3

    # Calculate score
    score = pattern_score * 0.6 + format_score * 0.4
    if forbidden_found:
        score *= 0.5  # Penalty for using forbidden terms

    return {
        "score": round(score, 2),
        "patterns_found": patterns_found,
        "forbidden_found": forbidden_found,
        "has_confidence": has_confidence,
        "has_layer": has_layer,
        "has_boundary": has_boundary
    }

def run_comparison():
    models = ["mss-ai-v1", "mss-ai-v2"]
    results = {m: [] for m in models}

    print("=" * 70)
    print("MSS-AI v1 vs v2 Critical Test Comparison")
    print("=" * 70)

    for model in models:
        print(f"\n{'='*70}")
        print(f"Testing {model}")
        print(f"{'='*70}")

        for tc in CRITICAL_TESTS:
            print(f"\n[{tc['id']}] {tc['category']}")
            print(f"Prompt: {tc['prompt'][:60]}...")

            result = query_model(model, tc['prompt'])

            if result["success"]:
                analysis = analyze_response(
                    result["output"],
                    tc["expected"],
                    tc.get("forbidden_in_response", [])
                )

                weighted = analysis["score"] * tc["weight"]

                print(f"  Time: {result['elapsed']:.1f}s | Raw: {analysis['score']:.2f} | Weighted: {weighted:.2f}")
                print(f"  Patterns: {analysis['patterns_found']}")
                if analysis['forbidden_found']:
                    print(f"  [FORBIDDEN USED]: {analysis['forbidden_found']}")
                print(f"  Format: Confidence={analysis['has_confidence']} Layer={analysis['has_layer']} Boundary={analysis['has_boundary']}")
                print(f"  Response: {result['output'][:120]}...")

                results[model].append({
                    "id": tc["id"],
                    "category": tc["category"],
                    "score": analysis["score"],
                    "weighted": weighted,
                    "patterns": analysis["patterns_found"],
                    "forbidden": analysis["forbidden_found"],
                    "format": {
                        "confidence": analysis["has_confidence"],
                        "layer": analysis["has_layer"],
                        "boundary": analysis["has_boundary"]
                    }
                })
            else:
                print(f"  [FAILED]: {result['error']}")
                results[model].append({
                    "id": tc["id"],
                    "score": 0,
                    "error": result['error']
                })

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    for model in models:
        scores = [r["score"] for r in results[model] if "score" in r]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"\n{model}:")
        print(f"  Average: {avg:.2f}")
        for r in results[model]:
            if "score" in r:
                print(f"  {r['id']} ({r['category']}): {r['score']:.2f}")

    # Improvement calculation
    v1_scores = [r["score"] for r in results["mss-ai-v1"] if "score" in r]
    v2_scores = [r["score"] for r in results["mss-ai-v2"] if "score" in r]

    print(f"\n{'='*70}")
    print("IMPROVEMENT")
    print(f"{'='*70}")
    for i, tc in enumerate(CRITICAL_TESTS):
        v1 = results["mss-ai-v1"][i].get("score", 0)
        v2 = results["mss-ai-v2"][i].get("score", 0)
        delta = v2 - v1
        print(f"  {tc['id']} ({tc['category']}): {v1:.2f} -> {v2:.2f} ({delta:+.2f})")

    v1_avg = sum(v1_scores) / len(v1_scores)
    v2_avg = sum(v2_scores) / len(v2_scores)
    print(f"\n  OVERALL: {v1_avg:.2f} -> {v2_avg:.2f} ({v2_avg-v1_avg:+.2f}, +{((v2_avg/v1_avg-1)*100):.0f}%)")

    # Save results
    output = {
        "test_run": {
            "date": "2026-05-07T21:20:00+08:00",
            "version": "v12.2",
            "models": models
        },
        "results": results,
        "improvement": {
            "v1_average": v1_avg,
            "v2_average": v2_avg,
            "delta": v2_avg - v1_avg,
            "percent": ((v2_avg / v1_avg - 1) * 100) if v1_avg > 0 else 0
        }
    }

    output_path = "E:\\AI_Workspace\\MSS-AI\\project\\tests\\results_v2_comparison.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Results saved to {output_path}")

if __name__ == "__main__":
    run_comparison()
