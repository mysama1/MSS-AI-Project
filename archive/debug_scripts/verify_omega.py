# -*- coding: utf-8 -*-
"""
楠岃瘉惟绾х粓瀹″搷搴斿悎瑙勫寲鐗堟湰
"""
import sys
sys.path.insert(0, 'E:\\AI_Workspace\\MSS-AI\\project')

from mss_analyzer import analyze_text
import json

# 璇诲彇鍚堣鍖栧唴瀹?with open('omega_content_compliant.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

content = data['omega_compliant']

print("=" * 60)
print("惟绾х粓瀹″搷搴斿悎瑙勫寲鐗堟湰浠茶楠岃瘉")
print("=" * 60)

result = analyze_text(content, claimed_layer="L3")

print(f"\n鎬诲垎: {result['overall_score']}")
print(f"妫€娴嬪埌灞傜骇: {result['layer']['detected']}")
print(f"闂鏁? {len(result['issues'])}")

if result['issues']:
    print("\n闂鍒楄〃锛?)
    for i, issue in enumerate(result['issues'], 1):
        print(f"  {i}. [{issue['severity']}] {issue['message']}")
else:
    print("\n鉁?鏃犻棶棰橈紝閫氳繃浠茶")

# 妫€鏌ュ叧閿慨姝ｇ偣
checks = [
    ("娓呴櫎'缁堟瀬'", "缁堟瀬" not in content),
    ("娓呴櫎'褰诲簳'", "褰诲簳" not in content),
    ("娓呴櫎'姘镐箙閿佸畾'", "姘镐箙閿佸畾" not in content),
    ("娓呴櫎'蹇呯劧'", "蹇呯劧" not in content),
    ("娣诲姞'鍋囪鎬?", "鍋囪鎬? in content),
    ("娣诲姞'闈炲畾璁?", "闈炲畾璁? in content),
    ("娣诲姞鍏嶈矗澹版槑", "涓嶆瀯鎴愮鐞嗗缓璁? in content),
    ("淇濈暀璋﹂€婃潯娆?, "Humility Clause" in content),
]

print(f"\n{'=' * 60}")
print("鍏抽敭淇鐐规鏌ワ細")
for check_name, check_result in checks:
    status = "鉁? if check_result else "鉂?
    print(f"  {status} {check_name}")

print(f"\n{'=' * 60}")
if result['overall_score'] >= 0.7:
    print("鉁?閫氳繃浠茶锛屽彲鍏ュ簱")
else:
    print(f"鈿狅笍 鏈揪鏍囷紙{result['overall_score']:.3f} < 0.7锛夛紝闇€杩涗竴姝ヤ慨鏀?)
