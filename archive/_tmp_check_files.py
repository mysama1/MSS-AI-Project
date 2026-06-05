import os, json

fp = r'C:\MSS-AI-Project\task_bar_current.json'
with open(fp, 'r', encoding='utf-8') as f:
    tb = json.load(f)

for t in tb['active_tasks']:
    tid = t['id']
    if tid in ['D5-029','D5-031','D5-023','D5-026','D5-025']:
        note = t.get('note','')[:120]
        print(f"{tid} {t['name']}: {t['progress']} — {note}")

print()
for f in ['benchmark_harness.py','whitepaper_v1.1.md','mss_z3_kernel.py',
          'mss_llm_perception_shell.py','web_api.py','API_GUIDE.md',
          'mss_agent_sdk']:
    fp2 = os.path.join(r'C:\MSS-AI-Project', f)
    if os.path.exists(fp2):
        if os.path.isdir(fp2):
            print(f"{f}/ (dir)")
        else:
            kb = os.path.getsize(fp2)/1024
            print(f"{f}: {kb:.0f}KB")
    else:
        print(f"{f}: NOT FOUND")