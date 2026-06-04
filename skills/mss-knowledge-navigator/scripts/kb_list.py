#!/usr/bin/env python3
"""KB Category Lister — intent-level, idempotent"""
import sys, os, json

KB_DIR = r"E:\AI_Workspace\MSS-AI\project\knowledge_base"

CATS = {
    "MSS-1": "核心公理与基础",
    "MSS-2": "数学形式化",
    "MSS-3": "物理与宇宙学",
    "MSS-4": "智能与工程",
    "MSS-5": "文明与社会",
    "MSS-6": "元理论与方法",
    "MSS-7": "理论债务",
    "MSS-8": "实验与验证",
    "MSS-9": "跨范式与传播",
}

CAT_KEYWORDS = {
    "MSS-1": ["公理", "axiom", "A1", "A2", "A3", "L1硬核", "本体论", "H141"],
    "MSS-2": ["数学", "math", "定理", "拓扑", "黎曼", "素数", "形式化"],
    "MSS-3": ["物理", "quantum", "宇宙", "熵", "热力学", "相对论"],
    "MSS-4": ["AI", "MSS-AI", "LLM", "工程", "部署", "架构", "训练"],
    "MSS-5": ["文明", "K3", "K4", "社会", "政治", "组织", "叙事"],
    "MSS-6": ["知识库", "KB", "归档", "审计", "元理论", "方法"],
    "MSS-7": ["TD-", "债务", "debt", "风险", "边界"],
    "MSS-8": ["实验", "验证", "模拟", "测试", "沙盒"],
    "MSS-9": ["跨范式", "定名", "发表", "传播", "翻译"],
}

if __name__ == "__main__":
    cat_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    if cat_arg and cat_arg in CATS:
        cats_to_show = {cat_arg: CATS[cat_arg]}
    else:
        cats_to_show = CATS
    
    for cat, cat_name in cats_to_show.items():
        keywords = CAT_KEYWORDS.get(cat, [])
        entries = []
        for fn in sorted(os.listdir(KB_DIR)):
            if not fn.endswith(".jsonl") or fn.startswith("_"): continue
            fp = os.path.join(KB_DIR, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    entry = json.loads(f.read())
            except: continue
            text = f"{entry.get('title','')} {entry.get('summary','')} {' '.join(entry.get('tags',[]))}".lower()
            if any(kw.lower() in text for kw in keywords):
                entries.append(entry)
        
        entries.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        print(f"\n{'='*60}")
        print(f"{cat}: {cat_name} ({len(entries)} entries)")
        print(f"{'='*60}")
        
        grade_a = [e for e in entries if e.get("confidence", 0) >= 0.8]
        grade_b = [e for e in entries if 0.5 <= e.get("confidence", 0) < 0.8]
        grade_c = [e for e in entries if e.get("confidence", 0) < 0.5]
        
        print(f"  Grade A: {len(grade_a)} | Grade B: {len(grade_b)} | Grade C: {len(grade_c)}")
        
        for e in entries[:15]:
            h_id = e.get("h_id", "?")
            title = e.get("title", "?")[:45]
            conf = e.get("confidence", 0)
            layer = e.get("layer", "?")
            grade = "A" if conf >= 0.8 else ("B" if conf >= 0.5 else "C")
            print(f"  [{grade}] {h_id} [{layer}, {conf:.2f}] {title}")
        
        if len(entries) > 15:
            print(f"  ... 还有 {len(entries)-15} 条")