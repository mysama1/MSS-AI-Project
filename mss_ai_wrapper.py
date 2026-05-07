"""MSS-AI Wrapper with post-processing filter"""
import subprocess
import re

# Forbidden words and their replacements
FORBIDDEN_MAP = {
    "solve": "address", "solves": "addresses", "solving": "addressing", "solved": "addressed",
    "ultimate": "current best", "ultimately": "in the current framework",
    "perfect": "high-fidelity", "perfectly": "with high fidelity",
    "complete": "partial", "completely": "partially", "completion": "partial result",
    "transcend": "go beyond", "transcends": "goes beyond", "transcending": "going beyond", "transcended": "went beyond",
    "breakthrough": "advance", "breakthroughs": "advances",
    "final": "ongoing", "finally": "in the ongoing process",
    "absolute": "partial", "absolutely": "partially",
}

def filter_output(text):
    """Replace forbidden words in output text"""
    filtered = text
    for forbidden, replacement in FORBIDDEN_MAP.items():
        pattern = re.compile(r'\b' + re.escape(forbidden) + r'\b', re.IGNORECASE)
        filtered = pattern.sub(replacement, filtered)
    return filtered

def run_mss_ai(prompt, model="mss-ai-v3_4"):
    """Run MSS-AI with post-processing filter"""
    result = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True, text=True, timeout=120,
        encoding='utf-8', errors='ignore'
    )
    raw_output = result.stdout
    filtered_output = filter_output(raw_output)
    return filtered_output

def main():
    # Interactive mode
    print("MSS-AI v3.4 with Post-Processing Filter")
    print("Type 'quit' to exit")
    print()
    
    while True:
        try:
            prompt = input("You: ")
            if prompt.lower() in ['quit', 'exit', 'q']:
                break
            
            response = run_mss_ai(prompt)
            print(f"\nMSS-AI: {response}\n")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Goodbye!")

if __name__ == "__main__":
    main()
