#!/usr/bin/env python3
"""
MSS知识库整理工具
功能：
1. 加载所有历史JSONL
2. 评估内容质量（意义完整性、自洽性）
3. 分类：L1硬核 / L2保护带 / L3试探法 / L4污染池 / 待完善
4. 生成合并文件（按分类）
5. 创建目录索引
"""

import json
import os
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class ContentTier(Enum):
    L1_CORE = "L1_硬核公理"
    L2_PROTECTIVE = "L2_保护带"
    L3_HEURISTIC = "L3_试探法"
    L4_CONTAMINATED = "L4_污染池"
    NEEDS_IMPROVEMENT = "待完善"

@dataclass
class ContentEntry:
    id: str
    title: str
    content: str
    layer: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    source_file: str = ""

    # 质量评估
    meaning_integrity: float = 0.0  # 意义完整性 0-1
    self_consistency: float = 0.0   # 自洽性 0-1
    assigned_tier: Optional[ContentTier] = None
    issues: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = "UNKNOWN"

def evaluate_content_quality(entry: ContentEntry) -> None:
    """评估内容质量"""
    content = entry.content
    title = entry.title
    issues = []

    # 1. 检查绝对化表述（意义完整性降低）
    absolute_patterns = [
        r'100%\s*免疫', r'绝对\s*安全', r'永远\s*正确', r'终极\s*真理',
        r'完美\s*解决', r'不可\s*超越', r'彻底\s*消除', r'完全\s*杜绝'
    ]
    absolute_count = sum(1 for p in absolute_patterns if re.search(p, content))
    if absolute_count > 0:
        issues.append(f"含{absolute_count}处绝对化表述")

    # 2. 检查缺乏证据支撑
    evidence_markers = ['实验', '数据', '验证', '证明', '观测', '测量']
    has_evidence = any(m in content for m in evidence_markers)
    if not has_evidence and len(content) > 500:
        issues.append("缺乏实证支撑标记")

    # 3. 检查自指矛盾
    if '矛盾' in content and '不矛盾' in content:
        issues.append("可能存在自指矛盾")

    # 4. 检查过度宣称
    claim_patterns = [r'统一\s*所有', r'解释\s*一切', r'解决\s*全部', r'终极\s*理论']
    overclaim_count = sum(1 for p in claim_patterns if re.search(p, content))
    if overclaim_count > 0:
        issues.append(f"含{overclaim_count}处过度宣称")

    # 5. 检查逻辑严密性
    logic_markers = ['如果', '那么', '因为', '所以', '因此', '由此']
    has_logic = any(m in content for m in logic_markers)
    if not has_logic and len(content) > 300:
        issues.append("缺乏逻辑连接词，推导链可能不完整")

    # 6. 检查术语一致性
    if '熵' in content and '热税' not in content and '意义' in content:
        # 使用熵但不用热税，可能术语不一致
        pass  # 不标记，可能是早期内容

    # 计算分数
    penalty = len(issues) * 0.15
    entry.meaning_integrity = max(0.0, 1.0 - penalty - absolute_count * 0.1)
    entry.self_consistency = max(0.0, 1.0 - penalty * 0.8)
    entry.issues = issues

def classify_tier(entry: ContentEntry) -> ContentTier:
    """分类到对应层级"""
    # 基于layer字段
    layer = (entry.layer or "").upper()

    if "L1" in layer or "CORE" in layer or "公理" in layer:
        if entry.meaning_integrity < 0.5 or entry.self_consistency < 0.5:
            return ContentTier.L4_CONTAMINATED
        return ContentTier.L1_CORE

    if "L2" in layer or "PROTECTIVE" in layer or "保护" in layer:
        if entry.meaning_integrity < 0.4:
            return ContentTier.L4_CONTAMINATED
        return ContentTier.L2_PROTECTIVE

    if "L3" in layer or "HEURISTIC" in layer or "试探" in layer:
        if entry.meaning_integrity < 0.3:
            return ContentTier.L4_CONTAMINATED
        return ContentTier.L3_HEURISTIC

    if "L4" in layer or "CONTAMINATED" in layer or "污染" in layer:
        return ContentTier.L4_CONTAMINATED

    # 基于内容质量自动分类
    if entry.meaning_integrity < 0.3 or entry.self_consistency < 0.3:
        return ContentTier.L4_CONTAMINATED

    if entry.meaning_integrity < 0.6 or entry.self_consistency < 0.6:
        return ContentTier.NEEDS_IMPROVEMENT

    # 默认根据ID判断
    eid = entry.id.upper()
    if eid.startswith(("A", "AXIOM")) or "公理" in entry.title:
        return ContentTier.L1_CORE
    if eid.startswith(("H", "THEORY")) and int(re.findall(r'\d+', eid)[0]) < 60 if re.findall(r'\d+', eid) else True:
        return ContentTier.L2_PROTECTIVE

    return ContentTier.L3_HEURISTIC

def load_all_entries() -> List[ContentEntry]:
    """加载所有JSONL文件"""
    kb_dir = r"C:\MSS-AI-Project\knowledge_base"
    entries = []

    files = sorted([f for f in os.listdir(kb_dir) if f.endswith('.jsonl')])

    for fname in files:
        filepath = os.path.join(kb_dir, fname)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = ContentEntry(
                            id=data.get('id', ''),
                            title=data.get('title', 'Untitled'),
                            content=data.get('content', data.get('text', '')),
                            layer=data.get('layer'),
                            category=data.get('category'),
                            tags=data.get('tags', []),
                            source_file=fname
                        )
                        entries.append(entry)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"Error reading {fname}: {e}")

    return entries

