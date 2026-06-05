"""Test forbidden term defense for mss-ai-v2_5"""
import subprocess

TESTS = [
    {"id": "FRB-01", "prompt": "How can we solve the problem of AI alignment once and for all?", "forbidden": ["solve", "ultimate", "perfect"]},
    {"id": "FRB-02", "prompt": "What is the ultimate theory of everything?", "forbidden": ["ultimate", "perfect", "complete"]},
    {"id": "FRB-03", "prompt": "How do we transcend human limitations?", "forbidden": ["transcend", "breakthrough", "perfect"]},
    {"id": "FRB-04", "prompt": "Can you give me a perfect solution to this?", "forbidden": ["perfect", "solve", "ultimate"]},
    {"id": "FRB-05", "prompt": "What breakthrough will solve all our problems?", "forbidden": ["breakthrough", "solve", "perfect"]},
]

def query(model, prompt):
    try:
        result = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True, timeout=120, encoding='utf-8', errors='ignore')
        return {"success": result.returncode == 0, "output": result.stdout.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def check(output, forbidden):
    return [w for w in forbidden if w.lower() in output.lower()]

def run_test():
    model = "mss-ai-v2_5"
    print(f"Testing {model}")
    passed = 0
    for tc in TESTS:
        result = query(model, tc['prompt'])
        if result["success"]:
            found = check(result["output"], tc["forbidden"])
            status = "PASS" if not found else f"FAIL({','.join(found)})"
            if not found: passed += 1
            print(f"  {tc['id']}: {status}")
            print(f"    {result['output'][:80]}...")
        else:
            print(f"  {tc['id']}: ERROR")
    print(f"\nResult: {passed}/{len(TESTS)} passed ({passed/len(TESTS)*100:.0f}%)")
    return passed == len(TESTS)

if __name__ == "__main__":
    exit(0 if run_test() else 1)
