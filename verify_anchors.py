#!/usr/bin/env python3
"""火种v2.1: 分布式锚定验证脚本
验证本地KB完整性，对比SHA256清单
"""
import hashlib, json, os, sys
from datetime import datetime

KB_DIR = r"E:\AI_Workspace\MSS-AI\project\knowledge_base"
MANIFEST = r"E:\AI_Workspace\MSS-AI\backups\manifest.sha256"

# ── 1. Load manifest ──
if not os.path.exists(MANIFEST):
    print("ERROR: No manifest found. Run fire_seed_backup.py first.")
    sys.exit(1)

with open(MANIFEST, "r", encoding="utf-8") as f:
    manifest = json.load(f)

expected = manifest["files"]
print(f"Manifest loaded: {len(expected)} files ({manifest['generated'][:19]})")

# ── 2. Scan local KB ──
current = {}
for root, dirs, files in os.walk(KB_DIR):
    for fname in sorted(files):
        if not fname.endswith(".jsonl"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        rel = os.path.relpath(fpath, KB_DIR)
        current[rel] = h

# ── 3. Compare ──
ok = 0
new_files = 0
modified = 0
missing = 0

for fname, hash_val in expected.items():
    if fname not in current:
        missing += 1
        print(f"  MISSING: {fname}")
    elif current[fname] != hash_val:
        modified += 1
        print(f"  MODIFIED: {fname}")
    else:
        ok += 1

for fname in current:
    if fname not in expected:
        new_files += 1

# ── 4. Report ──
total = len(expected)
integrity = ok / total * 100 if total > 0 else 0

print(f"\n{'='*50}")
print(f"FIRE SEED VERIFICATION — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*50}")
print(f"  OK:       {ok}/{total} ({integrity:.1f}%)")
print(f"  New:      {new_files} (since manifest)")
print(f"  Modified: {modified}")
print(f"  Missing:  {missing}")
print(f"{'='*50}")

if modified == 0 and missing == 0:
    print("✅ INTEGRITY VERIFIED — KB matches manifest")
    print(f"   New unverified entries: {new_files} (safe, just newer than last backup)")
    sys.exit(0)
elif integrity >= 99.0:
    print(f"⚠️  MINOR DRIFT — {modified+missing} files changed, {integrity:.1f}% intact")
    sys.exit(1)
else:
    print(f"❌ TAMPER ALERT — {modified+missing} files changed, only {integrity:.1f}% intact")
    print("   Run fire_seed_backup.py to update manifest if these are legitimate changes")
    sys.exit(2)
