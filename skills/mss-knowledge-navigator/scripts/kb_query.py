#!/usr/bin/env python3
"""KB Query Script — intent-level, idempotent"""
import sys, os, json, re

KB_DIR = r"E:\AI_Workspace\MSS-AI\project\knowledge_base"
INDEX = os.path.join(KB_DIR, "_master_index.md")

def search(keyword, regex=False, category=None):
    results = []
    for fn in sorted(os.listdir(KB_DIR)):
        if not fn.endswith(".jsonl") or fn.startswith("_"): continue
        fp = os.path.join(KB_DIR, fn)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                entry = json.loads(f.read())
        except: continue
        title = entry.get("title", "")
        content = entry.get("content", "")[:500]
        tags = " ".join(entry.get("tags", []))
        text = f"{title} {content} {tags}".lower()
        h_id = entry.get("h_id", "")
        
        if regex:
            if re.search(keyword, text, re.IGNORECASE):
                results.append(entry)
        else:
            if keyword.lower() in text:
                results.append(entry)
        
        if category:
            # Check from filename or category tag
            if category not in (entry.get("tags", []) or []):
                if category not in fn:
                    continue
    
    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: kb_query.py <keyword> [--regex] [--category MSS-X]")
        sys.exit(1)
    
    keyword = sys.argv[1]
    use_regex = "--regex" in sys.argv
    category = None
    for arg in sys.argv:
        if arg.startswith("--category"):
            category = arg.split("=")[-1] if "=" in arg else None
    
    results = search(keyword, regex=use_regex, category=category)
    
    if not results:
        print("未找到匹配项。建议搜索相关关键词，或检查拼写。")
        print("当前可用类别：MSS-1 (核心公理) ~ MSS-9 (跨范式传播)")
        sys.exit(0)
    
    print(f"找到 {len(results)} 条匹配项：\n")
    for e in results[:20]:
        h_id = e.get("h_id", "?")
        title = e.get("title", "?")[:50]
        layer = e.get("layer", "L?")
        conf = e.get("confidence", 0)
        tags = ", ".join(e.get("tags", [])[:5])
        print(f"  {h_id} [{layer}, {conf:.2f}] {title}")
        if tags: print(f"    tags: {tags}")
    
    if len(results) > 20:
        print(f"\n  ... 还有 {len(results)-20} 条 (前20条已显示)")