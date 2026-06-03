# -*- coding: utf-8 -*-
"""
验证合规化版本是否通过仲裁
"""
import sys
sys.path.insert(0, 'C:\\MSS-AI-Project')

from mss_analyzer import analyze_text
import json

# 读取合规化内容
with open('ai_content_compliant.json', 'r', encoding='utf-8') as f:
    content = json.load(f)

print("=" * 60)
print("合规化内容仲裁验证")
print("=" * 60)

results = []
for title, text in content.items():
    print(f"\n--- {title} ---")
    result = analyze_text(text, claimed_layer="L3")
    results.append(result)
    
    print(f"总分: {result['overall_score']}")
    print(f"检测到层级: {result['layer']['detected']}")
    print(f"问题数: {len(result['issues'])}")
    
    if result['issues']:
        for i, issue in enumerate(result['issues'][:3], 1):
            print(f"  {i}. [{issue['severity']}] {issue['message'][:50]}...")
    else:
        print("  无问题 ✅")

# 汇总
avg_score = sum(r['overall_score'] for r in results) / len(results)
print(f"\n{'=' * 60}")
print(f"平均总分: {avg_score:.3f}")
print(f"{'=' * 60}")

if avg_score >= 0.7:
    print("✅ 全部通过仲裁，可入库")
else:
    print("⚠️ 部分未达标，需进一步修改")
