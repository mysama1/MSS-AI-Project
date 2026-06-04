#!/usr/bin/env python3
"""Research Domain Heatmap — ASCII + status annotation"""
import json, os

KB_DIR = r"E:\AI_Workspace\MSS-AI\project\knowledge_base"
INDEX = os.path.join(KB_DIR, "_master_index.md")

CATS = {
    "MSS-1": ("核心公理", "Core Axioms"),
    "MSS-2": ("数学形式化", "Math Formalization"),
    "MSS-3": ("物理宇宙学", "Physics & Cosmo"),
    "MSS-4": ("智能与工程", "AI & Engineering"),
    "MSS-5": ("文明与社会", "Civilization"),
    "MSS-6": ("元理论方法", "Meta-Theory"),
    "MSS-7": ("理论债务", "Theoretical Debt"),
    "MSS-8": ("实验与验证", "Experiment"),
    "MSS-9": ("跨范式传播", "Communication"),
}

# Status by category
def assess_status(entries, cat):
    if not entries: return ("❌", "EMPTY")
    a = [e for e in entries if e.get("confidence", 0) >= 0.8]
    b = [e for e in entries if 0.5 <= e.get("confidence", 0) < 0.8]
    c = [e for e in entries if e.get("confidence", 0) < 0.5]
    total = len(entries)
    
    if total >= 5 and len(a)/total >= 0.3 and len(c) == 0:
        return ("✅", "MATURE")
    elif total >= 3 and len(a) + len(b) >= total * 0.5:
        return ("🔄", "BUILDING")
    elif total < 3:
        return ("⚠️", "SPARSE")
    else:
        return ("⚠️", "GAPS")

def load_master_index():
    """Parse _master_index.md for categorized entries"""
    import re
    cat_map = {}
    if not os.path.exists(INDEX):
        return cat_map
    with open(INDEX, "r", encoding="utf-8") as f:
        content = f.read()
    current_cat = None
    for line in content.split("\n"):
        # Detect category headers
        m_cat = re.match(r'## (MSS-\d):', line)
        if m_cat:
            current_cat = m_cat.group(1)
            cat_map[current_cat] = []
            continue
        # Parse entry lines: | MSS-1-001 | HXXX | title | confidence |
        m_entry = re.match(r'\|\s*(MSS-\d+-\d+)\s*\|\s*(H\d+)\s*\|\s*(.+?)\s*\|\s*([\d.]+)', line)
        if m_entry and current_cat:
            new_id = m_entry.group(1)
            h_id = m_entry.group(2)
            title = m_entry.group(3).strip()
            conf = float(m_entry.group(4))
            cat_map[current_cat].append({"new_id": new_id, "h_id": h_id, "title": title, "confidence": conf})
    return cat_map

if __name__ == "__main__":
    # Use master index for classification
    cat_entries = load_master_index()
    
    # Generate heatmap
    max_entries = max(len(e) for e in cat_entries.values()) or 1
    print("MSS Research Domain Heatmap\n")
    print(f"{'Category':<12} {'Name':<18} {'Entries':>7} {'Status':<9} Heatmap")
    print("-" * 80)
    
    for cat in sorted(CATS):
        name_cn, name_en = CATS[cat]
        entries = cat_entries.get(cat, [])
        icon, status = assess_status(entries, cat)
        count = len(entries)
        bar_len = max(1, int(count / max_entries * 30)) if max_entries > 0 else 1
        bar = "█" * bar_len
        
        a_count = len([e for e in entries if e.get("confidence", 0) >= 0.8])
        print(f"  {cat:<8} {name_cn:<16} {count:>5}  {icon}{status:<7} {bar} A:{a_count}")
    
    print("\nLegend: ✅MATURE = 30% Grade A, no gaps | 🔄BUILDING = active growth | ⚠️SPARSE/GAPS = needs attention")