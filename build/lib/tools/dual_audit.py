#!/usr/bin/env python3
"""
D5-040 Phase 3: MSS Dual Audit — Integrates mss_review_runner (K3→MSS) + mss_meaning_audit_v02 (MSS原生)
"""
import os, sys, json, argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from mss_review_runner import MSSReviewRunner, MSSReviewReport, ReviewFinding, MSSLevel

# Import MSS meaning audit
import importlib.util
_audit_spec = importlib.util.spec_from_file_location('mss_meaning_audit_v02',
    os.path.join(ROOT, 'mss_meaning_audit_v02.py'))
_audit = importlib.util.module_from_spec(_audit_spec)
_audit_spec.loader.exec_module(_audit)

def dual_audit(filepath):
    """Run both review systems and merge findings."""
    result = {
        "file": filepath,
        "audit_time": datetime.now().isoformat(),
        "mss_review": {},
        "mss_meaning": {},
        "merged": {"score": 0, "findings": []}
    }

    # 1. MSS Review Runner (K3→MSS adapted)
    try:
        runner = MSSReviewRunner(filepath)
        report = runner.run()
        result["mss_review"] = {
            "score": report.mss_total_score,
            "logical_rigidity": report.logical_rigidity_score,
            "thermal_tax": report.thermal_tax_index,
            "meaning_fidelity": report.meaning_fidelity_score,
            "verdict": report.verdict,
            "p0_count": sum(1 for f in report.findings if f.level == MSSLevel.P0),
            "p1_count": sum(1 for f in report.findings if f.level == MSSLevel.P1),
        }
        for f in report.findings:
            result["merged"]["findings"].append({
                "level": f.level.value,
                "source": "review_runner",
                "axis": f.axis,
                "line": f.line,
                "message": f.message[:120],
                "axiom": f.axiom
            })
    except Exception as e:
        result["mss_review"] = {"error": str(e)}

    # 2. MSS Meaning Audit (MSS原生)
    try:
        auditor = _audit.MSSMeaningAuditor()
        areport = auditor.audit_file(filepath)
        result["mss_meaning"] = {
            "score": areport.total_score,
            "logical_rigidity": areport.logical_rigidity,
            "thermal_tax": areport.thermal_tax_index,
            "meaning_fidelity": areport.meaning_fidelity,
        }
        for issue in areport.issues:
            result["merged"]["findings"].append({
                "level": issue.level.value,
                "source": "meaning_audit",
                "axis": issue.category,
                "line": issue.line,
                "message": issue.message[:120],
                "fix": issue.fix_suggestion[:80] if issue.fix_suggestion else ""
            })
    except Exception as e:
        result["mss_meaning"] = {"error": str(e)}

    # Merge scores
    r_score = result["mss_review"].get("score", 0)
    m_score = result["mss_meaning"].get("score", 0)
    result["merged"]["score"] = round((r_score + m_score) / 2, 1)

    # Merge verdict
    p0_count = result["mss_review"].get("p0_count", 0)
    if p0_count > 0 or result["merged"]["score"] < 50:
        result["merged"]["verdict"] = "REJECT"
    elif result["merged"]["score"] < 70:
        result["merged"]["verdict"] = "REQUEST_CHANGES"
    else:
        result["merged"]["verdict"] = "APPROVE"

    return result

def dual_audit_batch(root_path, max_files=20):
    """Batch review entire project."""
    results = []
    py_files = []
    for dirpath, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in ('__pycache__','node_modules','.git','unsloth_compiled_cache','releases','backups','archive','resilience_reports','knowledge_base','knowledge_base_organized')]
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(dirpath, f))

    print(f"Found {len(py_files)} Python files. Auditing up to {max_files}...")
    for fp in py_files[:max_files]:
        try:
            r = dual_audit(fp)
            results.append({
                "file": os.path.relpath(fp, root_path),
                "score": r["merged"]["score"],
                "verdict": r["merged"]["verdict"],
                "p0": r["mss_review"].get("p0_count", 0)
            })
        except Exception as e:
            results.append({"file": fp, "error": str(e)})

    results.sort(key=lambda x: x.get("score", 0))
    summary = {
        "project": root_path,
        "files_audited": len(results),
        "avg_score": round(sum(r.get("score", 0) for r in results) / max(len(results), 1), 1),
        "approved": sum(1 for r in results if r.get("verdict") == "APPROVE"),
        "rejected": sum(1 for r in results if r.get("verdict") == "REJECT"),
        "bottom_10": results[:10]
    }
    return summary

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MSS Dual Audit (D5-040 Phase 3)")
    ap.add_argument("target", help="File or directory")
    ap.add_argument("--batch", action="store_true", help="Batch mode")
    ap.add_argument("--max", type=int, default=20)
    args = ap.parse_args()

    if args.batch:
        result = dual_audit_batch(args.target, args.max)
    else:
        result = dual_audit(args.target)

    print(json.dumps(result, indent=2, ensure_ascii=False))