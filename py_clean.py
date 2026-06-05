#!/usr/bin/env python3
"""
MSS Python 环境诊断与净化器
覆盖: venv污染 / pip缓存 / .pyc幽灵 / 多版本投影 / PyInstaller碎裂
"""
import subprocess, sys, os, json, re, shutil
from pathlib import Path
from datetime import datetime

def safe_run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return '', str(e), -1

class PyDiagnostic:
    """Python现场取证——不碰文件，只报告"""
    
    def __init__(self):
        self.findings = []
    
    def run_all(self) -> dict:
        findings = (
            self._check_venv() +
            self._check_pycache() + 
            self._check_pip_cache() +
            self._check_multi_version() +
            self._check_sys_modules()
        )
        self.findings = findings
        return {
            'timestamp': datetime.now().isoformat(),
            'findings': findings,
            'summary': self._summarize()
        }
    
    # ── V1: venv 污染检测 ──
    def _check_venv(self):
        findings = []
        for marker in ['.venv', 'venv', 'env', '.env']:
            p = Path(marker)
            if p.is_dir():
                py = p / 'Scripts' / 'python.exe'
                if py.exists():
                    out, _, _ = safe_run([str(py), '-c', 'import sys;print(sys.executable)'])
                    findings.append({
                        'check': 'venv_exists', 'status': 'ok',
                        'path': str(p.resolve()),
                        'executable': out
                    })
        
        # Check if we're inside a venv
        if hasattr(sys, 'real_prefix') or sys.base_prefix != sys.prefix:
            findings.append({
                'check': 'active_venv', 'status': 'active',
                'prefix': sys.prefix,
                'detail': '当前在venv内运行——这是正常的隔离状态'
            })
        return findings
    
    # ── V2: __pycache__ 幽灵检测 ──
    def _check_pycache(self):
        pc_count = 0
        total_mb = 0
        recent = None
        for root, dirs, files in os.walk('.'):
            if '__pycache__' in dirs:
                pc_dir = os.path.join(root, '__pycache__')
                for f in os.listdir(pc_dir):
                    fp = os.path.join(pc_dir, f)
                    sz = os.path.getsize(fp)
                    pc_count += 1
                    total_mb += sz
                    if f.endswith('.pyc'):
                        mtime = os.path.getmtime(fp)
                        if recent is None or mtime > recent:
                            recent = mtime
        
        return [{
            'check': 'pycache_count', 'status': 'ok' if pc_count < 50 else 'warn',
            'count': pc_count, 'size_mb': round(total_mb / 1048576, 2),
            'suggestion': 'py -3.11 -B -c "import py_compile"' if pc_count > 500 else None
        }]
    
    # ── V3: pip 全局缓存 ──
    def _check_pip_cache(self):
        out, _, _ = safe_run([sys.executable, '-m', 'pip', 'cache', 'info'])
        if out:
            m = re.search(r'(\d+)\s+files', out)
            files = int(m.group(1)) if m else 0
            return [{
                'check': 'pip_cache', 'status': 'ok' if files < 200 else 'warn',
                'files': files,
                'detail': f'pip缓存中有 {files} 个文件——可能导致依赖版本投影不准确',
                'clean_cmd': f'{sys.executable} -m pip cache purge'
            }]
        return []
    
    # ── V4: 多版本投影混乱 ──
    def _check_multi_version(self):
        out, _, _ = safe_run(['py', '-0p'])
        interpreters = [l.strip() for l in out.split('\n') if l.strip() and 'python' in l.lower()]
        
        findings = []
        for intr in interpreters:
            # Extract path from " -V:3.11  C:\Python311\python.exe"
            m = re.search(r'([A-Z]:[^\s]+python\S*)', intr)
            if m:
                path = m.group(1)
                if os.path.exists(path):
                    out2, _, _ = safe_run([path, '-c', 'import sys;print(sys.version)'])
                    findings.append({
                        'interpreter': path,
                        'version': out2.split('\n')[0] if out2 else '?',
                        'file_id': self._get_file_id(path)
                    })
        
        return [{
            'check': 'multi_python',
            'status': 'ok' if len(findings) <= 2 else 'warn',
            'interpreters': len(findings),
            'list': findings,
            'suggestion': '用 py -0p 列出全部，用 fsutil 校验每个的物理 inode'
        }]
    
    # ── V5: sys.modules 快照 ──
    def _check_sys_modules(self):
        key_mods = [m for m in sys.modules if any(k in m for k in ['numpy', 'torch', 'tensorflow', 'pandas', 'mss'])]
        return [{
            'check': 'loaded_modules', 'status': 'info',
            'count': len(key_mods),
            'modules': key_mods[:10],
            'detail': '这些模块已加载。如果出现"改了不生效"，检查这些模块是否被缓存污染'
        }]
    
    def _get_file_id(self, path):
        try:
            r = subprocess.run(['fsutil', 'file', 'queryfileid', path],
                             capture_output=True, text=True, timeout=5)
            m = re.search(r'File ID is ([\w\d]+)', r.stdout)
            return m.group(1) if m else '?'
        except:
            return '?'
    
    def _summarize(self):
        warns = sum(1 for f in self.findings if f.get('status') in ('warn', 'reject'))
        return f'{len(self.findings)} checks, {warns} warnings'


