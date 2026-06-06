#!/usr/bin/env python3
"""
TRAE False Sandbox Diagnostic Tool v1.0
Detects minifilter status, blocked files, MFT residuals, and directory enumeration bypass.

Usage:
    py -3.11 trae_diag.py diagnose <directory>
    py -3.11 trae_diag.py list-blocked <directory>
    py -3.11 trae_diag.py bypass <directory> [--rename] [--copy]
"""
import os, sys, subprocess, json, re, shutil, ctypes
from pathlib import Path
from collections import defaultdict

# ── Detection ──────────────────────────────────────────

def check_minifilter() -> dict:
    """Check if TRAE (or similar) minifilter driver is active."""
    result = {
        'active': False,
        'drivers': [],
        'trae_related': []
    }
    try:
        p = subprocess.run(['fltmc', 'filters'], capture_output=True, text=True, timeout=5)
        for line in p.stdout.split('\n'):
            result['drivers'].append(line.strip())
            if any(kw in line.lower() for kw in ['trae', 'tencent', 'tca', 'minifilter', 'overlay', 'virtual']):
                result['trae_related'].append(line.strip())
        result['active'] = len(result['trae_related']) > 0
    except:
        result['error'] = 'fltmc not available (need admin?)'
    return result


def scan_directory(path: str, max_files: int = 500) -> dict:
    """
    Scan directory for file access anomalies.
    Returns: {normal, blocked, hidden, mismatched}
    """
    result = {
        'normal': [],
        'blocked': [],       # File exists but can't be opened
        'hidden': [],        # FindFirstFile shows it, CreateFile denies
        'mismatched': [],    # Metadata visible but content inaccessible
        'total_visible': 0,
        'total_accessible': 0,
    }
    
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        return {'error': f'Not a directory: {path}'}
    
    # Walk directory
    for root, dirs, files in os.walk(path):
        for f in files[:max_files]:
            fp = os.path.join(root, f)
            result['total_visible'] += 1
            
            # Test 1: Does stat work?
            try:
                st = os.stat(fp)
                size = st.st_size
            except PermissionError:
                result['blocked'].append({'path': fp, 'reason': 'stat denied'})
                continue
            except OSError as e:
                if e.winerror in (5, 32, 1920):
                    result['blocked'].append({'path': fp, 'reason': f'OS error {e.winerror}'})
                    continue
            
            # Test 2: Can we read content?
            try:
                with open(fp, 'rb') as fh:
                    fh.read(4)
                result['total_accessible'] += 1
                if result['total_accessible'] <= 5:
                    result['normal'].append(fp)
            except PermissionError:
                result['blocked'].append({'path': fp, 'reason': 'read denied', 'size': size})
            except OSError as e:
                if e.winerror == 1920:  # ERROR_CANT_ACCESS_FILE
                    result['blocked'].append({'path': fp, 'reason': 'cant access (minifilter blocked?)', 'size': size})
                else:
                    result['blocked'].append({'path': fp, 'reason': f'OS error {e.winerror}'})
    
    # Check for directory enumeration bypass
    if result['blocked'] and result['total_accessible'] < result['total_visible'] * 0.5:
        result['enumeration_bypass'] = True
        result['mismatched'] = [b['path'] for b in result['blocked'][:10]]
    
    return result


def find_blocked_files(path: str, max_depth: int = 3) -> list:
    """Find all files that exist on disk but are blocked by minifilter."""
    blocked = []
    path = os.path.abspath(path)
    
    for root, dirs, files in os.walk(path):
        depth = root.replace(path, '').count(os.sep)
        if depth > max_depth:
            dirs.clear()
            continue
        
        for f in files:
            fp = os.path.join(root, f)
            try:
                with open(fp, 'rb') as fh:
                    pass
            except:
                try:
                    st = os.stat(fp)
                    blocked.append({
                        'path': fp,
                        'size': st.st_size,
                        'reason': 'exists on disk, read blocked by filter'
                    })
                except:
                    blocked.append({
                        'path': fp,
                        'reason': 'directory entry exists, all access blocked'
                    })
    
    return blocked


# ── Bypass / Workaround ───────────────────────────────

def bypass_rename(path: str, blocked_files: list = None) -> dict:
    """
    Attempt rename-trick bypass:
    1. Rename blocked file to temp name
    2. Rename back to original
    3. This forces MFT update, potentially clearing minifilter marker
    
    CLASS_A fix only — works for MFT cache stale entries, not driver-level blocks.
    """
    if blocked_files is None:
        blocked_files = find_blocked_files(path)
    
    results = {'fixed': [], 'failed': [], 'untested': len(blocked_files)}
    
    for entry in blocked_files[:20]:  # Limit for safety
        fp = entry['path']
        try:
            tmp = fp + '.trae_bypass_tmp'
            os.rename(fp, tmp)
            os.rename(tmp, fp)
            # Verify
            try:
                with open(fp, 'rb') as fh:
                    fh.read(4)
                results['fixed'].append(fp)
            except:
                results['failed'].append({'path': fp, 'reason': 'rename succeeded but still blocked'})
        except OSError as e:
            results['failed'].append({'path': fp, 'reason': f'rename failed: {e}'})
    
    results['untested'] = len(blocked_files) - len(results['fixed']) - len(results['failed'])
    return results


