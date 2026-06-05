#!/usr/bin/env python3
"""Theoretical Debt Tracker — scans memory files for TD-XXX patterns"""
import os, re, glob

MEMORY_DIR = r"C:\Users\Administrator\.openclaw\workspace\memory"

def scan():
    debts = []
    pattern = re.compile(r'(TD-[\w-]+)\b')
    status_pattern = re.compile(r'(已清偿|RESOLVED|repaid|已升级|工程验证清偿|进行中|待启动|P0|P1|P2|P3|高|中|低|RESOLVED|resolved|✅)')
    
    for fp in sorted(glob.glob(os.path.join(MEMORY_DIR, "*.md")), reverse=True):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()
        except: continue
        
        for m in pattern.finditer(text):
            td_id = m.group(1)
            # Get context around the match
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 200)
            ctx = text[start:end].replace("\n", " ")
            
            # Check status
            statuses = status_pattern.findall(ctx)
            status = statuses[0] if statuses else "待确认"
            
            # Extract brief description
            desc = ""
            for line in text[m.start():m.start()+500].split("\n"):
                if td_id in line:
                    desc = line.strip()[:80]
                    break
            
            debts.append({
                "id": td_id,
                "status": status,
                "desc": desc,
                "file": os.path.basename(fp),
            })
    
    # Deduplicate
    seen = set()
    unique = []
    for d in debts:
        if d["id"] not in seen:
            seen.add(d["id"])
            unique.append(d)
    
    # Sort by priority
    prio_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "高": 4, "中": 5, "低": 6}
    unique.sort(key=lambda d: prio_order.get(d["status"], 99))
    
    if not unique:
        print("✅ 未发现未清偿的理论债务")
        return
    
    print(f"{'债务编号':<20} {'优先级':<10} {'状态':<10} {'来源文件'}")
    print("-" * 80)
    
    cleared = 0
    active = 0
    for d in unique:
        icon = "✅" if "清偿" in d["status"] else "🔴"
        print(f"  {icon} {d['id']:<18} {d['status']:<10} {d['file']}")
        if "清偿" in d["status"]:
            cleared += 1
        else:
            active += 1
    
    print(f"\n已清偿: {cleared} | 进行中/待处理: {active} | 总计: {len(unique)}")

if __name__ == "__main__":
    scan()