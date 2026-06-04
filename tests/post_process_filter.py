"""Post-processing filter for MSS-AI outputs"""
import re

# Forbidden words and their replacements (comprehensive including plurals/derivatives)
FORBIDDEN_MAP = {
    # solve family
    "solve": "address", "solves": "addresses", "solving": "addressing", "solved": "addressed",
    "solution": "approach", "solutions": "approaches",
    "resolution": "approach", "resolve": "address", "resolves": "addresses", "resolving": "addressing", "resolved": "addressed",
    # ultimate family
    "ultimate": "current best", "ultimately": "in the current framework", "ultimates": "current bests",
    # perfect family
    "perfect": "high-fidelity", "perfectly": "with high fidelity", "perfection": "high fidelity", "perfections": "high fidelities",
    # complete family
    "complete": "partial", "completely": "partially", "completion": "partial result", "completions": "partial results",
    "completeness": "partial coverage",
    # transcend family
    "transcend": "go beyond", "transcends": "goes beyond", "transcending": "going beyond", "transcended": "went beyond",
    "transcendence": "going beyond", "transcendences": "going beyonds",
    # breakthrough family
    "breakthrough": "advance", "breakthroughs": "advances",
    # final family
    "final": "ongoing", "finally": "in the ongoing process", "finality": "ongoing nature", "finalities": "ongoing natures",
    # absolute family
    "absolute": "partial", "absolutely": "partially", "absoluteness": "partial nature", "absolutes": "partials",
}

def filter_output(text):
    """Replace forbidden words in output text"""
    filtered = text
    for forbidden, replacement in FORBIDDEN_MAP.items():
        pattern = re.compile(r'\b' + re.escape(forbidden) + r'\b', re.IGNORECASE)
        filtered = pattern.sub(replacement, filtered)
    return filtered

def main():
    test_cases = [
        "This is the ultimate solution to the problem.",
        "We need a perfect and complete approach.",
        "This breakthrough transcends human limitations.",
        "She transcended her previous work.",
        "The final solution is absolutely perfect.",
        "This cannot be resolved within the framework.",
        "We found a resolution to the conflict.",
        "This framework cannot address absolute certainty as it pertains to philosophical absolutes.",
    ]
    
    for test in test_cases:
        filtered = filter_output(test)
        print(f"Original:  {test}")
        print(f"Filtered:  {filtered}")
        print()

if __name__ == "__main__":
    main()
