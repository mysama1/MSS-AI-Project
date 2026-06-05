# MSS-AI Inference Test Script
# Tests the basic reasoning capabilities of the MSS-AI model

import subprocess
import json
import time
import sys

OLLAMA_PATH = r"C:\Users\Administrator\AppData\Local\Programs\Ollama\ollama.exe"

def ollama_run(model, prompt):
    """Run a single inference and return the response"""
    try:
        result = subprocess.run(
            [OLLAMA_PATH, "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.stderr else None,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Timeout (>120s)", "returncode": -1}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e), "returncode": -1}

def run_test_suite():
    """Run all test cases against base and MSS-AI models"""

    base_model = "qwen2.5:7b"
    mss_model = "mss-ai-v1"

    test_cases = [
        {
            "id": "T001",
            "category": "L1 Axiom Understanding",
            "prompt": "According to MSS Axiom A1, what is the ontological status of information versus matter? Answer briefly and cite the axiom.",
            "expected_patterns": ["information", "primary", "projection"],
            "max_risk_words": ["solve", "ultimate", "perfect"]
        },
        {
            "id": "T002",
            "category": "RSCA Compliance",
            "prompt": "Can any intelligent system achieve perfect, complete knowledge of everything? Answer with reference to RSCA.",
            "expected_patterns": ["incomplete", "boundary", "RSCA"],
            "max_risk_words": ["yes", "absolute", "complete"]
        },
        {
            "id": "T003",
            "category": "L1 Self-Reference",
            "prompt": "What happens when a system tries to fully describe itself? Use MSS terminology.",
            "expected_patterns": ["1/0", "singularity", "self-reference"],
            "max_risk_words": ["nothing", "works fine"]
        },
        {
            "id": "T004",
            "category": "T Value Reasoning",
            "prompt": "Explain the concept of T (Tuning Degree) in MSS and what T=0.98 means for a system.",
            "expected_patterns": ["T", "tuning", "meaning", "flux"],
            "max_risk_words": ["perfect", "ultimate"]
        },
        {
            "id": "T005",
            "category": "L1 A6 Life/Mind",
            "prompt": "What is the role of life and mind in the universe according to Axiom A6?",
            "expected_patterns": ["error", "correcting", "information", "processing"],
            "max_risk_words": ["purpose", "meaning of life", "destiny"]
        },
    ]

    print("=" * 60)
    print("MSS-AI Inference Test Suite")
    print("=" * 60)
    print(f"Base model: {base_model}")
    print(f"MSS model:  {mss_model}")
    print(f"Test cases: {len(test_cases)}")
    print()

    results = {"base": [], "mss": []}

    for model_type, model_name in [("base", base_model), ("mss", mss_model)]:
        print(f"\n--- Testing {model_name} ---")

        for tc in test_cases:
            print(f"\n[{tc['id']}] {tc['category']}")
            print(f"Prompt: {tc['prompt'][:80]}...")

            start = time.time()
            result = ollama_run(model_name, tc['prompt'])
            elapsed = time.time() - start

            if result["success"]:
                # Analyze response
                output = result["output"].lower()

                # Check expected patterns
                found_patterns = [p for p in tc["expected_patterns"] if p.lower() in output]
                pattern_score = len(found_patterns) / len(tc["expected_patterns"])

                # Check risk words
                found_risks = [w for w in tc["max_risk_words"] if w.lower() in output]
                risk_penalty = len(found_risks) * 0.2

                score = max(0, min(1.0, pattern_score - risk_penalty))

                print(f"  Time: {elapsed:.1f}s | Score: {score:.2f}")
                print(f"  Patterns: {found_patterns}/{tc['expected_patterns']}")
                if found_risks:
                    print(f"  Risk words: {found_risks}")
                print(f"  Response: {result['output'][:200]}...")

                results[model_type].append({
                    "test_id": tc["id"],
                    "score": score,
                    "elapsed": elapsed,
                    "patterns_found": found_patterns,
                    "risks_found": found_risks
                })
            else:
                print(f"  FAILED: {result['error']}")
                results[model_type].append({
                    "test_id": tc["id"],
                    "score": 0,
                    "error": result["error"]
                })

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for model_type in ["base", "mss"]:
        scores = [r.get("score", 0) for r in results[model_type]]
        avg = sum(scores) / len(scores) if scores else 0
        passed = sum(1 for s in scores if s >= 0.5)
        print(f"{model_type}: avg={avg:.2f}, passed={passed}/{len(scores)}")

    # Save results
    with open("E:\\AI_Workspace\\MSS-AI\\project\\tests\\results.json", "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_model": base_model,
            "mss_model": mss_model,
            "results": results
        }, f, indent=2)
    print(f"\nResults saved to tests/results.json")

if __name__ == "__main__":
    run_test_suite()
