#!/usr/bin/env python3
"""
MSS PowerShell Physical Projection Verifier
复用 SOLO 战役的 junction/投影检测逻辑, 适配 PowerShell 工作流。
"""
import sys, os, subprocess, json, re
from pathlib import Path
from datetime import datetime

# ── PS Command Templates (NO bash aliases, NO POSIX) ──

PS_VERIFY_PATH = '''
$targetPath = "{path}"
if (-not (Test-Path $targetPath)) {{ throw "MSS: Path not found: $targetPath" }}
$fileId = (fsutil file queryfileid $targetPath 2>&1 | Select-String "File ID").Line.Split(":")[1].Trim()
Write-Output "MSS: Physical projection OK: $targetPath -> FileID: $fileId"
$fileId
'''

PS_CHECK_JUNCTION = '''
$items = @(Get-ChildItem "{dir}" -Force -ErrorAction SilentlyContinue | Where-Object {{$_.Attributes -match "ReparsePoint"}})
if ($items.Count -gt 0) {{
    Write-Output "MSS: Found {0} reparse points" -f $items.Count
    $items | ForEach-Object {{ Write-Output "$($_.Name) -> $(Get-Item $_.FullName | Select-Object -ExpandProperty Target)" }}
}} else {{
    Write-Output "MSS: No reparse points found"
}}
'''

PS_CREATE_JUNCTION = '''
$source = "{source}"
$target = "{target}"
if (Test-Path $target) {{ Remove-Item $target -Force -Recurse -ErrorAction Stop }}
New-Item -ItemType Junction -Path $target -Target $source -Force
Write-Output "MSS: Junction created: $target -> $source"
'''

PS_CHECK_ACL = '''
Get-Acl "{path}" | Format-List Path, Owner, AccessToString
'''

PS_CHECK_SESSION = '''
Write-Output "MSS Session Context:"
Write-Output "  PWD: $(Get-Location)"
Write-Output "  PowerShell Version: $($PSVersionTable.PSVersion)"
Write-Output "  ExecutionPolicy: $(Get-ExecutionPolicy)"
Write-Output "  Elevated: $([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"
Write-Output "  Path entries (top 5):"
$env:Path.Split(';') | Select-Object -First 5 | ForEach-Object {{ Write-Output "    $_" }}
'''

PS_FRESH_SESSION = '''
Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command `"{command}`"" -Wait
'''

# ── Python-side verification ──

def ps_elevate_script(script_path: str) -> str:
    """Generate self-elevating PowerShell script wrapper."""
    return f'''
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {{
    Write-Output "MSS: Elevating..."
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}}
Write-Output "MSS: Running elevated"
& "{script_path}"
'''

# ── P0/P1 新增: PS 命令模板 ──

PS_VERSION_CHECK = '''
$v = $PSVersionTable.PSVersion
Write-Output "MSS: PSVersion=$($v.Major).$($v.Minor)  Edition=$($PSVersionTable.PSEdition)"
if ($v.Major -lt 5) {{ Write-Output "MSS:ERROR: PowerShell version too old ($($v.Major).$($v.Minor)), need 5.1+" ; exit 1 }}
Write-Output "MSS: Version OK"
$v.ToString()
'''

PS_CHECK_EXEC_POLICY = '''
$policy = Get-ExecutionPolicy -Scope Process
Write-Output "MSS: ExecutionPolicy(Process)=$policy"
if ($policy -eq "Restricted" -or $policy -eq "AllSigned") {{
    Write-Output "MSS:WARN: Execution policy $policy will block scripts. Use: powershell -ExecutionPolicy Bypass -File script.ps1"
}}
$policy
'''

PS_CHECK_GLOBAL_PARAMS = '''
if ($PSDefaultParameterValues.Count -gt 0) {{
    Write-Output "MSS:WARN: $($PSDefaultParameterValues.Count) global default parameters detected"
    $PSDefaultParameterValues.Keys | ForEach-Object {{ Write-Output "MSS:POLLUTED: $_ = $($PSDefaultParameterValues[$_])" }}
    $PSDefaultParameterValues.Clear()
    Write-Output "MSS:FIXED: Global default parameters cleared"
}} else {{
    Write-Output "MSS: Global parameter state clean"
}}
'''

