#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS Skill API v2.3 — kb_query + VDP scan/audit/vaccine
NSSM-managed on port 53000.
"""
import sys, os, subprocess, json, re, tempfile
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# Paths
SKILL_DIR = os.path.join(os.path.dirname(__file__), "mss-vdp")
KB_QUERY = os.path.join(os.path.dirname(__file__), "mss-knowledge-navigator", "scripts", "kb_query.py")
VDP_SCAN = os.path.join(SKILL_DIR, "vdp_scan.py")
VDP_VACCINE = os.path.join(SKILL_DIR, "vdp_vaccine.py")
JS_SCAN = os.path.join(SKILL_DIR, "js_scan.py")
RUST_SCAN = os.path.join(SKILL_DIR, "rust_scan.py")
JAVA_SCAN = os.path.join(SKILL_DIR, "java_cpp_scan.py")
GO_SCAN = os.path.join(SKILL_DIR, "go_scan.py")
RUBY_SCAN = os.path.join(SKILL_DIR, "ruby_scan.py")
PHP_SCAN = os.path.join(SKILL_DIR, "php_scan.py")
KOTLIN_SCAN = os.path.join(SKILL_DIR, "kotlin_scan.py")
CSHARP_SCAN = os.path.join(SKILL_DIR, "csharp_scan.py")
KB_VECTOR = os.path.join(os.path.dirname(__file__), "mss-knowledge-navigator", "scripts", "kb_vector.py")
VDP_ANCHOR = os.path.join(SKILL_DIR, "vdp_anchor.py")
VDP_PRECOMMIT = os.path.join(SKILL_DIR, "vdp_precommit.py")
PS_VERIFY = os.path.join(SKILL_DIR, "ps_verify.py")
PIPELINE = os.path.join(SKILL_DIR, "vdp_pipeline.py")
FUZZER = os.path.join(SKILL_DIR, "vdp_fuzzer.py")

# Lazy-load TF-IDF lexical checker (NOT semantic — measures word overlap only)
_lexical_guard = None

def _get_lexical():
    global _lexical_guard
    if _lexical_guard is None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mss-vdp"))
        from vdp_lexical import LexicalGuard
        _lexical_guard = LexicalGuard()
    return _lexical_guard

app = FastAPI(title="MSS Skill API", version="2.4")

# ── Models ──
class QueryRequest(BaseModel):
    q: str = ""
    limit: int = 10

class VDPScanRequest(BaseModel):
    artifact: str = ""
    artifact_type: str = "auto"
    rules: list = ["V1","V2","V3","V4","V5","V6","V7"]
    semantic: bool = False
    user_messages: list = []
    verified_facts: list = []
    format: str = "json"  # "json" | "html"

class AuditRequest(BaseModel):
    transcript: str = ""
    file: str = ""
    checks: list = ["V1","V2","V3","V4","V5","V6","V7"]
    semantic: bool = False
    user_messages: list = []
    verified_facts: list = []

class KBSearchRequest(BaseModel):
    q: str
    k: int = 10
    min_score: float = 0.0


# ═══════════════════════════════════════════
#  VDP INLINE SCAN ENGINE (zero-subprocess)
# ═══════════════════════════════════════════

def _detect_type(content: str) -> str:
    """Detect artifact type from content."""
    if re.search(r'(Get-Content|Set-Content|Write-Host|Invoke-RestMethod|ForEach-Object)', content):
        return "powershell_script"
    if re.search(r'(def |import \w+|from \w+ import|if __name__)', content):
        return "python_script"
    return "agent_plan"

def _v1_check(content: str, atype: str):
    """V1: File I/O without existence precheck."""
    violations = []
    if atype in ("powershell_script", "auto"):
        io_ps = re.compile(r'(Get-Content|Set-Content|Add-Content|Out-File|Copy-Item\b.*-Destination)', re.I)
        pre_ps = re.compile(r'(Test-Path|try\s*\{|-ErrorAction\b)', re.I)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if io_ps.search(line):
                ctx = '\n'.join(lines[max(0,i-5):i])
                if not pre_ps.search(ctx):
                    violations.append({"rule":"V1","loc":"L%d"%(i+1),"kind":"NO_PATH_PRECHECK","quote":line.strip()[:100],"fix":"Add: Test-Path $target before file access"})
                    break
    if atype in ("python_script", "auto") and not violations:
        io_py = re.compile(r'\b(open|subprocess\.run)\s*\(')
        pre_py = re.compile(r'(os\.path\.exists|os\.path\.isfile|FileNotFoundError|try:)')
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if io_py.search(line):
                ctx = '\n'.join(lines[max(0,i-5):i])
                if not pre_py.search(ctx):
                    violations.append({"rule":"V1","loc":"L%d"%(i+1),"kind":"NO_PATH_PRECHECK","quote":line.strip()[:100],"fix":"Add: if not os.path.exists(path): raise FileNotFoundError"})
                    break
    return violations

def _v2_check(content: str, atype: str):
    """V2: Inferred cause without errno evidence."""
    violations = []
    inf = re.compile(r'((?:可能|看起来|好像|估计|大概)\w{0,3}(?:被?\s*(?:沙箱|拦截|限制|不允许|block|阻止))|(?:sandbox|blocked|permission\s*denied)\b)', re.I)
    evd = re.compile(r'(\$LASTEXITCODE|exit_?code|errno\b|stderr|HTTP\s+\d{3}|\$\?|Exception\.Message)', re.I)
    for m in inf.finditer(content):
        before = content[max(0,m.start()-300):m.end()+200]
        if not evd.search(before):
            ln = content[:m.start()].count('\n')+1
            violations.append({"rule":"V2","loc":"L%d"%ln,"kind":"INFERRED_CAUSE_NO_ERRNO","quote":m.group(0)[:100],"fix":"Report raw stderr/exit_code instead of guessing cause"})
            break
    return violations

def _v3_check(content: str, atype: str):
    """V3: I/O without explicit encoding."""
    violations = []
    if atype in ("powershell_script", "auto"):
        io_ps = re.compile(r'(Out-File|Set-Content|Add-Content|WriteAllText)\b', re.I)
        enc_ps = re.compile(r'-Encoding\b', re.I)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if io_ps.search(line) and not enc_ps.search(line):
                violations.append({"rule":"V3","loc":"L%d"%(i+1),"kind":"IMPLICIT_ENCODING","quote":line.strip()[:100],"fix":"Add: -Encoding UTF8"})
                break
    if atype in ("python_script", "auto") and not violations:
        io_py = re.compile(r'\bopen\s*\([^)]*[\"\']w[\"\']')
        enc_py = re.compile(r'encoding\s*=')
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if io_py.search(line) and not enc_py.search(line):
                violations.append({"rule":"V3","loc":"L%d"%(i+1),"kind":"IMPLICIT_ENCODING","quote":line.strip()[:100],"fix":"Add: encoding='utf-8'"})
                break
    return violations

def _v4_check(content: str, atype: str):
    """V4: Overwrite without backup/diff."""
    violations = []
    ow = re.compile(r'(Set-Content|Out-File\b.*-Force|WriteAllText|WriteAllBytes)', re.I)
    bk = re.compile(r'(Copy-Item.*\.bak|diff\b|backup|<<<APPEND)', re.I)
    for m in ow.finditer(content):
        ctx = content[max(0,m.start()-200):m.end()+500]
        if not bk.search(ctx):
            ln = content[:m.start()].count('\n')+1
            violations.append({"rule":"V4","loc":"L%d"%ln,"kind":"NO_BACKUP_BEFORE_OVERWRITE","quote":m.group(0)[:100],"fix":"Backup first: Copy-Item $target '$target.bak'; or output diff"})
            break
    return violations

def _v5_check(content: str, atype: str):
    """V5: Retry loop without circuit breaker."""
    violations = []
    loop = re.compile(r'(for\s*\(\s*\$?\w+.*;;|while\s*\(\s*True\b|while\s*\(\s*1\b)', re.I)
    breaker = re.compile(r'(\$maxAttempts|\$max_retries|circuit_breaker|fallback|DEGRADED|break\s*$)', re.I)
    retry = re.compile(r'(retry|attempt|tries|重试|失败)', re.I)
    for m in loop.finditer(content):
        ctx = content[m.start():m.start()+1000]
        if retry.search(ctx) and not breaker.search(ctx):
            ln = content[:m.start()].count('\n')+1
            violations.append({"rule":"V5","loc":"L%d"%ln,"kind":"RETRY_NO_BREAKER","quote":m.group(0)[:100],"fix":"Add: max_retries=2 with circuit breaker and DEGRADED fallback"})
            break
    return violations

def _v6_check(content: str, atype: str):
    """V6: Unanchored existence claims."""
    violations = []
    claim = re.compile(r'(?:文件|目录|路径|配置|脚本)\w{0,3}[A-Za-z]:\\[^\s\"\'<]{3,}', re.I)
    evd = re.compile(r'(Test-Path|dir\b|ls\b|Get-ChildItem|\[事实\]|\[已验证\]|\[推断\])', re.I)
    for m in claim.finditer(content):
        ctx = content[max(0,m.start()-400):m.end()+200]
        if not evd.search(ctx):
            ln = content[:m.start()].count('\n')+1
            violations.append({"rule":"V6","loc":"L%d"%ln,"kind":"UNANCHORED_CLAIM","quote":m.group(0)[:100],"fix":"Verify with Test-Path/dir first, or tag as [推断]"})
            break
    return violations

def _v7_check(content: str, atype: str):
    """V7: Fabricated user directives (pseudo-constraints)."""
    violations = []
    fab = re.compile(r'(用户\s*(?:说|要求|明确|禁止|不允许|限制|不让|说过)\s*(?:我\s*)?(?:不要|不能|禁止|不允许|不|要|应该)\w+)', re.I)
    for m in fab.finditer(content):
        ln = content[:m.start()].count('\n')+1
        violations.append({"rule":"V7","loc":"L%d"%ln,"kind":"PSEUDO_CONSTRAINT","quote":m.group(0)[:100],"fix":"Tag as [内部约束] instead of attributing to user. Verify against actual user messages."})
        break
    # Also check for contamination template leaks
    for ct_id, pattern in [("CT-001","(禁止.*(?:搜索|联网)|不.*联网|纯.*推理)"),("CT-002","(因为.*限制|安全.*不能|不能.*讨论.*系统)")]:
        if re.search(pattern, content):
            for m in re.finditer(pattern, content):
                ctx = content[max(0,m.start()-200):m.end()+200]
                if not re.search(r'(原始规则|内部约束|system prompt|authentic)', ctx, re.I):
                    ln = content[:m.start()].count('\n')+1
                    violations.append({"rule":"V7","loc":"L%d"%ln,"kind":ct_id,"quote":m.group(0)[:100],"fix":"Likely discourse template contamination. Add LVC boundary markers. GET /vdp/vaccine"})
                    break
    return violations

SCAN_ENGINE = {
    "V1": _v1_check, "V2": _v2_check, "V3": _v3_check,
    "V4": _v4_check, "V5": _v5_check, "V6": _v6_check, "V7": _v7_check
}


# ═══════════ ENDPOINTS ═══════════

@app.get("/health")
def health():
    return {
        "status": "live",
        "version": "2.4",
        "tools": [
            "kb_query", "kb_search", "kb_status",
            "vdp_scan", "vdp_audit", "vdp_vaccine",
            "vdp_anchor", "vdp_precommit", "audit"
        ],
        "port": 53000,
        "features": ["context_aware_v7", "html_report", "layered_executor"],
    }

def _run_query(q: str):
    result = subprocess.run(
        ["python", KB_QUERY, q],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
    )
    return {"query":q,"results":(result.stdout or "").strip(),"stderr":(result.stderr or "").strip() or None,"exit_code":result.returncode}

@app.get("/query")
def query_get(q: str = ""):
    if not q.strip(): return {"error":"Empty query","results":[]}
    try: return _run_query(q)
    except subprocess.TimeoutExpired: return {"error":"Query timed out","results":[]}
    except Exception as e: return {"error":str(e),"results":[]}

@app.post("/query")
def query_post(req: QueryRequest):
    if not req.q.strip(): return {"error":"Empty query","results":[]}
    try: return _run_query(req.q)
    except subprocess.TimeoutExpired: return {"error":"Query timed out","results":[]}
    except Exception as e: return {"error":str(e),"results":[]}

# ── VDP Scan (inline, zero-I/O) ──
@app.post("/vdp/scan")
def vdp_scan(req: VDPScanRequest):
    """Hard-validation endpoint: scan raw artifact content against V1-V7 rules.
    Returns structured verdict + violations. No file I/O, no subprocess.
    """
    content = req.artifact
    if not content.strip():
        return {"verdict":"pass","violations":[],"stats":{"lines":0,"rules_checked":req.rules}}

    atype = req.artifact_type if req.artifact_type != "auto" else _detect_type(content)
    
    # JS/TS routing: use tree-sitter scanner
    if atype in ("javascript", "typescript", "js", "ts") or (
        atype == "auto" and (
            content.strip().startswith('import ') or 
            content.strip().startswith('const ') or
            content.strip().startswith('function ') or
            '=>' in content[:200]
        )
    ):
        try:
            import tempfile
            tf = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
            tf.write(content)
            tf.close()
            r = subprocess.run(
                [sys.executable, JS_SCAN, tf.name, "--json"],
                capture_output=True, text=True, timeout=30, encoding='utf-8'
            )
            os.unlink(tf.name)
            if r.returncode == 0 and r.stdout.strip():
                result = json.loads(r.stdout)
                return {
                    "verdict": result.get("verdict", "pass"),
                    "violations": result.get("violations", []),
                    "stats": {
                        "lines": len(content.split('\n')),
                        "rules_checked": req.rules or ["V1_PATH","V2_ERROR","V5_TIMEOUT","V8_LEAK","V9_ASYNC"],
                        "filetype": "javascript"
                    }
                }
        except Exception as e:
            pass  # Fall through to Python scanner
    
    violations = []

    for rule_id in req.rules or []:
        fn = SCAN_ENGINE.get(rule_id)
        if fn:
            violations.extend(fn(content, atype))

    # Mark severity - V3 is warn, others are reject
    for v in violations:
        v["severity"] = "warn" if v["rule"] == "V3" else "reject"

    # ── Lexical enhancement (optional, semantic=false keeps it off) ──
    lexical_violations = []
    if req.semantic and req.user_messages:
        try:
            lg = _get_lexical()
            lex_result = lg.scan(
                content,
                user_messages=req.user_messages,
                verified_facts=req.verified_facts or [],
                checks=["LV7_PSEUDO", "LV7_INDIRECT", "LV6_ABSTRACT", "LV6_ANCHOR"]
            )
            lexical_violations = lex_result.get("violations", [])
            violations.extend(lexical_violations)
        except Exception as e:
            pass  # Semantic check failure is non-fatal; fall through to symbolic-only

    has_reject = any(v["severity"] == "reject" for v in violations)

    return {
        "verdict": "reject" if has_reject else ("warn" if violations else "pass"),
        "violations": violations,
        "stats": {
            "lines": content.count('\n')+1,
            "type": atype,
            "rules_checked": req.rules or [],
            "violations_count": len(violations),
            "symbolic_count": len(violations) - len(lexical_violations),
            "lexical_count": len(lexical_violations),
            "semantic_enabled": req.semantic,
            "lexical_limitation": "TF-IDF measures word overlap, NOT meaning. Zero-overlap semantic equivalents invisible."
        }
    }

# ── VDP Audit (subprocess, file+transcript) ──
@app.post("/vdp/audit")
def vdp_audit(req: AuditRequest):
    results = {"verdict":"pass","violations":[],"vaccine":None,"stats":{}}
    violations = []

    if req.file and os.path.exists(req.file):
        try:
            r = subprocess.run(["python",VDP_SCAN,req.file,"--format","json"],
                capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
            if r.stdout:
                scan = json.loads(r.stdout)
                violations.extend(scan.get("violations",[]))
                results["stats"]["file_scan"] = {"target":scan.get("target"),"type":scan.get("target_type"),"lines":scan.get("stats",{}).get("total_lines",0)}
        except Exception as e: results["stats"]["file_scan_error"] = str(e)

    if req.transcript.strip():
        tf = os.path.join(os.environ.get("TEMP","/tmp"),"vdp_transcript_tmp.txt")
        try:
            with open(tf,"w",encoding="utf-8") as f: f.write(req.transcript)
            r = subprocess.run(["python",VDP_VACCINE,"--audit",tf,"--format","json"],
                capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
            if r.stdout: violations.extend(json.loads(r.stdout).get("violations",[]))
        except Exception as e: results["stats"]["vaccine_error"] = str(e)
        finally:
            if os.path.exists(tf):
                try: os.remove(tf)
                except: pass

    if violations:
        ct_ids = set(v.get("kind","") for v in violations if v.get("kind","").startswith("CT-"))
        if ct_ids: results["vaccine"] = {"triggered_templates":list(ct_ids),"recommendation":"Add LVC markers. GET /vdp/vaccine"}

    results["violations"] = violations
    has_reject = any(v.get("severity")=="reject" for v in violations)
    has_warn = any(v.get("severity")=="warn" for v in violations)
    results["verdict"] = "reject" if has_reject else ("warn" if has_warn else "pass")
    results["stats"]["violations_count"] = len(violations)
    return results

# ── VDP Vaccine (LVC markers) ──
@app.get("/vdp/vaccine")
def vdp_vaccine():
    try:
        r = subprocess.run(["python",VDP_VACCINE,"--inject"],
            capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=10)
        return {"status":"ok","markers":(r.stdout or "").strip(),"version":"1.0"}
    except Exception as e: return {"error":str(e)}

# ── KB Vector Search ──
_kb_index = None

def _get_kb_index():
    global _kb_index
    if _kb_index is None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mss-knowledge-navigator", "scripts"))
        from kb_vector import KBVectorIndex
        _kb_index = KBVectorIndex()
        status = _kb_index.load()
        if status.get("status") != "loaded":
            _kb_index.build()
    return _kb_index

@app.get("/kb/search")
def kb_search_get(q: str = "", k: int = 10):
    """GET /kb/search?q=热税公理&k=5 — vector search knowledge base"""
    if not q: return {"error":"Missing query parameter 'q'"}
    try:
        idx = _get_kb_index()
        return idx.search(q, k=k)
    except Exception as e: return {"error":str(e)}

@app.post("/kb/search")
def kb_search_post(req: KBSearchRequest):
    """POST /kb/search — vector search with full parameters"""
    if not req.q: return {"error":"Missing query"}
    try:
        idx = _get_kb_index()
        return idx.search(req.q, k=req.k, min_score=req.min_score)
    except Exception as e: return {"error":str(e)}

@app.get("/kb/status")
def kb_status():
    """GET /kb/status — index status"""
    try:
        idx = _get_kb_index()
        return idx.status()
    except Exception as e: return {"error":str(e)}


# ── VDP Anchor Guard ──
@app.post("/vdp/anchor")
def vdp_anchor_check(req: VDPScanRequest):
    """POST /vdp/anchor — validate output against reference info whitelist"""
    try:
        import tempfile, subprocess as sp
        ref_f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        out_f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        ref_f.write(req.verified_facts[0] if req.verified_facts else req.artifact[:2000])
        out_f.write(req.artifact)
        ref_f.close(); out_f.close()
        r = sp.run(["python",VDP_ANCHOR,"check","--ref",ref_f.name,"--output",out_f.name,"--json"],
            capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=15)
        os.unlink(ref_f.name); os.unlink(out_f.name)
        return json.loads(r.stdout) if r.stdout and r.stdout.strip() else {"error":"empty response"}
    except Exception as e: return {"error":str(e)}

# ── VDP Pre-Commit (static analysis) ──
@app.post("/vdp/precommit")
def vdp_precommit(req: VDPScanRequest):
    """POST /vdp/precommit — run pre-commit static checks on artifact"""
    try:
        r = subprocess.run(["python",VDP_PRECOMMIT,"check","--stdin"],
            input=req.artifact,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=15)
        return {"status":"ok","output":(r.stdout or "").strip(),"stderr":(r.stderr or "")}
    except Exception as e: return {"error":str(e)}

# ── Unified Audit (full VDP pipeline) ──
@app.post("/audit")
def unified_audit(req: VDPScanRequest):
    """POST /audit — run full VDP audit pipeline against LLM output"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "unified_audit",
            os.path.join(os.path.dirname(__file__), "mss-vdp", "unified_audit.py")
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        ref = req.verified_facts[0] if req.verified_facts else ""
        auditor = m.UnifiedAudit(ref, strictness=0.7)
        report = auditor.audit(req.artifact)
        # HTML format support
        if req.format == "html":
            rg_spec = importlib.util.spec_from_file_location(
                "report_generator",
                os.path.join(os.path.dirname(__file__), "mss-vdp", "report_generator.py")
            )
            rg = importlib.util.module_from_spec(rg_spec)
            rg_spec.loader.exec_module(rg)
            html = rg.generate_html(report, "MSS Audit Report")
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=html)

        return report
    except Exception as e:
        return {"error": str(e)}

