#!/usr/bin/env python3
"""NSSM wrapper: MVP Phase 1 Lambda-EIT simulation"""
import time, os, sys, io
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from mvp_lambda_simulation import run_lambda_simulation
import json

print(f"[{time.strftime('%H:%M:%S')}] Starting MVP Phase 1 Lambda-EIT simulation..."); sys.stdout.flush()
t0 = time.time()
results = run_lambda_simulation()
elapsed = time.time() - t0

out_dir = r"E:\AI_Workspace\data\mvp_phase1"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "mvp_lambda_eit_results.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"[{time.strftime('%H:%M:%S')}] DONE ({elapsed:.1f}s) - {out_path}")
print("EXIT_SUCCESS")