PS_CHECK_MODULE_VERSIONS = '''
$conflicts = @()
Get-Module -ListAvailable | Group-Object Name | Where-Object {{ $_.Count -gt 1 }} | ForEach-Object {{
    $versions = ($_.Group | Sort-Object Version -Descending | Select-Object -First 3 | ForEach-Object {{ "$($_.Version)" }}) -join ', '
    Write-Output "MSS:WARN: Module '$($_.Name)' has $($_.Count) versions installed: $versions"
    $conflicts += $_.Name
}}
if ($conflicts.Count -eq 0) {{ Write-Output "MSS: No module version conflicts" }}
$conflicts.Count
'''

PS_INJECT_ERROR_HANDLING = '''
$ErrorActionPreference = "Stop"
trap {{ Write-Error "MSS: 未处理异常 at $($_.InvocationInfo.ScriptLineNumber): $_" ; exit 1 }}
'''

PS_CHECK_LONG_PATH = '''
$maxLen = 260
$path = "{path}"
if ($path.Length -gt $maxLen) {{
    Write-Output "MSS:WARN: Path length $($path.Length) exceeds Windows default limit ($maxLen)"
    Write-Output "MSS:FIX: Enable LongPathsEnabled via: New-ItemProperty -Path HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem -Name LongPathsEnabled -Value 1 -PropertyType DWord -Force"
}} else {{
    Write-Output "MSS: Path length OK ($($path.Length) chars)"
}}
'''

PS_CHECK_NETWORK_PATH = '''
$path = "{path}"
if ($path -match '^\\\\') {{
    Write-Output "MSS:INFO: Network share path detected — projection verification may be affected by network latency"
    try {{
        $exists = Test-Path $path
        Write-Output "MSS: Network path accessible: $exists"
    }} catch {{
        Write-Output "MSS:WARN: Network path unreachable: $_"
    }}
}} else {{
    Write-Output "MSS: Local path (no network share)"
}}
'''

PS_CHECK_PROFILE = '''
$profilePaths = @($PROFILE.AllUsersAllHosts, $PROFILE.AllUsersCurrentHost, $PROFILE.CurrentUserAllHosts, $PROFILE.CurrentUserCurrentHost)
$loaded = @()
foreach ($p in $profilePaths) {{
    if (Test-Path $p) {{
        $size = (Get-Item $p).Length
        $aliases = (Get-Content $p | Select-String "function |alias |Set-Alias").Count
        $loaded += "$p ($size bytes, $aliases custom definitions)"
    }}
}}
if ($loaded.Count -gt 0) {{
    Write-Output "MSS:WARN: $($loaded.Count) profile(s) loaded — may modify AI command behavior!"
    $loaded | ForEach-Object {{ Write-Output "MSS:PROFILE: $_" }}
    Write-Output "MSS:FIX: Run with -NoProfile to disable all user profiles"
}} else {{
    Write-Output "MSS: No profile pollution detected"
}}
'''

A7_PS_BOUNDARY = '''
⚠️  PowerShell 原生架构限制 (A7 不可解)
----------------------------------------------------------------------
1. 会话级伪沙盒 — 单进程内无法彻底隔离全局状态
2. PS 5.1 vs 7.x — 30%+ Cmdlet 行为不兼容
3. 网络共享路径 — 重解析点检测受网络环境影响
4. C# 二进制模块 — 无法彻底卸载，残留内存

✅ 唯一可靠方案: 每次运行都启动全新的 -NoProfile 独立进程
----------------------------------------------------------------------
'''


# ── P0: 版本兼容性检测 ──

def detect_ps_version() -> dict:
    r = subprocess.run(['powershell', '-NoProfile', '-Command', PS_VERSION_CHECK],
                      capture_output=True, text=True, timeout=10, encoding='utf-8')
    out = r.stdout
    m = re.search(r'PSVersion=(\d+)\.(\d+)', out)
    if m:
        major, minor = int(m.group(1)), int(m.group(2))
        edition = 'Core' if 'Core' in out else 'Desktop'
        return {
            'major': major, 'minor': minor, 'edition': edition, 'is_core': edition == 'Core',
            'warnings': ['-Depth: PS 5.1=2 default, PS 6+=1024 default', '&&/|| only in PS 7+'] if major < 6 else [],
        }
    return {'error': 'Cannot detect PS version', 'raw': out[:200]}

