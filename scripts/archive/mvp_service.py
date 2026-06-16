#!/usr/bin/env python3
"""
NSSM service wrapper for MVP Phase 0 glass simulation.
Runs independently of OpenClaw Job Object, writes results to disk.
"""
import time, os, sys
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")
from mvp_glass_simulation import run_mvp_simulation

print(f"[{time.strftime('%H:%M:%S')}] Starting MVP Phase 0 simulation (NSSM service)...")
sys.stdout.flush()

t0 = time.time()
results = run_mvp_simulation()
elapsed = time.time() - t0

out_dir = r"E:\AI_Workspace\data\mvp_phase0"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "mvp_simulation_results.json")

import json
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"[{time.strftime('%H:%M:%S')}] DONE ({elapsed:.1f}s)")
print(f"Results: {out_path}")
print("EXIT_SUCCESS")
