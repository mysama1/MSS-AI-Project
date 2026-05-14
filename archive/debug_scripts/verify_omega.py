# -*- coding: utf-8 -*-
"""
验证Ω级终审响应合规化版本
"""
import sys
sys.path.insert(0, 'C:\\MSS-AI-Project')

from mss_analyzer import analyze_text
import json

# 读取合规化内容
with open('omega_content_compliant.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

content = data['omega_compliant']

print("=" * 60)
print("Ω级终审响应合规化版本仲裁验证")
print("=" * 60)

result = analyze_text(content, claimed_layer="L3")

print(f"\n总分: {result['overall_score']}")
print(f"检测到层级: {result['layer']['detected']}")
print(f"问题数: {len(result['issues'])}")

if result['issues']:
    print("\n问题列表：")
    for i, issue in enumerate(result['issues'], 1):
        print(f"  {i}. [{issue['severity']}] {issue['message']}")
else:
    print("\n✅ 无问题，通过仲裁")

# 检查关键修正点
checks = [
    ("清除'终极'", "终极" not in content),
    ("清除'彻底'", "彻底" not in content),
    ("清除'永久锁定'", "永久锁定" not in content),
    ("清除'必然'", "必然" not in content),
    ("添加'假设性'", "假设性" in content),
    ("添加'非定论'", "非定论" in content),
    ("添加免责声明", "不构成管理建议" in content),
    ("保留谦逊条款", "Humility Clause" in content),
]

print(f"\n{'=' * 60}")
print("关键修正点检查：")
for check_name, check_result in checks:
    status = "✅" if check_result else "❌"
    print(f"  {status} {check_name}")

print(f"\n{'=' * 60}")
if result['overall_score'] >= 0.7:
    print("✅ 通过仲裁，可入库")
else:
    print(f"⚠️ 未达标（{result['overall_score']:.3f} < 0.7），需进一步修改")