# ── P0: 执行策略检测 ──

def check_execution_policy() -> dict:
    r = subprocess.run(['powershell', '-NoProfile', '-Command', PS_CHECK_EXEC_POLICY],
                      capture_output=True, text=True, timeout=10, encoding='utf-8')
    m = re.search(r'ExecutionPolicy\(Process\)=(\w+)', r.stdout)
    policy = m.group(1) if m else 'Unknown'
    blocked = policy in ('Restricted', 'AllSigned')
    return {'policy': policy, 'blocked': blocked,
            'fix': 'powershell -NoProfile -ExecutionPolicy Bypass -File script.ps1' if blocked else None}

# ── P0: 全局参数污染检测 ──

def check_global_params() -> dict:
    r = subprocess.run(['powershell', '-NoProfile', '-Command', PS_CHECK_GLOBAL_PARAMS],
                      capture_output=True, text=True, timeout=10, encoding='utf-8')
    polluted = [l.split('=')[0].replace('MSS:POLLUTED:', '').strip()
                for l in r.stdout.split('\n') if 'POLLUTED' in l]
    return {'polluted_count': len(polluted), 'polluted_params': polluted,
            'cleaned': 'FIXED' in r.stdout}

# ── P1: 模块版本冲突检测 ──

def check_module_conflicts() -> dict:
    r = subprocess.run(['powershell', '-NoProfile', '-Command', PS_CHECK_MODULE_VERSIONS],
                      capture_output=True, text=True, timeout=15, encoding='utf-8')
    conflicts = []
    for line in r.stdout.split('\n'):
        m = re.search(r"Module '([^']+)' has (\d+) versions", line)
        if m:
            conflicts.append({'module': m.group(1), 'versions': int(m.group(2))})
    return {'conflicts': len(conflicts), 'modules': conflicts}

# ── P1: SC-009 强制错误处理 ──

def inject_error_handling(code: str) -> str:
    if '$ErrorActionPreference' in code[:200]:
        return code
    return PS_INJECT_ERROR_HANDLING + '\n' + code

def has_error_handling(code: str) -> bool:
    return any(k in code for k in ['$ErrorActionPreference', 'trap {', 'trap{', 'try {', 'try{'])

# ── P1: 长路径检测 ──

def check_long_path(path: str) -> dict:
    length = len(path)
    exceeds = length > 260
    return {'path': path, 'length': length, 'exceeds_default': exceeds,
            'fix': 'Enable LongPathsEnabled in registry (needs admin + reboot)' if exceeds else None}

# ── P2: 网络共享路径检测 ──

def is_network_path(path: str) -> bool:
    return path.startswith('\\\\') or path.startswith('//')

def check_network_path(path: str) -> dict:
    is_net = is_network_path(path)
    result = {'path': path, 'is_network': is_net, 'exists': None, 'warning': None}
    if is_net:
        result['exists'] = os.path.exists(path)
        result['warning'] = 'Network share path — projection verification may be affected by network latency' if not result['exists'] else None
    return result

# ── P2: $profile 污染检测 ──

def check_profile_pollution() -> dict:
    r = subprocess.run(['powershell', '-NoProfile', '-Command', PS_CHECK_PROFILE],
                      capture_output=True, text=True, timeout=10, encoding='utf-8')
    profiles = []
    for line in r.stdout.split('\n'):
        if 'MSS:PROFILE:' in line:
            profiles.append(line.replace('MSS:PROFILE:', '').strip())
    return {'profiles_loaded': len(profiles), 'profiles': profiles,
            'fix': 'Always use -NoProfile parameter for script execution' if profiles else None}

# ── P2: 结构化日志 ──

LOG_DIR = os.path.join(os.path.dirname(__file__), '.mss', 'logs')

def init_logger():
    os.makedirs(LOG_DIR, exist_ok=True)

def log_event(event_type: str, data: dict):
    init_logger()
    log_file = os.path.join(LOG_DIR, f'ps_verify_{datetime.now().strftime("%Y%m%d")}.jsonl')
    entry = {'timestamp': datetime.now().isoformat(), 'type': event_type, **data}
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return log_file

# ── P2: 综合安全检查 (8合1, 新增 profile + network) ──