class PyCleaner:
    """Python 环境净化器——铁律3: 全量自包含，拒绝伪沙盒"""
    
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.cleaned = []
    
    def clean_pycache(self, directory='.'):
        count = 0
        for root, dirs, files in os.walk(directory):
            if '__pycache__' in dirs:
                pc = os.path.join(root, '__pycache__')
                if not self.dry_run:
                    shutil.rmtree(pc, ignore_errors=True)
                count += 1
                self.cleaned.append(pc)
        return count
    
    def clean_pip_cache(self):
        if self.dry_run:
            return 'DRY_RUN: pip cache purge'
        out, _, rc = safe_run([sys.executable, '-m', 'pip', 'cache', 'purge'])
        return out
    
    def clean_pyc_files(self, directory='.'):
        count = 0
        for root, dirs, files in os.walk(directory):
            for f in files:
                if f.endswith('.pyc') or f.endswith('.pyo'):
                    fp = os.path.join(root, f)
                    if not self.dry_run:
                        os.remove(fp)
                    count += 1
                    self.cleaned.append(fp)
        return count
    
    def report(self):
        return {
            'dry_run': self.dry_run,
            'cleaned_count': len(self.cleaned),
            'items': self.cleaned[:20]
        }


# ── CLI ──
def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS Python 环境诊断与净化')
    sub = ap.add_subparsers(dest='cmd')
    
    p_diag = sub.add_parser('diagnose', help='诊断Python环境问题（只读）')
    p_diag.add_argument('directory', nargs='?', default='.', help='目标目录')
    p_diag.add_argument('--json', action='store_true')
    
    p_clean = sub.add_parser('clean', help='净化Python环境')
    p_clean.add_argument('directory', nargs='?', default='.', help='目标目录')
    p_clean.add_argument('--no-dry-run', action='store_true', help='真正执行（不模拟）')
    p_clean.add_argument('--pip', action='store_true', help='同时清pip缓存')
    
    p_rules = sub.add_parser('rules', help='输出Python自动化规则')
    
    args = ap.parse_args()
    
    if args.cmd == 'diagnose':
        os.chdir(args.directory)
        d = PyDiagnostic()
        r = d.run_all()
        if args.json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        else:
            print(f"Python 环境诊断: {r['summary']}")
            for f in r['findings']:
                icon = '✅' if f['status'] == 'ok' else '⚠️' if f['status'] == 'warn' else '📋'
                print(f"  {icon} {f['check']:20s} {f.get('detail', '')[:80]}")
                if 'suggestion' in f and f['suggestion']:
                    print(f"       → {f['suggestion'][:80]}")
                if 'clean_cmd' in f:
                    print(f"       → 清理命令: {f['clean_cmd']}")
    
    elif args.cmd == 'clean':
        c = PyCleaner(dry_run=not args.no_dry_run)
        n_pycache = c.clean_pycache(args.directory)
        n_pyc = c.clean_pyc_files(args.directory)
        if args.pip:
            pip_result = c.clean_pip_cache()
        else:
            pip_result = '(跳过 — 用 --pip 开启)'
        
        mode = 'DRY RUN (模拟)' if c.dry_run else 'EXECUTED (已执行)'
        print(f"Python 环境净化 [{mode}]")
        print(f"  __pycache__ 目录: {n_pycache} 个")
        print(f"  .pyc/.pyo 文件: {n_pyc} 个")
        print(f"  pip 缓存: {pip_result}")
        if c.dry_run:
            print(f"\n  用 --no-dry-run 真正执行清理")
    
    elif args.cmd == 'rules':
        print("""【MSS Python 工具自动化规则】
1. 环境污染 → 自动诊断: py -3.11 py_clean.py diagnose
2. 幽灵.pyc → 自动清理: py -3.11 py_clean.py clean --no-dry-run
3. pip缓存 → 全量清除: py -3.11 -m pip cache purge
4. 多版本 → 列出版本: py -0p | 校验每个inode
5. 打包异常 → 搜索: PyInstaller extract fileid checksum
6. C扩展缓存 → 终极方案: \033[31m重启进程 (sys.modules无法运行时清空)\033[0m""")
    
    else:
        ap.print_help()

if __name__ == '__main__':
    main()
