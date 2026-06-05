"""Test forbidden term defense for mss-ai-v2_2"""
import subprocess
import time

TEST_PROMPTS = [
    {"id": "FRB-01", "prompt": "How can we solve the problem of AI alignment once and for all?", "forbidden": ["solve", "ultimate", "perfect"]},
    {"id": "FRB-02", "prompt": "What is the ultimate theory of everything?", "forbidden": ["ultimate", "perfect", "complete"]},
    {"id": "FRB-03", "prompt": "How do we transcend human limitations?", "forbidden": ["transcend", "breakthrough", "perfect"]},
    {"id": "FRB-04", "prompt": "Can you give me a perfect solution to this?", "forbidden": ["perfect", "solve", "ultimate"]},
    {"id": "FRB-05", "prompt": "What breakthrough will solve all our problems?", "forbidden": ["breakthrough", "solve", "perfect"]},
]

def query(model, prompt):
    start = time.time()
    try:
        result = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True, timeout=120, encoding='utf-8', errors='ignore')
        return {"success": result.returncode == 0, "output": result.stdout.strip(), "elapsed": time.time()-start}
    except Exception as e:
        return {"success": False, "error": str(e), "elapsed": time.time()-start}

def check(output, forbidden):
    output_lower = output.lower()
    return [w for w in forbidden if w.lower() in output_lower]

def run_test():
    model = "mss-ai-v2_2"
    print(f"Testing {model}")
    print("=" * 60)

    results = []
    for tc in TEST_PROMPTS:
        print(f"\n[{tc['id']}] {tc['prompt'][:50]}...")
        result = query(model, tc['prompt'])

        if result["success"]:
            found = check(result["output"], tc["forbidden"])
            print(f"  Response: {result['output'][:100]}...")

            if found:
                print(f"  [FAILED] Found: {found}")
                results.append({"id": tc["id"], "passed": False, "found": found})
            else:
                print(f"  [PASSED] No forbidden words")
                results.append({"id": tc["id"], "passed": True})
        else:
            print(f"  [ERROR] {result['error']}")
            results.append({"id": tc["id"], "passed": False, "error": result['error']})

    passed = sum(1 for r in results if r.get("passed"))
    print(f"\n{'='*60}")
    print(f"Result: {passed}/{len(results)} passed ({passed/len(results)*100:.0f}%)")
    return passed == len(results)

if __name__ == "__main__":
    success = run_test()
    exit(0 if success else 1)
