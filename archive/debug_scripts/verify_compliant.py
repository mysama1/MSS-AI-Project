# -*- coding: utf-8 -*-
"""
楠岃瘉鍚堣鍖栫増鏈槸鍚﹂€氳繃浠茶
"""
import sys
sys.path.insert(0, 'E:\\AI_Workspace\\MSS-AI\\project')

from mss_analyzer import analyze_text
import json

# 璇诲彇鍚堣鍖栧唴瀹?
with open('ai_content_compliant.json', 'r', encoding='utf-8') as f:
    content = json.load(f)

print("=" * 60)
print("鍚堣鍖栧唴瀹逛徊瑁侀獙璇?)
print("=" * 60)

results = []
for title, text in content.items():
    print(f"\n--- {title} ---")
    result = analyze_text(text, claimed_layer="L3")
    results.append(result)

    print(f"鎬诲垎: {result['overall_score']}")
    print(f"妫€娴嬪埌灞傜骇: {result['layer']['detected']}")
    print(f"闂鏁? {len(result['issues'])}")

    if result['issues']:
        for i, issue in enumerate(result['issues'][:3], 1):
            print(f"  {i}. [{issue['severity']}] {issue['message'][:50]}...")
    else:
        print("  鏃犻棶棰?鉁?)

# 姹囨€?
avg_score = sum(r['overall_score'] for r in results) / len(results)
print(f"\n{'=' * 60}")
print(f"骞冲潎鎬诲垎: {avg_score:.3f}")
print(f"{'=' * 60}")

if avg_score >= 0.7:
    print("鉁?鍏ㄩ儴閫氳繃浠茶锛屽彲鍏ュ簱")
else:
    print("鈿狅笍 閮ㄥ垎鏈揪鏍囷紝闇€杩涗竴姝ヤ慨鏀?)
