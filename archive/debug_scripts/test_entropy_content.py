import sys
sys.stdout.reconfigure(encoding='utf-8')

from mss_analyzer import MSSAnalyzer, analyze_text
import json

# 读取熵增雷达内容
with open('entropy_radar_content.md', 'r', encoding='utf-8') as f:
    text = f.read()

analyzer = MSSAnalyzer()
report = analyzer.analyze(text, claimed_layer="L3")

print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
