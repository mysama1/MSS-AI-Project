#!/usr/bin/env python3
"""Grade Standards Query — filter KB by confidence tier"""
import json, os, sys

KB_DIR = r"E:\AI_Workspace\MSS-AI\project\knowledge_base"

def query(threshold=0.8, layer=None):
    results = []
    for fn in sorted(os.listdir(KB_DIR)):
        if not fn.endswith(".jsonl") or fn.startswith("_"): continue
        try:
            with open(os.path.join(KB_DIR, fn), "r", encoding="utf-8") as f:
                entry = json.loads(f.read())
        except: continue
        
        conf = entry.get("confidence", 0)
        if layer and entry.get("layer", "") != layer:
            continue
        if conf >= threshold:
            results.append(entry)
    
    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return results

GRADE_INFO = {
    "A": (0.8, "高置信度 — 直接入库, 锚定公理明确, 无污染"),
    "B": (0.5, "中信度 — 已入库, 需定期审查, 可能有缺失"),
    "C": (0.0, "低置信度 — 框架占位, 待补全或废弃"),
}

if __name__ == "__main__":
    grade = "A"
    layer = None
    for arg in sys.argv[1:]:
        if arg.startswith("--grade="):
            grade = arg.split("=")[1].upper()
        elif arg.startswith("--threshold="):
            threshold = float(arg.split("=")[1])
        elif arg.startswith("--layer="):
            layer = arg.split("=")[1]
    
    if grade in GRADE_INFO:
        threshold = GRADE_INFO[grade][0]
        desc = GRADE_INFO[grade][1]
    else:
        threshold = 0.8
        desc = "自定义阈值"
    
    results = query(threshold, layer)
    
    print(f"Grade {grade}: {desc}")
    print(f"阈值: >= {threshold}" + (f", 层: {layer}" if layer else ""))
    print(f"匹配: {len(results)} 条目\n")
    print(f"{'H编号':<8} {'层':<4} {'置信度':<8} {'标题'}")
    print("-" * 70)
    
    for e in results:
        h_id = e.get("h_id", "?")
        conf = e.get("confidence", 0)
        layer_e = e.get("layer", "?")
        title = e.get("title", "?")[:40]
        print(f"  {h_id:<6} {layer_e:<4} {conf:.2f}     {title}")