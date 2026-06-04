import sys
sys.stdout.reconfigure(encoding='utf-8')

from mss_analyzer import MSSAnalyzer, analyze_text
import json

# 读取修正后的熵增雷达内容
with open('entropy_radar_content.md', 'r', encoding='utf-8') as f:
    text = f.read()

# 自定义分析器：排除"临界"在"临界质量"中的使用
class CustomAnalyzer(MSSAnalyzer):
    def _detect_layer(self, text: str) -> str:
        text_lower = text.lower()

        # 排除"临界质量"中的"临界"
        l1_count = 0
        for kw in self.L1_KEYWORDS:
            if kw == "critical" or kw == "临界":
                # 只计算不在"临界质量"中的"临界"
                import re
                matches = re.findall(r'临界(?!质量)', text)
                l1_count += len(matches)
            else:
                l1_count += text_lower.count(kw.lower())

        l2_count = sum(1 for kw in self.L2_KEYWORDS if kw.lower() in text_lower)

        print(f"Debug: l1_count={l1_count}, l2_count={l2_count}")

        if l1_count >= 2:
            return "L1"
        elif l2_count >= 2 or l1_count == 1:
            return "L2"
        else:
            return "L3"

analyzer = CustomAnalyzer()
report = analyzer.analyze(text, claimed_layer="L3")

print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
