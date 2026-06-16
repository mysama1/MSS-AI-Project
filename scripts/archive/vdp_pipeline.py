#!/usr/bin/env python3
"""
MSS-VDP Unified Pipeline — 一键扫描→聚合→报告
DEV-003: 四工具自动化集成
"""
import sys, os, json, time, argparse, subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

HERE = Path(__file__).resolve().parent

def green(s): return f"\033[32m{s}\033[0m"
def red(s): return f"\033[31m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def cyan(s): return f"\033[36m{s}\033[0m"

def run_tool(name: str, cmd: list, cwd=None) -> Dict:
    """Run a tool and capture its JSON output."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          cwd=str(cwd or HERE), encoding='utf-8')
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
        return {"error": r.stderr[:500], "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}

def find_python_files(directory: str) -> List[str]:
    """Recursively collect all .py files."""
    files = []
    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.git')]
        for f in filenames:
            if f.endswith('.py'):
                files.append(os.path.join(root, f))
    return files

def find_js_files(directory: str) -> List[str]:
    """Recursively collect all .js/.ts/.jsx/.tsx/.mjs/.cjs files."""
    js_ext = {'.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs', '.mts', '.cts'}
    files = []
    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', '.git', 'dist', 'build', '.next')]
        for f in filenames:
            ext = os.path.splitext(f)[1]
            if ext in js_ext:
                files.append(os.path.join(root, f))
    return files

def find_rust_files(directory: str) -> List[str]:
    """Recursively collect all .rs files."""
    files = []
    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('target', 'node_modules', '.git')]
        for f in filenames:
            if f.endswith('.rs'):
                files.append(os.path.join(root, f))
    return files

def run_pipeline(target: str, outdir: str = None, strictness: float = 0.7):
    """Execute full VDP pipeline on target directory."""
    start = time.time()
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    py = sys.executable
    if not outdir:
        outdir = os.path.join(target, '.vdp_reports')

    print(cyan(f"\n{'='*60}"))
    print(cyan(f"  MSS-VDP Unified Pipeline  |  {timestamp}"))
    print(cyan(f"  Target: {target}"))
    print(cyan(f"  Reports: {outdir}"))
    print(cyan(f"{'='*60}\n"))

    results = {
        "timestamp": timestamp,
        "target": target,
        "strictness": strictness,
        "stages": {},
        "summary": {}
    }

    # ── Stage 1: vdp_scan.py (V1-V6) ──
    print(yellow("[1/3] vdp_scan — V1-V6 violations"))
    py_files = find_python_files(target)
    scan_results = []
    scan_errors = 0
    for f in py_files:
        r = run_tool("vdp_scan", [py, str(HERE/"vdp_scan.py"), f])
        if "error" not in r:
            scan_results.append(r)
        else:
            scan_errors += 1

    scan_violations = sum(len(r.get("violations", [])) for r in scan_results)
    results["stages"]["vdp_scan"] = {
        "files_scanned": len(py_files),
        "files_with_violations": sum(1 for r in scan_results if r.get("violations")),
        "total_violations": scan_violations,
        "errors": scan_errors
    }
    print(f"  Scanned {len(py_files)} files → {scan_violations} violations, {scan_errors} errors")

    # ── Stage 1b: js_scan.py (JS/TS) ──
    print(yellow("[1b] js_scan — JS/TS V1-V9 violations"))
    js_files = find_js_files(target)
    js_scan_results = []
    js_scan_errors = 0
    if js_files:
        js_scan_path = str(HERE/"js_scan.py")
        for f in js_files[:100]:  # Cap at 100 files
            r = run_tool("js_scan", [py, js_scan_path, f, "--json"])
            if "error" not in r:
                js_scan_results.append(r)
            else:
                js_scan_errors += 1
    
    js_violations = sum(len(r.get("violations", [])) for r in js_scan_results)
    results["stages"]["js_scan"] = {
        "files_scanned": len(js_files),
        "files_with_violations": sum(1 for r in js_scan_results if r.get("violations")),
        "total_violations": js_violations,
        "errors": js_scan_errors
    }
    print(f"  Scanned {len(js_files)} JS/TS files → {js_violations} violations, {js_scan_errors} errors")

    # ── Stage 1c: rust_scan.py (Rust) ──
    print(yellow("[1c] rust_scan — Rust R1-R5 violations"))
    rust_files = find_rust_files(target)
    rust_scan_results = []
    rust_scan_errors = 0
    if rust_files:
        rust_scan_path = str(HERE/"rust_scan.py")
        for f in rust_files[:100]:
            r = run_tool("rust_scan", [py, rust_scan_path, f, "--json"])
            if "error" not in r:
                rust_scan_results.append(r)
            else:
                rust_scan_errors += 1
    
    rust_violations = sum(len(r.get("violations", [])) for r in rust_scan_results)
    results["stages"]["rust_scan"] = {
        "files_scanned": len(rust_files),
        "files_with_violations": sum(1 for r in rust_scan_results if r.get("violations")),
        "total_violations": rust_violations,
        "errors": rust_scan_errors
    }
    print(f"  Scanned {len(rust_files)} Rust files → {rust_violations} violations, {rust_scan_errors} errors")

    # ── Stage 2: vdp_precommit.py (CLI-001, NAMING-002) ──
    print(yellow("[2/3] vdp_precommit — CLI/NAMING checks"))
    pre_results = run_tool("vdp_precommit", [
        py, str(HERE/"vdp_precommit.py"), "check", "--dir", target, "--json"
    ])
    pre_count = 0
    if isinstance(pre_results, list):
        pre_count = sum(r.get("count", 0) for r in pre_results)
    elif isinstance(pre_results, dict) and "error" not in pre_results:
        pre_count = pre_results.get("count", 0)
    results["stages"]["vdp_precommit"] = {
        "total_violations": pre_count,
        "raw": pre_results if not isinstance(pre_results, list) else None,
        "files": len(pre_results) if isinstance(pre_results, list) else 0
    }
    print(f"  Pre-commit → {pre_count} violations")

    # ── Stage 3: unified_audit.py ──
    print(yellow("[3/3] unified_audit — 四层审计"))
    # Collect all .py file contents as audit input
    audit_input = []
    for f in py_files[:50]:  # Cap at 50 files to avoid token overflow
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                audit_input.append(f"{f}\n{fh.read()}")
        except:
            pass

    # Write to temp file for unified_audit
    import tempfile
    tf = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    tf.write("\n\n".join(audit_input))
    tf.close()

    ua_result = run_tool("unified_audit", [
        py, str(HERE/"unified_audit.py"),
        "--output", tf.name,
        "--strictness", str(strictness),
        "--json"
    ])
    os.unlink(tf.name)

    ua_violations = 0
    if isinstance(ua_result, dict) and "error" not in ua_result:
        ua_violations = ua_result.get("scores", {}).get("total_violations", 0)
        results["stages"]["unified_audit"] = {
            "verdict": ua_result.get("verdict"),
            "composite_score": ua_result.get("scores", {}).get("composite"),
            "total_violations": ua_violations,
            "T_total": ua_result.get("thermal_tax", {}).get("T_total"),
            "layers": ua_result.get("layers", {}),
            "elapsed_ms": ua_result.get("elapsed_ms")
        }
    else:
        results["stages"]["unified_audit"] = {"error": str(ua_result.get("error", "unknown"))}
    print(f"  Audit → {results['stages']['unified_audit'].get('total_violations', '?')} violations")

    # ── Aggregate ──
    total_v = scan_violations + js_violations + rust_violations + pre_count + ua_violations
    results["summary"] = {
        "total_violations": total_v,
        "scan_violations": scan_violations,
        "js_violations": js_violations,
        "rust_violations": rust_violations,
        "precommit_violations": pre_count,
        "audit_violations": ua_violations,
        "elapsed_seconds": round(time.time() - start, 1)
    }

    # ── Save results ──
    os.makedirs(outdir, exist_ok=True)
    report_path = os.path.join(outdir, f"vdp_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # ── Generate HTML ──
    try:
        from report_generator import generate_html
        html = generate_html(ua_result if isinstance(ua_result, dict) else {}, 
                           f"MSS-VDP Report — {os.path.basename(target)}")
        html_path = report_path.replace('.json', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        results["summary"]["html_report"] = html_path
    except Exception as e:
        print(f"  HTML generation skipped: {e}")
    
    # ── Generate PDF ──
    try:
        from report_pdf import generate_pdf
        import traceback
        pdf_path = report_path.replace('.json', '.pdf')
        safe_title = f"MSS-VDP Report - {os.path.basename(target)}"
        generate_pdf(results["stages"].get("unified_audit", {}), pdf_path, safe_title)
        results["summary"]["pdf_report"] = pdf_path
    except Exception as e:
        traceback.print_exc()
        print(f"  PDF generation skipped: {e}")

    # ── Print summary ──
    elapsed = results["summary"]["elapsed_seconds"]
    print(cyan(f"\n{'='*60}"))
    print(cyan(f"  PIPELINE COMPLETE — {elapsed}s"))
    print(cyan(f"{'='*60}"))
    print(f"  V1-V6 scan:      {green(scan_violations)} violations ({len(py_files)} files)")
    print(f"  JS/TS scan:      {green(js_violations)} violations ({len(js_files)} files)")
    print(f"  Rust scan:       {green(rust_violations)} violations ({len(rust_files)} files)")
    print(f"  Pre-commit:      {green(pre_count)} violations")
    print(f"  Unified audit:   {green(ua_violations)} violations")
    print(f"  TOTAL:           {red(total_v) if total_v > 0 else green(total_v)} violations")
    print(f"  JSON report:     {report_path}")
    if "html_report" in results["summary"]:
        print(f"  HTML report:     {results['summary']['html_report']}")
    if "pdf_report" in results["summary"]:
        print(f"  PDF report:      {results['summary']['pdf_report']}")
    print()

    return results


def main():
    ap = argparse.ArgumentParser(description="MSS-VDP Unified Pipeline — 一键扫描→报告")
    ap.add_argument("target", nargs='+', help="Target directory(s) to scan")
    ap.add_argument("--outdir", "-o", help="Output directory for reports")
    ap.add_argument("--strictness", "-s", type=float, default=0.7,
                   help="Audit strictness (0.0-1.0)")
    ap.add_argument("--json", action="store_true", help="Output JSON only")
    args = ap.parse_args()

    all_results = []
    for target in args.target:
        if not os.path.isdir(target):
            print(f"Skipping (not a directory): {target}", file=sys.stderr)
            continue
        results = run_pipeline(target, args.outdir, args.strictness)
        all_results.append(results)

    if not all_results:
        print("Error: no valid targets", file=sys.stderr)
        sys.exit(1)
    
    if args.json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))
    
    # Aggregate across all projects
    total_v = sum(r["summary"]["total_violations"] for r in all_results)
    print(cyan(f"\n{'='*60}"))
    print(cyan(f"  BATCH COMPLETE — {len(all_results)} project(s)"))
    print(cyan(f"  TOTAL: {red(total_v) if total_v > 0 else green(total_v)} violations"))
    print(cyan(f"{'='*60}"))
    
    sys.exit(0 if total_v == 0 else 1)


if __name__ == "__main__":
    main()
