#!/usr/bin/env python3
"""MSS-VDP Ghost File Cleaner — MFT残留索引清理工具

TRAE SOLO minifilter bug:
  Session结束时清空overlay数据, 但未清理下层MFT路径标记
  → 目录枚举可见, 路径解析全阻塞
  → os.scandir() OK, os.open() FileNotFoundError

Usage:
  python clean_ghosts.py <target_dir>         # 诊断模式
  python clean_ghosts.py <target_dir> --clean # 清理模式
"""

import os, sys, argparse, shutil, json
from datetime import datetime

def find_ghosts(directory):
    """Find ghost files: listable by scandir but unreadable by open."""
    ghosts = []
    locked_dirs = []
    
    for root, dirs, files in os.walk(directory):
        # Check directory itself
        try:
            os.listdir(root)
        except PermissionError:
            locked_dirs.append(root)
            dirs.clear()
            continue
        
        for fname in files:
            fp = os.path.join(root, fname)
            try:
                # Try path-based access
                with open(fp, 'rb') as f:
                    pass
            except FileNotFoundError:
                # Ghost: scandir sees it but open doesn't
                ghosts.append(fp)
            except PermissionError:
                ghosts.append(fp)
    
    return ghosts, locked_dirs

def clean_ghosts(directory, dry_run=True):
    """Remove ghost directories by renaming and recreating."""
    ghosts, locked = find_ghosts(directory)
    results = []
    
    if not ghosts and not locked:
        return {"status": "clean", "ghosts": 0, "locked": 0, "actions": []}
    
    for fp in ghosts:
        action = {
            "path": fp,
            "action": "would-remove" if dry_run else "removed",
        }
        try:
            if not dry_run:
                os.unlink(fp)
            results.append(action)
        except Exception as e:
            action["error"] = str(e)
            results.append(action)
    
    for d in locked:
        action = {
            "path": d,
            "action": "locked-dir",
        }
        results.append(action)
    
    return {
        "status": "cleaned" if not dry_run else "dry-run",
        "ghosts": len(ghosts),
        "locked": len(locked),
        "actions": results,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MSS Ghost File Cleaner")
    parser.add_argument("target", help="Target directory to scan")
    parser.add_argument("--clean", action="store_true", help="Actually remove ghost files")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    
    if not os.path.isdir(args.target):
        print("Error: %s is not a directory" % args.target, file=sys.stderr)
        sys.exit(1)
    
    result = clean_ghosts(args.target, dry_run=not args.clean)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = result["status"]
        print(f"Status: {status}")
        print(f"Ghost files: {result['ghosts']} | Locked dirs: {result['locked']}")
        for a in result.get("actions", []):
            print(f"  [{a['action']}] {a['path']}")
        if not args.clean and result["ghosts"] > 0:
            print("\nRe-run with --clean to remove ghost files")
    
    sys.exit(1 if result["ghosts"] > 0 or result["locked"] > 0 else 0)
