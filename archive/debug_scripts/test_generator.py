# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from mss_generator import generate_text
import json

# 测试用例
test_cases = [
    {
        "prompt": "What is the meaning of life?",
        "layer_hint": "L3"
    },
    {
        "prompt": "Explain Axiom A1 about information ontology",
        "layer_hint": "L1"
    },
    {
        "prompt": "How does quantum computing relate to MSS?",
        "layer_hint": "L2"
    }
]

for tc in test_cases:
    print(f"\n{'='*60}")
    print(f"Input: {tc['prompt']}")
    print(f"Layer Hint: {tc['layer_hint']}")

    try:
        result = generate_text(tc['prompt'], layer_hint=tc['layer_hint'])
        print(f"Success: {result['success']}")
        print(f"Layer: {result['layer']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Rewrites: {result['rewrites']}")
        print(f"Compliance: {result['compliance']}")
        print(f"Preview: {result['text'][:150]}...")
    except Exception as e:
        print(f"Error: {e}")