def comprehensive_check() -> dict:
    results = {
        'timestamp': datetime.now().isoformat(),
        'ps_version': detect_ps_version(),
        'execution_policy': check_execution_policy(),
        'global_params': check_global_params(),
        'module_conflicts': check_module_conflicts(),
        'profile_pollution': check_profile_pollution(),
        'a7_boundary': A7_PS_BOUNDARY,
    }
    issues = []
    if results['execution_policy'].get('blocked'):
        issues.append('P0: Execution policy blocks scripts')
    if results['global_params'].get('polluted_count', 0) > 0:
        issues.append(f'P0: {results["global_params"]["polluted_count"]} global params polluted')
    if results['module_conflicts'].get('conflicts', 0) > 0:
        issues.append(f'P1: {results["module_conflicts"]["conflicts"]} modules have version conflicts')
    if results['profile_pollution'].get('profiles_loaded', 0) > 0:
        issues.append(f'P2: {results["profile_pollution"]["profiles_loaded"]} profile(s) may modify AI commands')
    results['verdict'] = 'reject' if issues else 'pass'
    results['issues'] = issues
    
    log_event('comprehensive_check', {'verdict': results['verdict'], 'issues': issues})
    return results

# ── 综合安全检查 (8合1, 新增 profile + network) ──


# ── 原有的投影验证器 ──


class PSProjectionVerifier:
    """PowerShell 物理投影验证器 — 复用 SOLO 方案"""
    
    def __init__(self):
        self.results = []
        self._projection_ok = True
    
    def verify_path(self, path: str) -> dict:
        """验证单个路径的物理投影. 返回 {exists, file_id, is_junction, target}"""
        result = {
            'path': path,
            'exists': os.path.exists(path),
            'file_id': None,
            'is_junction': False,
            'junction_target': None,
            'error': None,
        }
        
        if not result['exists']:
            result['error'] = 'PATH_NOT_FOUND'
            return result
        
        try:
            # Check if junction
            path_obj = Path(path)
            if sys.platform == 'win32':
                import ctypes
                FILE_ATTRIBUTE_REPARSE_POINT = 0x400
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                result['is_junction'] = bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
                
                if result['is_junction']:
                    # Get junction target
                    import _winapi
                    result['junction_target'] = os.readlink(path) if os.path.islink(path) else None
        except Exception as e:
            result['error'] = str(e)
        
        try:
            # Get file ID via fsutil (inode-like verification)
            r = subprocess.run(
                ['fsutil', 'file', 'queryfileid', path],
                capture_output=True, text=True, timeout=5, encoding='utf-8'
            )
            if r.returncode == 0:
                m = re.search(r'File ID is ([\w\d]+)', r.stdout)
                if m:
                    result['file_id'] = m.group(1)
        except Exception:
            pass
        
        return result
    
    def verify_pair(self, path_a: str, path_b: str) -> dict:
        """验证两个路径指向同一物理文件 (投影一致性检查)"""
        a = self.verify_path(path_a)
        b = self.verify_path(path_b)
        
        consistent = (a['file_id'] and b['file_id'] and a['file_id'] == b['file_id'])
        
        return {
            'path_a': a, 'path_b': b,
            'consistent': consistent,
            'verdict': 'pass' if consistent else 'PROJECTION_MISMATCH',
            'fix': f'Remove-Item "{path_a}" -Force; New-Item -ItemType Junction -Path "{path_a}" -Target "{path_b}" -Force'
                    if not consistent else None,
        }
    
    def scan_directory(self, directory: str) -> dict:
        """扫描目录下所有重解析点和投影断裂"""
        violations = []
        junc_points = []
        
        for root, dirs, files in os.walk(directory):
            for d in dirs:
                full = os.path.join(root, d)
                r = self.verify_path(full)
                if r['is_junction']:
                    junc_points.append(r)
                    if not r['exists']:
                        violations.append({
                            'rule_id': 'PS_BROKEN_JUNCTION',
                            'severity': 'reject',
                            'loc': full,
                            'kind': 'broken_junction',
                            'detail': f'Junction broken: {full} -> {r.get("junction_target", "?")}',
                        })
        
        return {
            'directory': directory,
            'junctions_found': len(junc_points),
            'violations': violations,
            'junctions': junc_points,
            'verdict': 'reject' if violations else 'pass',
        }


# ── POSIX Command Detector + Auto-Corrector ──

