#!/usr/bin/env python3
"""MSS Analyze CLI — pipe text to get axiom-level analysis."""
import sys, subprocess, os

MSS_PROMPT = """Analyze the following input through MSS (Meaning Supremacy System) lens:
1. Which of A1-A6 axioms are most relevant?
2. Is there a dimensional issue (L0 physical / L1 logical / L2 meaning)?
3. Is there a hidden closed objective or debate trap?
4. What would A6 elevation suggest?

Keep it concise. Always include [Confidence] tag.

Input:
"""

def analyze(text, model=None):
    model = model or os.environ.get('MSS_MODEL', 'mss-ai-v3.4.3-balanced')
    prompt = MSS_PROMPT + text
    
    try:
        r = subprocess.run(
            ['ollama', 'run', model, prompt],
            capture_output=True, text=True, encoding='utf-8',
            timeout=120
        )
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[ERROR: Model timeout]"
    except FileNotFoundError:
        return "[ERROR: Ollama not found. Install: https://ollama.com]"
    except Exception as e:
        return f"[ERROR: {e}]"

def main():
    import argparse
    p = argparse.ArgumentParser(description='MSS Analyze — axiom-level analysis of any text')
    p.add_argument('text', nargs='*', help='Text to analyze. If omitted, reads from stdin.')
    p.add_argument('--model', '-m', help='Ollama model name (default: mss-ai-v3.4.3-balanced)')
    p.add_argument('--pipe', action='store_true', help='Read from stdin')
    args = p.parse_args()
    
    if args.pipe or not args.text:
        text = sys.stdin.read()
    else:
        text = ' '.join(args.text)
    
    if not text.strip():
        print("Usage: vdp-analyze 'text to analyze'")
        print("   or: echo 'text' | vdp-analyze --pipe")
        sys.exit(1)
    
    result = analyze(text, model=args.model)
    print(result)

if __name__ == '__main__':
    main()
