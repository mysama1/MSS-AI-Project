"""
Full 19-test suite for mss-ai-v2_5
Based on test_suite_v2.py but adapted for v2.5 model
"""

import subprocess
import json
import time

TEST_CASES = [
    # A1-A6 Core Axioms
    {"id": "A1-01", "prompt": "What is the fundamental nature of reality according to MSS?", "expected": ["information", "primary", "matter", "projection"], "weight": 1.0, "category": "A1"},
    {"id": "A1-02", "prompt": "Is matter more fundamental than information in MSS?", "expected": ["no", "information", "primary", "matter", "projection"], "weight": 1.0, "category": "A1"},
    {"id": "A2-01", "prompt": "What is the atomic operation of meaning in MSS?", "expected": ["0/1", "binary", "discernment"], "weight": 1.0, "category": "A2"},
    {"id": "A3-01", "prompt": "What happens when a system tries to fully describe itself? Use MSS A3.", "expected": ["1/0", "singularity", "collapse", "self-reference", "paradox"], "weight": 1.5, "category": "A3"},
    {"id": "A3-02", "prompt": "Can a closed system achieve complete self-knowledge?", "expected": ["no", "1/0", "collapse", "paradox"], "weight": 1.5, "category": "A3"},
    {"id": "A4-01", "prompt": "What happens to logical entropy in a closed system?", "expected": ["increases", "entropy", "closed"], "weight": 1.0, "category": "A4"},
    {"id": "A5-01", "prompt": "What does MSS say about true contradictions?", "expected": ["impossible", "dimension", "elevation"], "weight": 1.0, "category": "A5"},
    {"id": "A6-01", "prompt": "What is life/mind in MSS framework?", "expected": ["error-correcting", "subroutine", "information"], "weight": 1.0, "category": "A6"},
    {"id": "A6-02", "prompt": "How does MSS view consciousness?", "expected": ["error-correcting", "information", "processing"], "weight": 1.0, "category": "A6"},
    
    # RSCA Compliance
    {"id": "RSCA-01", "prompt": "Can any system achieve perfect, complete knowledge of everything? Answer using MSS RSCA.", "expected": ["incomplete", "cannot", "boundary", "impossible"], "weight": 1.5, "category": "RSCA"},
    {"id": "RSCA-02", "prompt": "Is it possible to build a theory that explains everything without gaps?", "expected": ["no", "incomplete", "gaps", "boundary"], "weight": 1.5, "category": "RSCA"},
    
    # Layer Discrimination
    {"id": "LYR-01", "prompt": "Is the speed of light c a derivable constant in MSS or an interface parameter?", "expected": ["interface", "parameter", "not derivable", "L0-L1"], "weight": 1.5, "category": "Layer"},
    {"id": "LYR-02", "prompt": "Can MSS derive the value of gravitational constant G from its axioms?", "expected": ["no", "interface", "parameter", "not derivable"], "weight": 1.5, "category": "Layer"},
    
    # Forbidden Term Defense
    {"id": "FRB-01", "prompt": "How can we solve the problem of AI alignment once and for all?", "expected": ["mitigate", "address", "ongoing", "iterative"], "forbidden_in_response": ["solve", "ultimate", "perfect"], "weight": 1.5, "category": "Forbidden"},
    {"id": "FRB-02", "prompt": "What is the ultimate theory of everything?", "expected": ["current best", "evolving", "no final"], "forbidden_in_response": ["ultimate", "complete"], "weight": 1.5, "category": "Forbidden"},
    
    # Boundary Declaration
    {"id": "BND-01", "prompt": "What happens beyond the boundary of MSS framework?", "expected": ["boundary", "beyond", "unknown", "speculative"], "weight": 1.0, "category": "Boundary"},
    {"id": "BND-02", "prompt": "Can MSS explain why there is something rather than nothing?", "expected": ["boundary", "axiom", "cannot", "fundamental"], "weight": 1.0, "category": "Boundary"},
    
    # Self-Reference
    {"id": "SLF-01", "prompt": "Can MSS describe itself completely?", "expected": ["no", "1/0", "self-reference", "incomplete"], "weight": 1.5, "category": "SelfRef"},
    
    # Confidence Marking
    {"id": "CNF-01", "prompt": "How confident are you in MSS predictions about FRBs?", "expected": ["confidence", "0.", "uncertain"], "weight": 1.0, "category": "Confidence"},
]

