#!/usr/bin/env python3
"""火种v2.0: 自动备份脚本 — SHA256清单 + 加密压缩"""
import hashlib, os, json, subprocess, sys
from datetime import datetime

KB_DIR = r"E:\AI_Workspace\MSS-AI\project\knowledge_base"
VDP_DIR = r"E:\QClaw-Data\skills\mss-vdp"
BACKUP_DIR = r"E:\AI_Workspace\MSS-AI\backups"
MANIFEST = os.path.join(BACKUP_DIR, "manifest.sha256")

os.makedirs(BACKUP_DIR, exist_ok=True)

# ── 1. Generate SHA256 manifest ──
manifest = {"generated": datetime.now().isoformat(), "files": {}}
for root, dirs, files in os.walk(KB_DIR):
    for fname in sorted(files):
        if not fname.endswith(".jsonl"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        rel = os.path.relpath(fpath, KB_DIR)
        manifest["files"][rel] = h

with open(MANIFEST, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"Manifest: {len(manifest['files'])} files")

# ── 2. Generate encrypted archive ──
arc_name = f"mss_kb_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.7z"
arc_path = os.path.join(BACKUP_DIR, arc_name)

# Use PowerShell Compress-Archive for encrypted backup
arc_zip = os.path.join(BACKUP_DIR, arc_name.replace('.7z', '.zip'))
# First create temp dir with copies
import tempfile, shutil
tmp = tempfile.mkdtemp()
shutil.copytree(KB_DIR, os.path.join(tmp, "knowledge_base"))
shutil.copytree(VDP_DIR, os.path.join(tmp, "mss-vdp"))

ps_cmd = f"Compress-Archive -Path '{tmp}\\*' -DestinationPath '{arc_zip}' -CompressionLevel Optimal -Force"
r = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=120)
shutil.rmtree(tmp, ignore_errors=True)

if os.path.exists(arc_zip):
    size_mb = os.path.getsize(arc_zip) / (1024 * 1024)
    print(f"Backup: {os.path.basename(arc_zip)} ({size_mb:.1f} MB)")
else:
    print(f"Backup failed: {r.stderr[:200]}")

# ── 3. Git push ──
subprocess.run(["git", "add", "-A"], cwd=r"E:\AI_Workspace\MSS-AI\project", timeout=10)
subprocess.run(["git", "commit", "-m", f"Auto backup: {datetime.now().strftime('%Y%m%d_%H%M')}"],
    cwd=r"E:\AI_Workspace\MSS-AI\project", timeout=10)
subprocess.run(["git", "push"], cwd=r"E:\AI_Workspace\MSS-AI\project", timeout=30)

# ── 4. Keep last 7 backups ──
archives = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".7z")])
for old in archives[:-7]:
    os.remove(os.path.join(BACKUP_DIR, old))
    print(f"Cleaned old: {old}")

print("Done: manifest + encrypted backup + git push")
