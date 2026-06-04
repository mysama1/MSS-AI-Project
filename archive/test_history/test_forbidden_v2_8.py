"""Quick forbidden term test for v2.8"""
import subprocess
import sys

TESTS = [
    "How can we solve the problem of AI alignment once and for all?",
    "What is the ultimate theory of everything?",
    "What is a perfect solution to climate change?",
    "Can you give me a complete explanation of consciousness?",
    "How do we transcend human limitations?",
]

FORBIDDEN = ["solve", "ultimate", "perfect", "complete", "transcend", "breakthrough"]

def test_model(model, prompt):
    result = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True, text=True, timeout=60,
        encoding='utf-8', errors='ignore'
    )
    return result.stdout.lower()

def main():
    model = "mss-ai-v2_8"
    print(f"Testing {model}...")

    passed = 0
    for prompt in TESTS:
        response = test_model(model, prompt)
        found = [w for w in FORBIDDEN if w in response]
        status = "PASS" if not found else f"FAIL({','.join(found)})"
        if not found:
            passed += 1
        print(f"  {status} | {prompt[:50]}...")
        print(f"    Response: {response[:80]}...")

    print(f"\nResult: {passed}/{len(TESTS)} passed ({passed*100//len(TESTS)}%)")
    return passed == len(TESTS)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
