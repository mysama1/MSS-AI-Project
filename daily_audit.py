#!/usr/bin/env python3
"""MSS Daily System Audit — KB health + VDP status + blackhole + summary"""
import json, os, subprocess, datetime, sys

REPORT_DIR = r'E:\QClaw-Data\reports\daily'
KB_DIR = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'

def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    now = datetime.datetime.now()
    report = {"date": now.isoformat(), "status": "OK", "checks": {}}

    # 1. KB health
    kb_files = [f for f in os.listdir(KB_DIR) if f.endswith('.jsonl')]
    invalid = 0
    for f in kb_files:
        try:
            with open(os.path.join(KB_DIR, f), 'r', encoding='utf-8') as fh:
                json.loads(fh.readline())
        except:
            invalid += 1
    report["checks"]["kb"] = {"total": len(kb_files), "invalid": invalid,
                              "health": "OK" if invalid == 0 else f"WARN({invalid} bad)"}
    if invalid > 0:
        report["status"] = "WARN"

    # 2. VDP scan self-check
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("vdp_scan",
            os.path.join(os.path.dirname(__file__), "vdp_scan.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        result = m.scan_file(os.path.join(os.path.dirname(__file__), "vdp_scan.py"))
        report["checks"]["vdp_self_scan"] = {
            "violations": len(result.get("violations", [])),
            "health": "OK" if len(result.get("violations", [])) < 3 else "WARN"
        }
    except Exception as e:
        report["checks"]["vdp_self_scan"] = {"error": str(e)[:100], "health": "FAIL"}
        report["status"] = "FAIL"

    # 3. Blackhole monitor (test with known text)
    try:
        spec = importlib.util.spec_from_file_location("k3_bh",
            os.path.join(os.path.dirname(__file__), "k3_blackhole_monitor.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        detector = m.MeaningBlackHoleDetector()
        # Test with normal text
        r_normal = detector.analyze("The MSS framework provides a consistent axiomatic foundation.", source="audit")
        # Test with borderline text
        r_border = detector.analyze("I must retry this approach. No alternative exists.", source="audit")
        report["checks"]["blackhole"] = {
            "normal_score": r_normal["bh_score"],
            "border_score": r_border["bh_score"],
            "health": "OK" if r_normal["bh_score"] < 5 else "WARN"
        }
    except Exception as e:
        report["checks"]["blackhole"] = {"error": str(e)[:100], "health": "FAIL"}

    # 4. Git status
    try:
        r = subprocess.run(["git", "log", "--oneline", "-1"],
            cwd=r'E:\AI_Workspace\MSS-AI\project', capture_output=True, timeout=10,
            encoding='utf-8', errors='replace')
        report["checks"]["git"] = {"head": r.stdout.strip()[:80] if r.returncode == 0 else "N/A"}
    except:
        report["checks"]["git"] = {"head": "unavailable"}

    # 5. Module cache pollution
    try:
        spec2 = importlib.util.spec_from_file_location("mcd",
            os.path.join(r'E:\QClaw-Data\skills\mss-vdp', 'module_cache_detector.py'))
        mcd = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mcd)
        infected, _ = mcd.scan([r'E:\QClaw-Data\skills', r'E:\AI_Workspace\MSS-AI'])
        
        # SV_r calculation: running-environment susceptibility
        # SV_r = (N_stale / N_total) × (avg_stale_hours / 24)
        # If no project modules loaded (standalone run), estimate total from disk
        n_stale = len(infected)
        n_total = max(n_stale + len(_), 1)  # safe + infected
        if n_stale > 0:
            stale_hours = sum(c['stale_seconds'] for c in infected) / 3600
            avg_hours = stale_hours / n_stale
            sv_r = (n_stale / n_total) * (avg_hours / 24.0)
        else:
            sv_r = 0.0

        # Thresholds: sv_r < 0.01=OK, < 1.0=WARN, >=1.0=CRITICAL
        if sv_r >= 1.0:
            health = f"CRITICAL(SV_r={sv_r:.2f})"
        elif sv_r >= 0.01:
            health = f"WARN(SV_r={sv_r:.2f})"
        else:
            health = "OK"

        report["checks"]["cache"] = {
            "infected": n_stale, "sv_r": round(sv_r, 4),
            "health": health
        }
        if sv_r >= 0.01:
            if report["status"] == "OK":
                report["status"] = "WARN"
        if sv_r >= 1.0 and report["status"] != "FAIL":
            report["status"] = "CRITICAL"
    except Exception as e:
        report["checks"]["cache"] = {"error": str(e)[:80], "health": "FAIL"}

    # 6. Compression scan: flag entries untouched >30 days
    stale_threshold = now - datetime.timedelta(days=30)
    stale_count = 0
    for f in os.listdir(KB_DIR):
        if not f.endswith('.jsonl'):
            continue
        path = os.path.join(KB_DIR, f)
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        if mtime < stale_threshold:
            stale_count += 1
    report["checks"]["compression"] = {
        "stale_entries": stale_count,
        "threshold_days": 30,
        "health": "OK" if stale_count < 100 else f"WARN({stale_count} stale)"
    }
    if stale_count >= 100:
        if report["status"] == "OK":
            report["status"] = "WARN"

    # Summary
    fails = sum(1 for c in report["checks"].values() if c.get("health") == "FAIL")
    warns = sum(1 for c in report["checks"].values() if c.get("health") == "WARN")
    if fails > 0:
        report["status"] = "FAIL"
    elif warns > 0:
        report["status"] = "WARN"

    # Write report
    filename = now.strftime("audit_%Y-%m-%d_%H%M.json")
    path = os.path.join(REPORT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Console summary
    print(f"MSS Daily Audit: {report['status']}")
    for name, check in report["checks"].items():
        h = check.get("health", "?")
        icon = {"OK": "+", "WARN": "!", "FAIL": "X"}.get(h, "?")
        print(f"  [{icon}] {name}: {h}")
    print(f"\nReport: {path}")

    return 0 if report["status"] == "OK" else 1

if __name__ == "__main__":
    sys.exit(main())
