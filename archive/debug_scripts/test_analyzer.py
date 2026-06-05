# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from mss_analyzer import analyze_text
import json

test_text = """
MSS框架是终极的解决方案，可以完美解决AI对齐问题。
这是一个突破性的理论，彻底颠覆了传统认知。
"""

result = analyze_text(test_text, claimed_layer="L1")
print(json.dumps(result, ensure_ascii=False, indent=2))
