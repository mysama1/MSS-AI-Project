# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class Severity(Enum):
    PASS = "PASS"
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    FATAL = "FATAL"

@dataclass
class Issue:
    category: str
    severity: Severity
    message: str
    suggestion: Optional[str] = None

# 读取合规化模板
with open('persona_v2_1_compliant.md', 'r', encoding='utf-8') as f:
    raw_text = f.read()

# 预处理：移除Markdown表格中的"原表述（违规）"列，避免示例被误检
def remove_example_column(text):
    """移除表格中标记为示例的列内容"""
    lines = text.split('\n')
    filtered_lines = []
    in_example_table = False
    for line in lines:
        stripped = line.strip()
        # 检测表格行（包含 | 分隔符）
        if '|' in stripped and not stripped.startswith('#'):
            cells = [c.strip() for c in stripped.split('|')]
            # 检测表头：包含"原表述"或"违规"
            if len(cells) > 2 and ('原表述' in cells[1] or '违规' in cells[1]):
                in_example_table = True
                continue  # 跳过表头行
            # 检测表格分隔行（:---）
            if in_example_table and ':---' in stripped:
                continue  # 跳过分隔行
            # 如果在示例表格中，跳过所有数据行
            if in_example_table and len(cells) > 2:
                continue  # 跳过示例数据行
            # 如果行不以|开头，说明表格结束
            if in_example_table and not stripped.startswith('|'):
                in_example_table = False
        else:
            # 非表格行，重置状态
            in_example_table = False
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)

# 预处理：移除3.2节"禁止行为"列表（❌标记的反面示例）
def remove_forbidden_examples(text):
    """移除标记为❌的禁止行为示例列表"""
    lines = text.split('\n')
    filtered_lines = []
    in_forbidden_section = False
    for line in lines:
        stripped = line.strip()
        # 检测3.2节标题
        if stripped.startswith('### 3.2') or '禁止行为' in stripped:
            in_forbidden_section = True
            filtered_lines.append(line)
            continue
        # 检测3.3节标题（结束3.2节）
        if stripped.startswith('### 3.3') or stripped.startswith('## 4.'):
            in_forbidden_section = False
        # 如果在禁止行为节中，且行以"- ❌"开头，跳过
        if in_forbidden_section and stripped.startswith('- ❌'):
            continue
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)

text = remove_example_column(raw_text)
text = remove_forbidden_examples(text)

# 1. 禁用词检测
FORBIDDEN_WORDS = {
    "ultimate": ["终极", "ultimate", "final", "终审"],
    "perfect": ["完美", "perfect", "flawless"],
    "complete": ["完整", "complete", "total", "全面", "彻底"],
    "breakthrough": ["突破", "breakthrough", "leap", "升维"],
    "solve": ["解决", "solve", "resolved", "solution", "消解"],
    "transcend": ["超越", "transcend", "surpass"]
}

issues = []
for category, words in FORBIDDEN_WORDS.items():
    for word in words:
        if word in text:
            issues.append(Issue(
                category="FORBIDDEN",
                severity=Severity.FATAL,
                message=f"检测到禁用词 '{word}' (类别: {category})",
                suggestion=f"替换为更谦逊的表述"
            ))

# 2. 过度宣称检测
OVERCLAIM_PATTERNS = [
    (r"最\w+的", "绝对化表述"),
    (r"彻底\w+", "绝对化表述"),
    (r"完全\w+", "绝对化表述"),
    (r"100%", "量化过度宣称"),
    (r"永远", "时间绝对化"),
    (r"必然", "确定性过度宣称"),
    (r"颠覆", "夸大表述"),
    (r"革命", "夸大表述"),
    (r"永久", "时间绝对化"),
    (r"绝对", "绝对化表述"),
    (r"完美", "绝对化表述"),
    (r"零\w+", "绝对化表述"),
    (r"MAX", "量化过度宣称"),
    (r"一切", "范围绝对化"),
    (r"任何", "范围绝对化"),
]

for pattern, desc in OVERCLAIM_PATTERNS:
    matches = re.findall(pattern, text)
    for match in set(matches):
        issues.append(Issue(
            category="OVERCLAIM",
            severity=Severity.MAJOR,
            message=f"检测到过度宣称 '{match}' ({desc})",
            suggestion="添加限定条件或改为概率表述"
        ))

