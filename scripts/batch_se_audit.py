# Batch multi-project MSS audit
# Usage: python batch_audit.py
import sys, os, json, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path

targets = [
    ("requests", r"C:\Users\Administrator\AppData\Local\Programs\Python\Python311\Lib\site-packages\requests"),
    ("click",    r"C:\Users\Administrator\AppData\Local\Programs\Python\Python311\Lib\site-packages\click"),
    ("fastapi",  r"C:\Users\Administrator\AppData\Local\Programs\Python\Python311\Lib\site-packages\fastapi"),
]

auditor = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mssclaw", "se_audit.py")
outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(outdir, exist_ok=True)

results = {}
for name, path in targets:
    if not os.path.isdir(path):
        print(f"  ❌ {name}: path not found ({path})")
        continue
    json_out = os.path.join(outdir, f"se_audit_{name}.json")
    t0 = time.time()
    rc = subprocess.run([sys.executable, auditor, path, "--json", json_out],
                       capture_output=True, text=True, timeout=60)
    elapsed = time.time() - t0
    if rc.returncode != 0 and not os.path.exists(json_out):
        print(f"  ❌ {name}: audit failed ({elapsed:.1f}s)")
        print(f"     stderr: {rc.stderr[:200]}")
        continue
    if os.path.exists(json_out):
        with open(json_out, encoding='utf-8') as f:
            data = json.load(f)
        results[name] = data
        vcount = len(data.get("violations", []))
        eta = data.get("eta_code", 0)
        print(f"  ✅ {name}: η={eta:.3f}, {data['files']} files, {data['lines']} lines, "
              f"{vcount} violations ({elapsed:.1f}s)")

# Summary table
print(f"\n{'='*70}")
print(f"  Multi-Project MSS Audit Summary")
print(f"{'='*70}")
print(f"  {'Project':<12} {'η':>6} {'Files':>6} {'Lines':>8} {'Violations':>10}")
print(f"  {'─'*12} {'─'*6} {'─'*6} {'─'*8} {'─'*10}")
for name, data in results.items():
    vcount = len(data.get("violations", []))
    print(f"  {name:<12} {data['eta_code']:>6.3f} {data['files']:>6} {data['lines']:>8} {vcount:>10}")
# mssclaw comparison
mss_file = os.path.join(outdir, "se_audit_mssclaw.json")
if os.path.exists(mss_file):
    with open(mss_file, encoding='utf-8') as f:
        mss = json.load(f)
    print(f"  {'─'*12} {'─'*6} {'─'*6} {'─'*8} {'─'*10}")
    print(f"  {'mssclaw':<12} {mss['eta_code']:>6.3f} {mss['files']:>6} {mss['lines']:>8} "
          f"{len(mss.get('violations',[])):>10}")

print(f"\n  Key finding: MSS measures what SonarQube cannot —")
print(f"  normative field compliance and stable node fidelity.")
print(f"{'='*70}")