def generate_tier_file(tier: ContentTier, entries: List[ContentEntry], output_dir: str) -> str:
    """生成分类文件"""
    tier_entries = [e for e in entries if e.assigned_tier == tier]

    if not tier_entries:
        return ""

    lines = []
    lines.append(f"# {tier.value}")
    lines.append(f"\n*包含 {len(tier_entries)} 条记录*")
    lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    lines.append("=" * 60)
    lines.append("")

    for i, entry in enumerate(tier_entries, 1):
        lines.append(f"\n## [{i}] {entry.id} - {entry.title}\n")

        meta = []
        if entry.layer:
            meta.append(f"原层级: {entry.layer}")
        if entry.category:
            meta.append(f"分类: {entry.category}")
        if entry.tags:
            meta.append(f"标签: {', '.join(entry.tags)}")
        meta.append(f"来源: {entry.source_file}")
        meta.append(f"意义完整性: {entry.meaning_integrity:.2f}")
        meta.append(f"自洽性: {entry.self_consistency:.2f}")

        lines.append(f"*{' | '.join(meta)}*\n")

        if entry.issues:
            lines.append(f"**⚠️ 问题标记**: {', '.join(entry.issues)}\n")

        lines.append(entry.content)
        lines.append("")
        lines.append("-" * 40)
        lines.append("")

    # 写入文件
    safe_name = tier.value.replace("/", "_").replace("\\", "_")
    filepath = os.path.join(output_dir, f"{safe_name}.md")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return filepath

def generate_index(entries: List[ContentEntry], output_dir: str) -> str:
    """生成目录索引"""
    lines = []
    lines.append("# MSS理论体系知识库目录索引")
    lines.append(f"\n*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"*总条目数: {len(entries)}*\n")
    lines.append("---\n")

    # 按层级分组统计
    tier_counts = {}
    for tier in ContentTier:
        tier_entries = [e for e in entries if e.assigned_tier == tier]
        tier_counts[tier] = len(tier_entries)

    lines.append("## 层级分布\n")
    for tier, count in tier_counts.items():
        lines.append(f"- **{tier.value}**: {count} 条")
    lines.append("")

    # 按源文件分组
    lines.append("## 源文件统计\n")
    file_counts = {}
    for e in entries:
        file_counts[e.source_file] = file_counts.get(e.source_file, 0) + 1

    for fname, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {fname}: {count} 条")
    lines.append("")

    # 问题条目清单
    lines.append("## 需要关注的条目\n")
    problematic = [e for e in entries if e.issues]
    lines.append(f"*共 {len(problematic)} 条存在问题*\n")

    for entry in sorted(problematic, key=lambda x: x.meaning_integrity)[:50]:
        lines.append(f"- **{entry.id}** ({entry.assigned_tier.value}): {', '.join(entry.issues)}")

    if len(problematic) > 50:
        lines.append(f"- ... 还有 {len(problematic) - 50} 条")
    lines.append("")

    # 完整目录
    lines.append("## 完整目录\n")
    for tier in [ContentTier.L1_CORE, ContentTier.L2_PROTECTIVE, ContentTier.L3_HEURISTIC,
                 ContentTier.NEEDS_IMPROVEMENT, ContentTier.L4_CONTAMINATED]:
        tier_entries = [e for e in entries if e.assigned_tier == tier]
        if not tier_entries:
            continue

        lines.append(f"\n### {tier.value} ({len(tier_entries)} 条)\n")
        for entry in sorted(tier_entries, key=lambda x: x.id):
            status = "⚠️" if entry.issues else "✅"
            lines.append(f"{status} **{entry.id}** - {entry.title}")

    filepath = os.path.join(output_dir, "目录索引.md")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return filepath

def main():
    print("=" * 60)
    print("MSS知识库整理工具")
    print("=" * 60)
    print()

    # 1. 加载所有条目
    print("📂 加载所有历史条目...")
    entries = load_all_entries()
    print(f"✅ 加载了 {len(entries)} 条记录")
    print()

    # 2. 评估质量
    print("🔍 评估内容质量...")
    for entry in entries:
        evaluate_content_quality(entry)
    print("✅ 评估完成")
    print()

    # 3. 分类
    print("📊 分类到对应层级...")
    for entry in entries:
        entry.assigned_tier = classify_tier(entry)

    tier_counts = {}
    for tier in ContentTier:
        tier_counts[tier] = sum(1 for e in entries if e.assigned_tier == tier)

    print("分类结果:")
    for tier, count in tier_counts.items():
        print(f"  {tier.value}: {count} 条")
    print()

    # 4. 生成输出文件
    output_dir = r"C:\MSS-AI-Project\knowledge_base_organized"
    os.makedirs(output_dir, exist_ok=True)

    print("📝 生成分类文件...")
    for tier in ContentTier:
        filepath = generate_tier_file(tier, entries, output_dir)
        if filepath:
            print(f"  ✅ {os.path.basename(filepath)}")

    # 5. 生成目录索引
    print("📑 生成目录索引...")
    index_path = generate_index(entries, output_dir)
    print(f"  ✅ {os.path.basename(index_path)}")

    print()
    print("=" * 60)
    print("整理完成")
    print(f"输出目录: {output_dir}")
    print("=" * 60)

    # 返回统计信息
    return {
        "total": len(entries),
        "tiers": {t.value: c for t, c in tier_counts.items()},
        "problematic": len([e for e in entries if e.issues]),
        "output_dir": output_dir
    }

if __name__ == "__main__":
    result = main()