POSIX_TO_PS = {
    'ls': ('Get-ChildItem', ''),
    'dir': ('Get-ChildItem', ''),
    'rm ': ('Remove-Item ', '-Recurse -Force'),
    'del ': ('Remove-Item ', '-Force'),
    'cd ': ('Set-Location ', ''),
    'cat ': ('Get-Content ', ''),
    'type ': ('Get-Content ', ''),
    'echo ': ('Write-Output ', ''),
    'print ': ('Write-Output ', ''),
    'grep ': ('Where-Object ', ''),
    'findstr ': ('Where-Object ', ''),
    'mkdir ': ('New-Item -ItemType Directory ', ''),
    'cp ': ('Copy-Item ', ''),
    'copy ': ('Copy-Item ', ''),
    'mv ': ('Move-Item ', ''),
    'move ': ('Move-Item ', ''),
    'pwd': ('Get-Location', ''),
    'whoami': ('[System.Security.Principal.WindowsIdentity]::GetCurrent().Name', ''),
    'chmod': ('Set-Acl', ' # MSS: Use Set-Acl or icacls instead'),
    'chown': ('Set-Acl', ' # MSS: Use Set-Acl or icacls instead'),
    'kill ': ('Stop-Process -Name ', ''),
    'ps ': ('Get-Process ', ''),
    'curl ': ('Invoke-WebRequest -Uri ', ''),
    'wget ': ('Invoke-WebRequest -Uri ', ''),
    'touch ': ('New-Item -ItemType File ', ''),
    'tail ': ('Get-Content -Tail 10 ', ''),
    'head ': ('Get-Content -TotalCount 10 ', ''),
    'wc ': ('Measure-Object -Line -Word -Character ', ''),
    'sort ': ('Sort-Object ', ''),
    'uniq ': ('Get-Unique ', ''),
    'man ': ('Get-Help ', ''),
    'which ': ('Get-Command ', ''),
    'export ': ('Set-Variable -Name ', ' # MSS: Use Set-Variable or [Environment]::SetEnvironmentVariable'),
    'source ': ('. ', ' # MSS: Use dot-sourcing: . script.ps1'),
    'alias ': ('Get-Alias ', ''),
    'clear': ('Clear-Host', ''),
}

def detect_posix_commands(code: str) -> list:
    """检测 PowerShell 代码中的 POSIX 命令, 返回替换建议"""
    violations = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            continue
        
        for posix, (ps_cmd, extra) in POSIX_TO_PS.items():
            if stripped == posix or stripped.startswith(posix):
                violations.append({
                    'rule_id': 'SC-008',
                    'severity': 'warn',
                    'loc': f'L{i}',
                    'kind': 'posix_command',
                    'detail': f"POSIX command '{posix}' detected — replace with '{ps_cmd}{extra}'",
                    'original': stripped,
                    'fixed': f'{ps_cmd}{stripped[len(posix):]} {extra}'.strip(),
                })
                break
    
    return violations

def autocorrect(code: str) -> tuple:
    """自动矫正 PowerShell 代码中的 POSIX 命令.
    Returns (corrected_code, corrections_made)"""
    vs = detect_posix_commands(code)
    lines = code.split('\n')
    corrections = []
    
    for v in sorted(vs, key=lambda x: int(x['loc'][1:]), reverse=True):
        line_idx = int(v['loc'][1:]) - 1
        lines[line_idx] = v['fixed']
        corrections.append(f"{v['loc']}: {v['original'][:50]} -> {v['fixed'][:50]}")
    
    return '\n'.join(lines), corrections


# ── The 5 Iron Rules as Prompt Injection ──

MSS_PS_RULES_PROMPT = """
【MSS PowerShell 强制规则 — 5条铁律】
以下规则不可突破，违反任一条将导致命令被拦截:

1. 仅使用 PowerShell 原生 Cmdlet，禁止任何 Linux/macOS 命令
   ❌ 禁止: ls, rm, cd ~, grep, cat, wget, curl, chmod, chown
   ✅ 必须: Get-ChildItem, Remove-Item, Set-Location $HOME, Where-Object

2. 操作路径前必须执行物理投影验证
   ✅ 必须插入:
     $targetPath = "目标路径"
     if (-not (Test-Path $targetPath)) {{ throw "MSS: Path not found" }}
     fsutil file queryfileid $targetPath

3. 不使用临时会话变量，所有命令自包含、持久化
   ❌ 禁止: $env:Path += ";新路径" (仅当前会话)
   ✅ 必须: [Environment]::SetEnvironmentVariable("Path", ..., "Machine")

4. 不主动提权，优先排查路径投影问题
   ❌ 禁止: 直接 Start-Process -Verb RunAs
   ✅ 必须: 先 Get-Acl 检查权限 → fsutil 验证投影 → 最后才提权

5. 用对象管道过滤，禁止纯文本解析
   ❌ 禁止: Get-Process | findstr chrome
   ✅ 必须: Get-Process | Where-Object Name -eq "chrome"
"""

