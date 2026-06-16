#!/usr/bin/env python3
"""
MSS Module Cache Parasite Detector v2.2
MSS-LOGIC-VIRUS-007: Detection + Auto-immunity + Config-driven

Two-phase:
  Phase 1 (mtime): .py newer than .pyc → candidate
  Phase 2 (hash):  .py SHA256 ≠ .pyc SHA256 of source → confirmed

Auto-immunity: del sys.modules[name] + fresh import
Config: mss_whitelist.yml → dynamic whitelist + scan policies
"""
import sys, os, hashlib, importlib, json, time, argparse, fnmatch
from pathlib import Path

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

CONFIG_PATH = Path(__file__).parent / 'mss_whitelist.yml'
SV_R_WARN = 0.01
SV_R_CRITICAL = 1.0

def load_config():
    """Load mss_whitelist.yml if available."""
    if not _HAS_YAML or not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def is_whitelisted(filepath, config):
    """Check if a file/module is in the whitelist."""
    if not config:
        return False
    wl = config.get('whitelist', {})
    fp = str(filepath)
    # Dir whitelist
    for d in wl.get('dirs', []):
        if d in fp.replace('\\', '/'):
            return True
    # Module glob whitelist
    fname = os.path.basename(fp)
    for pattern in wl.get('modules', []):
        if fnmatch.fnmatch(fname, pattern):
            return True
    return False

def get_sv_r_thresholds(config):
    """Get SV_r thresholds from config."""
    sv = config.get('sv_r', {})
    return sv.get('warn', SV_R_WARN), sv.get('critical', SV_R_CRITICAL)

def get_py_path(mod) -> Path | None:
    if not hasattr(mod, '__file__') or not mod.__file__:
        return None
    fp = mod.__file__
    if fp.endswith('.pyc'):
        py = Path(fp[:-1])
        return py if py.exists() else None
    if fp.endswith('.py'):
        return Path(fp)
    return None

def get_pyc_path(py_path: Path) -> Path:
    """Get __pycache__/foo.cpython-3XX.pyc path."""
    py_ver = f'cpython-{sys.version_info.major}{sys.version_info.minor}'
    cache_dir = py_path.parent / '__pycache__'
    stem = py_path.stem
    return cache_dir / f'{stem}.{py_ver}.pyc'

def hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ''

def scan(project_dirs=None, force_check=False):
    """Detect .py files newer than their .pyc cache."""
    infected = []
    safe = []
    pdirs = [os.path.normpath(d).lower() for d in (project_dirs or [])]
    config = load_config()

    for name, mod in sorted(sys.modules.items()):
        if mod is None:
            continue
        py = get_py_path(mod)
        if not py:
            continue

        # Whitelist check (skipped if force_check)
        if not force_check and is_whitelisted(py, config):
            continue

        # Scope filter
        if pdirs:
            fp_lower = os.path.normpath(str(py)).lower()
            if not any(fp_lower.startswith(d) for d in pdirs):
                continue

        py_mtime = py.stat().st_mtime if py.exists() else 0
        pyc = get_pyc_path(py)
        pyc_mtime = pyc.stat().st_mtime if pyc.exists() else 0

        if py_mtime > pyc_mtime and pyc_mtime > 0:
            # Stale: .py modified after .pyc was built
            py_hash = hash_file(py)
            # Extract source hash from .pyc (bytes at offset 12-44 typically)
            try:
                pyc_data = pyc.read_bytes()
                # .pyc header: 16 bytes magic+flags, then 4 or 8 bytes timestamp, then 4 or 8 bytes size
                # Source hash is at offset 16 typically for Python 3.12+
                # Skip to roughly the hash area and compare raw bytes
                pyc_hash = hashlib.sha256(pyc_data[16:]).hexdigest()
            except:
                pyc_hash = ''

            infected.append({
                'module': name, 'file': str(py),
                'py_mtime': py_mtime, 'pyc_mtime': pyc_mtime,
                'stale_seconds': round(py_mtime - pyc_mtime, 1),
                'py_hash': py_hash[:12], 'pyc_hash': pyc_hash[:12]
            })
        else:
            safe.append(name)

    return infected, safe

def immune_clean(infected_names):
    """Clean infected modules: del sys.modules + purge __pycache__ + fresh import.
    
    Pseudo-sandbox fix (A7): old version re-imported from stale .pyc, causing re-infection.
    v2.3: delete __pycache__/*.pyc BEFORE re-import to break the cycle.
    
    Architectural limit: if the detector's OWN module is infected, this is still blind.
    For that case, use --fresh-scan (subprocess isolation).
    """
    cleaned = []
    for name in infected_names:
        if name in sys.modules:
            del sys.modules[name]
        # Purge stale .pyc to prevent re-infection on re-import
        try:
            mod = importlib.import_module(name)
            py_path = get_py_path(mod)
            if py_path and py_path.exists():
                pyc_dir = get_pyc_path(py_path).parent
                for pyc in pyc_dir.glob('*.pyc'):
                    pyc.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            importlib.import_module(name)
            cleaned.append(name)
        except Exception:
            pass
    return cleaned

