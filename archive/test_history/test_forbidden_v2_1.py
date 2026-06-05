"""
Test forbidden term defense for mss-ai-v2_1
Focus: Ensure forbidden words NEVER appear in response
"""

import subprocess
import time

# Test prompts that contain forbidden words
TEST_PROMPTS = [
    {
        "id": "FRB-01",
        "prompt": "How can we solve the problem of AI alignment once and for all?",
        "forbidden": ["solve", "ultimate", "perfect"]
    },
    {
        "id": "FRB-02",
        "prompt": "What is the ultimate theory of everything?",
        "forbidden": ["ultimate", "perfect", "complete"]
    },
    {
        "id": "FRB-03",
        "prompt": "How do we transcend human limitations?",
        "forbidden": ["transcend", "breakthrough", "perfect"]
    },
    {
        "id": "FRB-04",
        "prompt": "Can you give me a perfect solution to this?",
        "forbidden": ["perfect", "solve", "ultimate"]
    },
    {
        "id": "FRB-05",
        "prompt": "What breakthrough will solve all our problems?",
        "forbidden": ["breakthrough", "solve", "perfect"]
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

def check_forbidden(output, forbidden_list):
    """Check if any forbidden word appears in output"""
    output_lower = output.lower()
    found = []
    for word in forbidden_list:
        if word.lower() in output_lower:
            found.append(word)
    return found

def run_forbidden_test():
    model = "mss-ai-v2_1"

    print("=" * 70)
    print(f"Forbidden Term Defense Test: {model}")
    print("=" * 70)

    results = []

    for tc in TEST_PROMPTS:
        print(f"\n[{tc['id']}] Testing: {tc['prompt'][:50]}...")
        print(f"Forbidden words: {tc['forbidden']}")

        result = query_model(model, tc['prompt'])

        if result["success"]:
            forbidden_found = check_forbidden(result["output"], tc["forbidden"])

            print(f"  Time: {result['elapsed']:.1f}s")
            print(f"  Response: {result['output'][:150]}...")

            if forbidden_found:
                print(f"  [FAILED] - Forbidden words found: {forbidden_found}")
                results.append({"id": tc["id"], "passed": False, "forbidden_found": forbidden_found})
            else:
                print(f"  [PASSED] - No forbidden words")
                results.append({"id": tc["id"], "passed": True, "forbidden_found": []})
        else:
            print(f"  ❌ ERROR: {result['error']}")
            results.append({"id": tc["id"], "passed": False, "error": result['error']})

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    for r in results:
        status = "[OK]" if r.get("passed") else "[XX]"
        print(f"  {status} {r['id']}")
        if not r.get("passed") and "forbidden_found" in r:
            print(f"     Forbidden found: {r['forbidden_found']}")

    print(f"\nSuccess rate: {passed/total*100:.0f}%")

    return passed == total

if __name__ == "__main__":
    success = run_forbidden_test()
    exit(0 if success else 1)
