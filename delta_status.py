#!/usr/bin/env python3
"""MSS Δ Status Check — detect if system is approaching closure (Δ→0)."""
import sys, os, json, re
from datetime import datetime, timedelta

# Configurable project root
PROJECT_ROOT = os.environ.get('MSS_PROJECT_ROOT', r'E:\AI_Workspace\MSS-AI\project')

def delta_status(tau_months=3, output_json=False):
    tau = timedelta(days=tau_months*30)
    now = datetime.now()
    
    papers_dir = os.path.join(PROJECT_ROOT, 'papers')
    kb_dir = os.path.join(PROJECT_ROOT, 'knowledge_base')
    
    # S1: Theory incompleteness annotations
    s1_active = False
    if os.path.isdir(papers_dir):
        for f in os.listdir(papers_dir):
            fp = os.path.join(papers_dir, f)
            if not f.endswith('.md'): continue
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                if now - mtime < tau:
                    with open(fp, encoding='utf-8') as fh:
                        content = fh.read()
                    if 'known unknown' in content.lower() or '不完备' in content or 'has not been' in content.lower():
                        s1_active = True
                        break
            except: pass
    
    # S2: Counterexample response
    s2_active = False
    # Check if five_ways_mss_fails was recently touched
    fails_path = os.path.join(papers_dir, 'five_ways_mss_fails.md') if os.path.isdir(papers_dir) else ''
    if fails_path and os.path.exists(fails_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(fails_path))
        s2_active = (now - mtime) < tau
    
    # S3: Dissent space — detect commentary/critique activity
    s3_active = False
    if os.path.isdir(papers_dir):
        for f in os.listdir(papers_dir):
            fp = os.path.join(papers_dir, f)
            if not f.endswith('.md'): continue
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                if now - mtime < tau:
                    s3_active = True
                    break
            except: pass
    
    # S4: Output validity - simplified check
    s4_active = False
    if os.path.isdir(kb_dir):
        recent_new = 0
        recent_total = 0
        for root, dirs, files in os.walk(kb_dir):
            for f in files:
                if not f.endswith('.jsonl'): continue
                fp = os.path.join(root, f)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                    recent_total += 1
                    if now - mtime < tau:
                        recent_new += 1
                except: pass
        s4_active = recent_new > 0 and recent_new < recent_total * 0.1  # <10% new = healthy restraint
    
    active = sum([s1_active, s2_active, s3_active, s4_active])
    
    status = "HEALTHY" if active >= 3 else ("WARNING" if active >= 2 else "CRITICAL")
    
    result = {
        'timestamp': now.strftime('%Y-%m-%d %H:%M'),
        'delta_status': status,
        'active_signals': active,
        'signals': {
            'S1_incompleteness': s1_active,
            'S2_counterexample': s2_active,
            'S3_dissent_space': s3_active,
            'S4_output_validity': s4_active
        },
        'project_root': PROJECT_ROOT,
        'tau_months': tau_months
    }
    
    if output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if status != "CRITICAL" else 1
    
    print("=== MSS Delta Status ===")
    print(f"Timestamp: {now.strftime('%Y-%m-%d %H:%M')}")
    print()
    print(f"S1 Theory Incompleteness: {'ACTIVE' if s1_active else 'INACTIVE'}")
    print(f"S2 Counterexample Response: {'ACTIVE' if s2_active else 'INACTIVE'}")
    print(f"S3 Dissent Space: {'ACTIVE' if s3_active else 'INACTIVE'}")
    print(f"S4 Output Validity: {'ACTIVE' if s4_active else 'INACTIVE'}")
    print()
    print(f"Delta Status: {status} (signals active: {active}/4)")
    print()
    
    if status == "CRITICAL":
        print("WARNING: Delta approaching zero. System may be closing.")
        print("Recommended: Trigger 3-tier reboot sequence.")
    elif status == "WARNING":
        print("CAUTION: Delta signals low. Monitor closely.")
    else:
        print("Delta > 0 — System is breathing.")
    
    return 0 if status != "CRITICAL" else 1

def main():
    import argparse
    p = argparse.ArgumentParser(description='MSS Delta Status Check')
    p.add_argument('--tau', type=int, default=3, help='Months window for signal detection')
    p.add_argument('--json', action='store_true', help='Output as JSON (for dashboard)')
    args = p.parse_args()
    sys.exit(delta_status(tau_months=args.tau, output_json=args.json))

if __name__ == '__main__':
    main()