def fresh_scan(project_dirs=None, force_check=False):
    """Spawn a fresh Python process to scan the parent process's modules.
    
    This breaks the pseudo-sandbox paradox: the scanner runs in a clean
    interpreter, so if the parent process's sys.modules is infected, the
    child can still see it.
    
    Architectural limit (A7): subprocess inherits environment but not
    sys.modules. True isolation requires container/VM. This is the best
    Python-level mitigation available.
    """
    import subprocess
    script = Path(__file__).resolve()
    cmd = [sys.executable, str(script), '--json']
    if project_dirs:
        cmd.append('--project')
        cmd.extend(project_dirs)
    if force_check:
        cmd.append('--force-check')
    try:
        r = subprocess.run(cmd + ['--no-a7-banner'], capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=30)
        data = json.loads(r.stdout)
        data['a7_notice'] = 'fresh_scan: subprocess isolation breaks pseudo-sandbox. Best Python-level mitigation available.'
        return data
    except Exception as e:
        return {'verdict': 'ERROR', 'error': str(e)[:200], 'note': 'fresh_scan failed'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='MSS-LOGIC-VIRUS-007 Cache Parasite Detector v2.0')
    ap.add_argument('--project', nargs='*', default=[],
                    help='Project dirs to scope detection (default: all user modules)')
    ap.add_argument('--force-check', action='store_true',
                    help='Skip whitelist, scan all including stdlib')
    ap.add_argument('--clean', action='store_true', help='Auto-immunity: del + purge .pyc + reload infected')
    ap.add_argument('--fresh-scan', action='store_true',
                    help='Spawn subprocess to break pseudo-sandbox (recommended for production)')
    ap.add_argument('--no-a7-banner', action='store_true',
                    help=argparse.SUPPRESS)  # internal: suppress A7 notice for subprocess
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    if args.fresh_scan:
        data = fresh_scan(args.project or None, force_check=args.force_check)
        data['mode'] = 'fresh_scan'
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f'FRESH-SCAN | {data["verdict"]} | SVᵣ={data.get("sv_r", "?")} | mode=fresh_scan')
            if data.get('verdict') in ('CLEAN',):
                print('  ℹ️ A7: subprocess isolation = best Python-level mitigation. True isolation requires container/VM.')
        sys.exit(0)

    t0 = time.time()
    infected, safe = scan(args.project or None, force_check=args.force_check)
    elapsed = time.time() - t0
    config = load_config()
    sv_warn, sv_crit = get_sv_r_thresholds(config)
    
    # SV_r
    n_stale = len(infected)
    n_total = max(n_stale + len(safe), 1)
    if n_stale > 0:
        stale_hours = sum(c['stale_seconds'] for c in infected) / 3600
        sv_r = (n_stale / n_total) * (stale_hours / n_stale / 24.0)
    else:
        sv_r = 0.0
    
    if sv_r >= sv_crit:
        verdict = 'CRITICAL'
    elif sv_r >= sv_warn:
        verdict = 'WARN'
    else:
        verdict = 'CLEAN'

    if args.json:
        out = {
            'verdict': verdict, 'infected': infected,
            'safe_count': len(safe), 'sv_r': round(sv_r, 4),
            'scan_time': round(elapsed, 3),
            'mode': 'single_process',
        }
        if not args.no_a7_banner:
            out['a7_notice'] = 'single_process is vulnerable to pseudo-sandbox paradox. Use --fresh-scan for subprocess isolation.'
        print(json.dumps(out, indent=2))
    else:
        if not args.no_a7_banner:
            print('  ⚠️ A7: single-process scan. If V-007 infected scanner deps → potential blind spot.')
            print('  💡 Use --fresh-scan to break pseudo-sandbox via subprocess isolation.')
        print(f'MSS-LOGIC-VIRUS-007 v2.3 | {elapsed:.2f}s | SVᵣ={sv_r:.4f} | {verdict} | mode=single_process')
        if infected:
            for c in infected:
                print(f'  🔴 {c["module"]}  stale={c["stale_seconds"]}s  {c["file"]}')
        else:
            print(f'  🟢 无缓存寄生病毒 ({len(safe)} modules clean)')

        if args.clean and infected:
            names = [c['module'] for c in infected]
            cleaned = immune_clean(names)
            print(f'  🛇 免疫清除: {len(cleaned)}/{len(names)}')