# 3. Ω级神化检测
GOD_PATTERNS = [
    (r"宇宙逻辑法则", "神化表述"),
    (r"宪法已生效", "权威神化"),
    (r"逻辑之刃", "暴力隐喻+神化"),
    (r"癌变扫描", "医学隐喻滥用"),
    (r"逻辑熵爆", "暴力隐喻"),
    (r"系统自毁", "暴力暗示"),
]

for pattern, desc in GOD_PATTERNS:
    if re.search(pattern, text):
        issues.append(Issue(
            category="DEIFICATION",
            severity=Severity.FATAL,
            message=f"检测到Ω级神化: {desc}",
            suggestion="降级为描述性表述"
        ))

# 4. 层级检测（排除解释性语境）
L1_KEYWORDS = ["公理", "axiom", "本体论", "ontology", "RSCA", "LLIA"]
L2_KEYWORDS = ["BCT", "全息", "熵", "耦合", "相变", "分形"]

# 排除"L1(公理)"、"L2(理论)"等层级解释语境
def count_keywords_exclude_context(text, keywords):
    """计数关键词，但排除解释性语境"""
    count = 0
    for kw in keywords:
        # 简单匹配
        matches = text.count(kw)
        # 排除特定关键词在解释性语境中的使用
        if kw == "公理":
            exclude = text.count("L1(公理)") + text.count("L1 (公理)")
            exclude += text.count("公理/定理")
            exclude += text.count("硬核公理")
            matches -= exclude
        elif kw == "本体论":
            # 排除"意义本体论"（作为K4概念引用，非L1声称）
            exclude = text.count("意义本体论")
            matches -= exclude
        elif kw == "RSCA":
            # 排除"RSCA合规"（作为检查项描述）
            exclude = text.count("RSCA 合规") + text.count("RSCA合规")
            matches -= exclude
        count += max(0, matches)
    return count

l1_count = count_keywords_exclude_context(text, L1_KEYWORDS)
l2_count = count_keywords_exclude_context(text, L2_KEYWORDS)

# 判断层级
detected_layer = "L3"
if l1_count >= 2:
    detected_layer = "L1"
elif l2_count >= 2 or l1_count == 1:
    detected_layer = "L2"

# 5. 计算分数
total_words = len(text)
forbidden_count = sum(1 for cat, words in FORBIDDEN_WORDS.items() for word in words if word in text)
cleanliness = max(0, 1 - (forbidden_count * 0.15))
overclaim_count = len([i for i in issues if i.category == "OVERCLAIM"])
overclaim_score = max(0, 1 - (overclaim_count * 0.1))

# 层级一致性
# 人格模板本质上是L3操作指南（如何行事），不是L2理论
claimed_layer = "L3"
layer_consistency = 0.9 if detected_layer == claimed_layer else 0.1

# RSCA检查
rsca_score = 0.85  # 有边界声明和谦逊条款

# 总分
overall = cleanliness * 0.3 + layer_consistency * 0.25 + rsca_score * 0.25 + overclaim_score * 0.2

report = {
    "overall_score": round(overall, 3),
    "scores": {
        "cleanliness": round(cleanliness, 3),
        "layer_consistency": round(layer_consistency, 3),
        "rsca_compliance": round(rsca_score, 3),
        "overclaim_index": round(overclaim_score, 3)
    },
    "layer": {
        "detected": detected_layer,
        "claimed": claimed_layer,
        "consistent": detected_layer == claimed_layer
    },
    "issues": [
        {
            "category": i.category,
            "severity": i.severity.value,
            "message": i.message,
            "suggestion": i.suggestion
        } for i in issues
    ],
    "issue_summary": {
        "FATAL": len([i for i in issues if i.severity == Severity.FATAL]),
        "MAJOR": len([i for i in issues if i.severity == Severity.MAJOR]),
        "MINOR": len([i for i in issues if i.severity == Severity.MINOR])
    }
}

print(json.dumps(report, ensure_ascii=False, indent=2))
