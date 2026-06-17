"""
safe_run.py — Cross-platform script runner (P1-2 engineering fix).

Problem: Direct inline PowerShell via exec causes encoding corruption,
         $args splitting, and special character handling failures.
         Root cause documented as "写文件→运行文件" (write-file-then-run).

Solution: Always write script content to a temp UTF-8-BOM .ps1 file,
          then execute it via subprocess. This avoids the encoding
          corruption path entirely.

Usage:
    python scripts/safe_run.py 'get-content' --content 'Get-Content data.txt'
    python scripts/safe_run.py 'invoke' --file deploy.ps1 --params '-Force'
"""
import subprocess, sys, tempfile, os, json, argparse
from pathlib import Path

def write_temp_ps1(content: str) -> Path:
    """Write PowerShell content to temp file with UTF-8 BOM."""
    tmp = Path(tempfile.mktemp(suffix='.ps1'))
    # UTF-8 BOM: PowerShell 5.1 requires BOM to read UTF-8 correctly
    tmp.write_bytes(b'\xef\xbb\xbf' + content.encode('utf-8'))
    return tmp

def run_ps1_content(content: str, params: str = "") -> dict:
    """Run PowerShell script from content string. Returns {rc, stdout, stderr}."""
    tmp = write_temp_ps1(content)
    try:
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", str(tmp)]
        if params:
            cmd.extend(params.split())
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=120)
        return {
            "rc": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "tmp": str(tmp)
        }
    finally:
        tmp.unlink(missing_ok=True)

def run_ps1_file(path: str, params: str = "") -> dict:
    """Run existing .ps1 file safely. Returns {rc, stdout, stderr}."""
    # Re-write with BOM to ensure correct encoding
    content = Path(path).read_text(encoding='utf-8-sig')
    tmp = write_temp_ps1(content)
    try:
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", str(tmp)]
        if params:
            cmd.extend(params.split())
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=120)
        return {
            "rc": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "source": path
        }
    finally:
        tmp.unlink(missing_ok=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Safe PowerShell runner")
    ap.add_argument("action", choices=["get-content", "invoke"])
    ap.add_argument("--content", help="PowerShell code as string")
    ap.add_argument("--file", help="Path to existing .ps1 file")
    ap.add_argument("--params", default="", help="Arguments to pass to script")
    args = ap.parse_args()

    if args.action == "get-content":
        if not args.content:
            sys.exit("--content required for get-content action")
        result = run_ps1_content(args.content, args.params)
    elif args.action == "invoke":
        if not args.file:
            sys.exit("--file required for invoke action")
        result = run_ps1_file(args.file, args.params)
    else:
        sys.exit(f"Unknown action: {args.action}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(result["rc"])