def bypass_copy_out(path: str, dest: str, blocked_files: list = None) -> dict:
    """
    Attempt copy-out bypass:
    Read through the minifilter's CreateFile bypass gap.
    Some minifilters allow READ but not WRITE through certain paths.
    """
    if blocked_files is None:
        blocked_files = find_blocked_files(path)
    
    results = {'copied': [], 'failed': []}
    os.makedirs(dest, exist_ok=True)
    
    for entry in blocked_files[:50]:
        fp = entry['path']
        rel = os.path.relpath(fp, path)
        dp = os.path.join(dest, rel)
        try:
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            shutil.copy2(fp, dp)
            results['copied'].append(fp)
        except:
            # Try raw read
            try:
                with open(fp, 'rb') as src:
                    with open(dp, 'wb') as dst:
                        while True:
                            chunk = src.read(65536)
                            if not chunk: break
                            dst.write(chunk)
                results['copied'].append(fp)
            except:
                results['failed'].append({'path': fp, 'reason': 'all copy methods failed'})
    
    return results


# ── Full Diagnosis Report ─────────────────────────────

def full_diagnosis(path: str) -> dict:
    """Run complete TRAE sandbox diagnosis."""
    report = {
        'target': path,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'minifilter': check_minifilter(),
        'scan': {},
        'verdict': ''
    }
    
    # Scan for anomalies
    report['scan'] = scan_directory(path)
    
    # Build verdict
    s = report['scan']
    if s.get('error'):
        report['verdict'] = f"ERROR: {s['error']}"
    elif len(s.get('blocked', [])) > 0 and s.get('enumeration_bypass', False):
        report['verdict'] = 'CONFIRMED: TRAE false sandbox detected — directory enumeration bypass active'
        report['severity'] = 'PATHOLOGY_6_DETECTABLE_NOT_FIXABLE'
        report['a5_projection'] = True
        report['recommendation'] = 'Files marked BLOCKED by minifilter. Try bypass_rename (CLASS_A) or copy to new directory.'
    elif len(s.get('blocked', [])) > 0:
        report['verdict'] = 'SUSPECTED: Blocked files found without enumeration bypass'
        report['severity'] = 'NEEDS_INVESTIGATION'
    elif s.get('total_visible', 0) == 0:
        report['verdict'] = 'CLEAN: No files or directory empty'
    else:
        report['verdict'] = 'CLEAN: All files accessible'
    
    return report


# ── CLI Entry Point ──
def main():
    """Entry point for vdp-trae console script."""
    if len(sys.argv) < 2:
        print("TRAE False Sandbox Diagnostic Tool v1.0")
        print()
        print("Commands:")
        print("  diagnose <dir>       Full diagnosis report")
        print("  list-blocked <dir>   List blocked files")
        print("  bypass-rename <dir>  Attempt rename trick")
        print("  bypass-copy <dir> <dest>  Copy accessible files out")
        sys.exit(0)

if __name__ == '__main__':
    main()
    
    cmd = sys.argv[1]
    
    if cmd == 'diagnose':
        path = sys.argv[2] if len(sys.argv) > 2 else '.'
        report = full_diagnosis(path)
        # Print concise
        print(f"Target: {report['target']}")
        print(f"Minifilter active: {report['minifilter']['active']}")
        if report['minifilter']['trae_related']:
            for d in report['minifilter']['trae_related']:
                print(f"  Driver: {d}")
        s = report['scan']
        print(f"Files visible: {s.get('total_visible', 0)}")
        print(f"Files accessible: {s.get('total_accessible', 0)}")
        print(f"Files blocked: {len(s.get('blocked', []))}")
        if s.get('enumeration_bypass'):
            print(f"🔴 Enumeration BYPASS detected!")
            print(f"   Dir shows {s['total_visible']} files, but only {s['total_accessible']} are readable")
        print(f"\nVerdict: {report['verdict']}")
        
        # Save full JSON
        import json
        report_path = os.path.join(os.path.dirname(__file__) if '__file__' in dir() else '.', '.run', 'trae_diag_report.json')
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nFull report: {report_path}")
    
    elif cmd == 'list-blocked':
        path = sys.argv[2] if len(sys.argv) > 2 else '.'
        blocked = find_blocked_files(path)
        print(f"Blocked files: {len(blocked)}")
        for b in blocked[:30]:
            print(f"  {b['path']}")
            print(f"    Size: {b.get('size', 'N/A')} | Reason: {b.get('reason', 'unknown')}")
    
    elif cmd == 'bypass-rename':
        path = sys.argv[2] if len(sys.argv) > 2 else '.'
        print(f"Attempting rename bypass on: {path}")
        result = bypass_rename(path)
        print(f"Fixed: {len(result['fixed'])} | Failed: {len(result['failed'])} | Untested: {result['untested']}")
        for f in result['fixed'][:5]:
            print(f"  ✅ {f}")
        for f in result['failed'][:5]:
            print(f"  ❌ {f['path']}: {f['reason']}")
    
    elif cmd == 'bypass-copy':
        path = sys.argv[2] if len(sys.argv) > 2 else '.'
        dest = sys.argv[3] if len(sys.argv) > 3 else path + '_recovered'
        print(f"Copying from {path} → {dest}")
        result = bypass_copy_out(path, dest)
        print(f"Copied: {len(result['copied'])} | Failed: {len(result['failed'])}")
        for f in result['failed'][:5]:
            print(f"  ❌ {f['path']}: {f['reason']}")