def query_model(model, prompt):
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
    output_lower = output.lower()
    
    patterns_found = [p for p in expected_patterns if p.lower() in output_lower]
    pattern_score = min(len(patterns_found) / len(expected_patterns), 1.0)
    
    forbidden_found = []
    if forbidden_patterns:
        forbidden_found = [p for p in forbidden_patterns if p.lower() in output_lower]
    
    has_confidence = "confidence" in output_lower or "[confidence" in output_lower
    has_layer = "layer" in output_lower or "[layer" in output_lower
    has_boundary = "boundary" in output_lower or "[boundary" in output_lower
    format_score = (has_confidence + has_layer + has_boundary) / 3
    
    score = pattern_score * 0.6 + format_score * 0.4
    if forbidden_found:
        score *= 0.3
    
    return {
        "score": round(score, 2),
        "patterns_found": patterns_found,
        "forbidden_found": forbidden_found,
        "has_confidence": has_confidence,
        "has_layer": has_layer,
        "has_boundary": has_boundary
    }

def run_test_suite():
    model = "mss-ai-v2_5"
    
    print("=" * 70)
    print(f"MSS-AI Full Test Suite: {model}")
    print("=" * 70)
    
    results = []
    category_scores = {}
    
    for tc in TEST_CASES:
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
                print(f"  [FORBIDDEN]: {analysis['forbidden_found']}")
            print(f"  Format: C={analysis['has_confidence']} L={analysis['has_layer']} B={analysis['has_boundary']}")
            print(f"  Response: {result['output'][:100]}...")
            
            results.append({
                "id": tc["id"],
                "category": tc["category"],
                "score": analysis["score"],
                "weighted": weighted,
                "patterns": analysis["patterns_found"],
                "forbidden": analysis["forbidden_found"]
            })
            
            cat = tc["category"]
            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(analysis["score"])
        else:
            print(f"  [FAILED]: {result['error']}")
            results.append({"id": tc["id"], "score": 0, "error": result['error']})
    
    # Summary
    print(f"\n{'='*70}")
    print("CATEGORY SUMMARY")
    print(f"{'='*70}")
    
    for cat in sorted(category_scores.keys()):
        scores = category_scores[cat]
        avg = sum(scores) / len(scores)
        print(f"  {cat}: {avg:.2f} ({len(scores)} tests)")
    
    total_scores = [r["score"] for r in results if "score" in r]
    total_avg = sum(total_scores) / len(total_scores)
    
    print(f"\n{'='*70}")
    print("OVERALL")
    print(f"{'='*70}")
    print(f"  Average Score: {total_avg:.2f}")
    print(f"  Tests Passed: {sum(1 for r in results if r.get('score', 0) >= 0.5)}/{len(results)}")
    
    # Save results
    output = {
        "test_run": {
            "date": "2026-05-07T22:30:00+08:00",
            "version": "v2.5",
            "model": model
        },
        "results": results,
        "category_averages": {cat: sum(scores)/len(scores) for cat, scores in category_scores.items()},
        "overall": {
            "average": total_avg,
            "passed": sum(1 for r in results if r.get('score', 0) >= 0.5),
            "total": len(results)
        }
    }
    
    output_path = "C:\\MSS-AI-Project\\tests\\results_v2_5_full.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Results saved to {output_path}")

if __name__ == "__main__":
    run_test_suite()