# ── CLI ──

def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS PowerShell Workflow Verifier & Corrector')
    sub = ap.add_subparsers(dest='cmd')
    
    p_scan = sub.add_parser('scan', help='Scan directory for physical projection issues')
    p_scan.add_argument('directory')
    p_scan.add_argument('--json', action='store_true')
    
    p_detect = sub.add_parser('detect', help='Detect POSIX commands in PowerShell code')
    p_detect.add_argument('file', help='PowerShell script to check')
    p_detect.add_argument('--fix', action='store_true', help='Auto-correct POSIX commands')
    p_detect.add_argument('--json', action='store_true')
    
    p_verify = sub.add_parser('verify', help='Verify physical projection for a path pair')
    p_verify.add_argument('path_a')
    p_verify.add_argument('path_b')
    
    p_rules = sub.add_parser('rules', help='Print the 5 iron rules prompt')
    
    p_check = sub.add_parser('check', help='P0+P1 六合一安全检查 (version/policy/params/modules)')
    p_check.add_argument('--json', action='store_true')
    
    p_version = sub.add_parser('version', help='检测 PowerShell 版本兼容性')
    p_version.add_argument('--json', action='store_true')
    
    p_error = sub.add_parser('error', help='SC-009 强制错误处理注入')
    p_error.add_argument('file', help='PowerShell script to inject error handling into')
    
    p_long = sub.add_parser('longpath', help='检测路径长度是否超过Windows 260字符限制')
    p_long.add_argument('path', help='Path to check')
    
    p_profile = sub.add_parser('profile', help='检测 $profile 配置污染')
    p_profile.add_argument('--json', action='store_true')
    
    p_net = sub.add_parser('netpath', help='检测网络共享路径投影')
    p_net.add_argument('path', help='Network path to check (e.g., \\server\share)')
    
    p_log = sub.add_parser('log', help='查看最近的 PowerShell 操作日志')
    p_log.add_argument('--last', type=int, default=10, help='最近N条记录')
    
    p_scan.add_argument('--recursive', action='store_true', help='Batch: recursively scan all subdirectories')
    
    args = ap.parse_args()
    
    if args.cmd == 'profile':
        r = check_profile_pollution()
        if args.json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        else:
            if r['profiles_loaded']:
                print(f"⚠️  {r['profiles_loaded']} profile(s) detected:")
                for p in r['profiles']:
                    print(f"     {p}")
                print(f"\nFix: {r['fix']}")
            else:
                print("✅  No profile pollution")
    
    elif args.cmd == 'netpath':
        r = check_network_path(args.path)
        print(f"Type: {'Network share' if r['is_network'] else 'Local path'}")
        print(f"Exists: {r['exists']}")
        if r.get('warning'):
            print(f"⚠️  {r['warning']}")
    
    elif args.cmd == 'log':
        init_logger()
        log_files = sorted(Path(LOG_DIR).glob('ps_verify_*.jsonl'), reverse=True)
        if not log_files:
            print("No logs found")
        else:
            with open(log_files[0], 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line in lines[-args.last:]:
                try:
                    entry = json.loads(line)
                    print(f"  [{entry['timestamp'][:19]}] {entry['type']:25s} {entry.get('verdict','')} {entry.get('file','')}")
                except:
                    print(f"  {line.strip()[:100]}")
            print(f"\nLog file: {log_files[0]} ({len(lines)} entries)")
    
    elif args.cmd == 'check':
        r = comprehensive_check()
        if args.json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        else:
            v = r['ps_version']
            print(f"PowerShell {v.get('major','?')}.{v.get('minor','?')} ({v.get('edition','?')})")
            print(f"Execution Policy: {r['execution_policy']['policy']} {'⚠️  BLOCKED' if r['execution_policy'].get('blocked') else '✅'}")
            print(f"Global Params: {r['global_params']['polluted_count']} polluted {'⚠️' if r['global_params']['polluted_count'] else '✅'}")
            print(f"Module Conflicts: {r['module_conflicts']['conflicts']} {'⚠️' if r['module_conflicts']['conflicts'] else '✅'}")
            print(f"Verdict: {r['verdict'].upper()}")
            if r['issues']:
                for i in r['issues']:
                    print(f"  ⚠️  {i}")
            if r['execution_policy'].get('fix'):
                print(f"\nFix: {r['execution_policy']['fix']}")
            print(r['a7_boundary'])
    
    elif args.cmd == 'version':
        r = detect_ps_version()
        if args.json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        else:
            if 'error' in r:
                print(f"Error: {r['error']}")
            else:
                print(f"PowerShell {r['major']}.{r['minor']} ({r['edition']})")
                for w in r.get('warnings', []):
                    print(f"  ⚠️  {w}")
    
    elif args.cmd == 'error':
        with open(args.file, 'r', encoding='utf-8') as f:
            code = f.read()
        if has_error_handling(code):
            print(f"Already has error handling: {args.file}")
        else:
            corrected = inject_error_handling(code)
            import shutil
            shutil.copy2(args.file, args.file + '.bak')
            with open(args.file, 'w', encoding='utf-8') as f:
                f.write(corrected)
            print(f"SC-009: Injected error handling into {args.file}")
            print(f"  Added: $ErrorActionPreference = 'Stop'")
            print(f"  Added: trap {{ ... ; exit 1 }}")
            print(f"  Backup: {args.file}.bak")
    
    elif args.cmd == 'longpath':
        r = check_long_path(args.path)
        print(f"Path length: {r['length']} chars (limit: 260)")
        if r['exceeds_default']:
            print(f"⚠️  EXCEEDS Windows default path limit!")
            print(f"Fix: {r['fix']}")
        else:
            print(f"✅  Within limit")
    
    elif args.cmd == 'scan':
        v = PSProjectionVerifier()
        r = v.scan_directory(args.directory)
        
        # Recursive scan all subdirectories if requested
        if getattr(args, 'recursive', False):
            for root, dirs, files in os.walk(args.directory):
                for d in list(dirs):
                    if d.startswith('.') or d in ('node_modules', '.git', '__pycache__'):
                        dirs.remove(d)
                sub_r = v.scan_directory(root)
                r['violations'].extend(sub_r['violations'])
                r['junctions_found'] += sub_r['junctions_found']
        
        if args.json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        else:
            print(f"Junctions found: {r['junctions_found']}")
            print(f"Violations: {len(r['violations'])}")
            for v in r['violations']:
                print(f"  [{v['severity']}] {v['loc']}: {v['detail']}")
    
    elif args.cmd == 'detect':
        with open(args.file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        vs = detect_posix_commands(code)
        
        if args.fix:
            corrected, corrections = autocorrect(code)
            bak = args.file + '.bak'
            import shutil
            shutil.copy2(args.file, bak)
            with open(args.file, 'w', encoding='utf-8') as f:
                f.write(corrected)
            print(f"Corrected {len(corrections)} POSIX commands:")
            for c in corrections:
                print(f"  {c}")
            print(f"Backup: {bak}")
            log_event('detect_fix', {'file': args.file, 'corrections': len(corrections), 'backup': bak})
        else:
            if args.json:
                print(json.dumps({'file': args.file, 'violations': vs}, indent=2, ensure_ascii=False))
            else:
                print(f"{len(vs)} POSIX command(s) detected in {args.file}:")
                for v in vs:
                    print(f"  [{v['severity']}] {v['loc']}: {v['detail']}")
                    print(f"    Original: {v['original'][:60]}")
                    print(f"    Fixed:    {v['fixed'][:60]}")
                if vs:
                    print(f"\nRun with --fix to auto-correct")
    
    elif args.cmd == 'verify':
        v = PSProjectionVerifier()
        r = v.verify_pair(args.path_a, args.path_b)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    
    elif args.cmd == 'rules':
        print(MSS_PS_RULES_PROMPT)
    
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