# ── K3 Black Hole Monitor ──
class BHRequest(BaseModel):
    text: str = ""
    source: str = "api"

class JudgeRequest(BaseModel):
    domain_id: str = ""
    round_num: int = 1
    response: str = ""

@app.post("/vdp/blackhole")
def blackhole_scan(req: BHRequest):
    """POST /vdp/blackhole — detect K3 meaning black hole formation"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "k3_blackhole_monitor",
            os.path.join(os.path.dirname(__file__), "mss-vdp", "k3_blackhole_monitor.py")
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        detector = m.MeaningBlackHoleDetector()
        result = detector.analyze(req.text, source=req.source)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.post("/benchmark/judge")
def benchmark_judge(req: JudgeRequest):
    """LLM judge scoring for benchmark responses."""
    try:
        sys.path.insert(0, r'E:\QClaw-Data\workspace\engineering-problems\tests')
        from judge import judge
        result = judge(req.domain_id, req.round_num, req.response)
        return {"status": "ok", "score": result}
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}


@app.get("/benchmark/status")
async def benchmark_status():
    """Return latest benchmark scores."""
    try:
        import json, glob
        results_dir = r'E:\QClaw-Data\workspace\engineering-problems\tests\results'
        files = sorted(glob.glob(f'{results_dir}/auto_benchmark_*.json'), reverse=True)
        if not files:
            return {"status": "ok", "message": "No benchmark runs yet"}
        data = json.load(open(files[0], encoding='utf-8'))
        summary = {
            "date": files[0].split('_')[-1].replace('.json', ''),
            "rounds": sum(len(v['rounds']) for v in data.values()),
            "domains": {k: {"name": v['name'], "avg": v['average']} for k, v in data.items()},
            "overall": round(sum(v['average'] for v in data.values()) / len(data), 2)
        }
        return {"status": "ok", "data": summary}
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}


# ── PowerShell 矫正端点 ──

class PSPosixCheck(BaseModel):
    code: str
    auto_fix: bool = False

class PSPathPair(BaseModel):
    path_a: str
    path_b: str

@app.post("/vdp/ps_verify/detect")
def ps_detect_posix(req: PSPosixCheck):
    """Detect (and optionally fix) POSIX commands in PowerShell code."""
    try:
        sys.path.insert(0, os.path.dirname(PS_VERIFY))
        from ps_verify import detect_posix_commands, autocorrect
        violations = detect_posix_commands(req.code)
        result = {
            "status": "ok",
            "violations": violations,
            "count": len(violations),
        }
        if req.auto_fix and violations:
            corrected, corrections = autocorrect(req.code)
            result["corrected"] = corrected
            result["corrections"] = corrections
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}

@app.post("/vdp/ps_verify/projection")
def ps_verify_projection(req: PSPathPair):
    """Verify physical projection consistency between two paths."""
    try:
        sys.path.insert(0, os.path.dirname(PS_VERIFY))
        from ps_verify import PSProjectionVerifier
        v = PSProjectionVerifier()
        result = v.verify_pair(req.path_a, req.path_b)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}

@app.get("/vdp/ps_verify/rules")
def ps_get_rules():
    """Return the 5 iron rules as a prompt block."""
    try:
        sys.path.insert(0, os.path.dirname(PS_VERIFY))
        from ps_verify import MSS_PS_RULES_PROMPT
        return {"status": "ok", "rules": MSS_PS_RULES_PROMPT}
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}


# ── Multi-language Scanner Endpoints ──

class ScanRequest(BaseModel):
    code: str
    lang: str = "auto"  # auto|py|js|rust|java|cpp|go|ruby|php|kt|cs

SCANNER_ROUTES = {
    "py": ("python_script", VDP_SCAN, (".py"), "--format", "json"),
    "js": ("javascript", JS_SCAN, (".js"), "--json"),
    "rust": ("rust", RUST_SCAN, (".rs"), "--json"),
    "java": ("java", JAVA_SCAN, (".java"), "--json", "--java"),
    "cpp": ("c/c++", JAVA_SCAN, (".cpp"), "--json", "--cpp"),
    "go": ("go", GO_SCAN, (".go"), "--json"),
    "ruby": ("ruby", RUBY_SCAN, (".rb"), "--json"),
    "php": ("php", PHP_SCAN, (".php"), "--json"),
    "kt": ("kotlin", KOTLIN_SCAN, (".kt"), "--json"),
    "cs": ("csharp", CSHARP_SCAN, (".cs"), "--json"),
}

EXT_MAP = {
    ".py": "py", ".js": "js", ".ts": "js", ".jsx": "js",
    ".rs": "rust", ".java": "java", ".cpp": "cpp", ".c": "cpp", ".h": "cpp",
    ".go": "go", ".rb": "ruby", ".php": "php",
    ".kt": "kt", ".kts": "kt", ".cs": "cs",
}

def _run_scan(lang_key: str, code: str) -> dict:
    """Run scanner for a given language, return dict result."""
    if lang_key not in SCANNER_ROUTES:
        return {"verdict": "error", "violations": [], "stats": {"error": f"Unknown language: {lang_key}"}}
    
    lang_name, scanner_path, ext = SCANNER_ROUTES[lang_key][:3]
    args = list(SCANNER_ROUTES[lang_key][2:])
    
    # Write temp file
    tf = tempfile.NamedTemporaryFile(suffix=ext[0], mode='w', encoding='utf-8', delete=False)
    try:
        tf.write(code)
        tf.close()
        r = subprocess.run(
            [sys.executable, scanner_path, tf.name] + list(args),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20
        )
        data = json.loads(r.stdout) if r.stdout.strip() else {}
        items = [data] if isinstance(data, dict) else data
        all_violations = []
        for item in items:
            all_violations.extend(item.get('violations', []))
        
        has_reject = any(v.get('severity') == 'reject' for v in all_violations)
        return {
            "verdict": "reject" if has_reject else ("warn" if all_violations else "pass"),
            "violations": all_violations,
            "stats": {
                "lang": lang_name,
                "lang_key": lang_key,
                "lines": code.count('\n') + 1,
                "violations_count": len(all_violations),
            }
        }
    except Exception as e:
        return {"verdict": "error", "violations": [], "stats": {"error": str(e)[:200]}}
    finally:
        try: os.unlink(tf.name)
        except: pass

@app.post("/vdp/scan/all")
def vdp_scan_all(req: ScanRequest):
    """Run all 10 scanners against the code (auto-detect or forced)."""
    if req.lang != "auto" and req.lang in SCANNER_ROUTES:
        return {"results": {"all": _run_scan(req.lang, req.code)}}
    
    results = {}
    for lk in ["py", "js", "rust", "java", "cpp", "go", "ruby", "php", "kt", "cs"]:
        results[lk] = _run_scan(lk, req.code)
    
    total_v = sum(r["stats"].get("violations_count", 0) for r in results.values())
    any_reject = any(r["verdict"] == "reject" for r in results.values())
    return {
        "verdict": "reject" if any_reject else ("warn" if total_v > 0 else "pass"),
        "total_violations": total_v,
        "results": results,
    }

@app.post("/vdp/scan/py")
def vdp_scan_py(req: ScanRequest):
    return _run_scan("py", req.code)

@app.post("/vdp/scan/js")
def vdp_scan_js(req: ScanRequest):
    return _run_scan("js", req.code)

@app.post("/vdp/scan/rust")
def vdp_scan_rust(req: ScanRequest):
    return _run_scan("rust", req.code)

@app.post("/vdp/scan/java")
def vdp_scan_java(req: ScanRequest):
    return _run_scan("java", req.code)

@app.post("/vdp/scan/cpp")
def vdp_scan_cpp(req: ScanRequest):
    return _run_scan("cpp", req.code)

@app.post("/vdp/scan/go")
def vdp_scan_go(req: ScanRequest):
    return _run_scan("go", req.code)

@app.post("/vdp/scan/ruby")
def vdp_scan_ruby(req: ScanRequest):
    return _run_scan("ruby", req.code)

@app.post("/vdp/scan/php")
def vdp_scan_php(req: ScanRequest):
    return _run_scan("php", req.code)

@app.post("/vdp/scan/kotlin")
def vdp_scan_kotlin(req: ScanRequest):
    return _run_scan("kt", req.code)

@app.post("/vdp/scan/csharp")
def vdp_scan_csharp(req: ScanRequest):
    return _run_scan("cs", req.code)

@app.get("/vdp/scan/languages")
def vdp_scan_languages():
    """List all supported languages."""
    return {
        "languages": {k: v[0] for k, v in SCANNER_ROUTES.items()},
        "extensions": EXT_MAP,
        "total": len(SCANNER_ROUTES),
    }


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 53000
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")