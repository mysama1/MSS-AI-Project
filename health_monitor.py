"""
全局健康监控 — D2黑洞预警 + Git状态 + 任务栏 + 进程存活
===========================================================
用法:
    python health_monitor.py              # 单次扫描
    python health_monitor.py --serve      # 启动HTTP服务 (端口53001)
    python health_monitor.py --poll 300   # 每300秒轮询一次
"""
import sys, os, json, time, subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(PROJECT_ROOT, ".health_monitor_state.json")

# ─── Health Check Functions ───

def check_d2_blackhole():
    """自检: 扫描项目README和核心代码的黑洞信号."""
    signals = {
        'narrative_inflation': ['重新定义行业', '万亿市场', '指数级增长', '下一个', '革命性'],
        'too_big_to_mean': ['无所不能', '终极', '完美解决', '彻底改变'],
        'growth_paradox': ['每年翻倍', '估值千亿', '不计成本', '烧钱'],
        'free_lunch': ['免费替代', '零成本部署', '自动生成一切'],
        'complexity_explosion': ['过度工程化', '不必要的抽象', '为了技术而技术'],
        'value_decoupling': ['AI裁员', '被取代', '不再需要人类', '自动淘汰'],
        'trust_dissolution': ['幻觉率', '不可靠输出', '编造事实', '虚假信息'],
        'meaning_flattening': ['一切皆可量化', '纯效率驱动', '唯一指标'],
        'circular_dependency': ['自我指涉', '循环论证', '无法证伪'],
    }
    # Documents that ANALYZE/DOCUMENT blackholes (not exhibiting them) get 0.3x weight
    analyzing_patterns = ['黑洞', 'blackhole', '热税', 'heat_tax', '意义场', 'meaning_field', '诊断', 'diagnos']
    
    targets = ['README.md', 'docs/MEANING_ENGINEERING_WHITEPAPER_v1.0.md',
               'mssclaw/core/agent.py', 'mssclaw/core/heat_tax.py']
    
    total_score = 0
    hits_detail = {}
    for fname in targets:
        fpath = os.path.join(PROJECT_ROOT, fname)
        if not os.path.exists(fpath): continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
        except: continue
        words = len(content.split())
        # Check if this document is analyzing blackholes (not exhibiting them)
        is_analyzing = any(pat in fname.lower() or pat in content[:500].lower() for pat in analyzing_patterns)
        weight = 0.3 if is_analyzing else 1.0
        fhits = {}
        for sig, keywords in signals.items():
            matched = [kw for kw in keywords if kw in content]
            if matched:
                fhits[sig] = matched
                total_score += len(matched) * 0.5 * weight
        if fhits:
            hits_detail[fname] = {'words': words, 'hits': fhits}
    
    return {
        'crtr': round(min(total_score, 15), 2),
        'threat': 'safe' if total_score < 3 else ('warning' if total_score < 6 else 'critical'),
        'files_scanned': len(targets),
        'hits': hits_detail
    }

def check_git():
    """Git状态: 未推送提交 + 未提交变更."""
    try:
        r = subprocess.run(['git', 'log', 'origin/main..HEAD', '--oneline'],
                          capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=5,
                          encoding='utf-8', errors='replace')
        unpushed = [l for l in (r.stdout or '').strip().split('\n') if l]
        r2 = subprocess.run(['git', 'status', '--porcelain'],
                           capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=5,
                           encoding='utf-8', errors='replace')
        dirty = [l for l in (r2.stdout or '').strip().split('\n') if l]
        r3 = subprocess.run(['git', 'log', '-1', '--format=%h %s'],
                           capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=5,
                           encoding='utf-8', errors='replace')
        return {
            'last_commit': (r3.stdout or '').strip(),
            'unpushed': len(unpushed),
            'dirty_files': len(dirty),
            'status': 'dirty' if dirty else ('ahead' if unpushed else 'clean')
        }
    except Exception as e:
        return {'error': str(e), 'status': 'unknown'}

def check_processes():
    """关键进程存活检查."""
    targets = {
        'skill_api': 'python.*skill_api',
        'ollama': 'ollama',
        'openclaw_gateway': 'openclaw.*gateway',
    }
    results = {}
    for name, pattern in targets.items():
        try:
            r = subprocess.run(['powershell', '-Command',
                f"Get-Process | Where-Object {{$_.ProcessName -match '{pattern}'}} | Measure-Object | Select-Object -ExpandProperty Count"],
                capture_output=True, text=True, timeout=5)
            results[name] = int(r.stdout.strip() or 0) > 0
        except:
            results[name] = None
    return results

def check_taskbar():
    """任务栏状态摘要."""
    task_paths = [
        os.path.join(PROJECT_ROOT, 'task_bar_sprint152.md'),
        'E:\\QClaw-Data\\workspace\\task_bar_sprint151.md',
    ]
    for tp in task_paths:
        if os.path.exists(tp):
            with open(tp, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                'file': os.path.basename(tp),
                'size': len(content),
                'lines': content.count('\n')
            }
    return {'file': None, 'status': 'not found'}

def full_scan():
    """执行全项健康扫描."""
    return {
        'timestamp': datetime.now().isoformat(),
        'blackhole': check_d2_blackhole(),
        'git': check_git(),
        'processes': check_processes(),
        'taskbar': check_taskbar(),
    }

# ─── HTTP Server ───

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            data = full_scan()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
        elif self.path == '/dashboard':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<title>MSS 全局健康监控</title>
<style>
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#c9d1d9;padding:24px;max-width:900px;margin:0 auto}
h1{color:#58a6ff;font-size:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin:12px 0}
.card h2{color:#f0f6fc;font-size:15px;margin:0 0 10px}
.status-ok{color:#3fb950} .status-warn{color:#d29922} .status-bad{color:#f85149}
.metric{display:inline-block;margin:4px 12px;font-size:14px}
.metric .val{font-size:24px;font-weight:700}
.grid{display:flex;gap:12px;flex-wrap:wrap}
.grid .card{flex:1;min-width:180px}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
.live{animation:pulse 2s infinite}
</style>
</head>
<body>
<h1>🔍 MSS 全局健康监控 <span class="live" style="font-size:12px;color:#3fb950">● LIVE</span></h1>
<div id="content">加载中...</div>
<script>
async function refresh(){try{const r=await fetch('/health');const d=await r.json();
let h='';
h+=`<div class="grid">
<div class="card"><h2>🌌 黑洞预警</h2>
<div class="metric"><span class="val ${d.blackhole.threat=='safe'?'status-ok':'status-bad'}">${d.blackhole.crtr}</span> CRTR</div>
<div class="metric">${d.blackhole.threat=='safe'?'✅ 安全':'❌ 告警'}</div>
<div class="metric" style="font-size:12px">${d.blackhole.files_scanned}文件已扫</div></div>
<div class="card"><h2>📦 Git</h2>
<div class="metric">${d.git.status=='clean'?'<span class="status-ok">✅ 干净</span>':d.git.status=='ahead'?'<span class="status-warn">⚠️ 待推送</span>':'<span class="status-bad">❌ 脏</span>'}</div>
<div class="metric" style="font-size:12px">${d.git.last_commit||''}</div></div>
<div class="card"><h2>⚙️ 进程</h2>`;
for(const [k,v] of Object.entries(d.processes)) h+=`<div class="metric" style="font-size:13px">${k}: ${v===true?'<span class="status-ok">●</span>':'<span class="status-bad">○</span>'}</div>`;
h+=`</div></div>
<div class="card"><h2>📋 任务栏</h2><div class="metric">${d.taskbar.file||'未找到'} (${d.taskbar.lines||0}行)</div></div>
<div style="text-align:center;color:#484f58;font-size:11px;margin-top:16px">🔄 ${d.timestamp} | 每30秒自动刷新</div>`;
document.getElementById('content').innerHTML=h;}catch(e){document.getElementById('content').innerHTML='<div class="card"><span class="status-bad">❌ 扫描失败: '+e.message+'</span></div>';}}
refresh();setInterval(refresh,30000);
</script>
</body>
</html>"""

# ─── CLI ───

if __name__ == '__main__':
    if '--serve' in sys.argv:
        port = 53001
        for i, a in enumerate(sys.argv):
            if a == '--port' and i+1 < len(sys.argv):
                port = int(sys.argv[i+1])
        server = HTTPServer(('127.0.0.1', port), HealthHandler)
        print(f'🔍 MSS Health Monitor running on http://127.0.0.1:{port}')
        print(f'   /health    → JSON')
        print(f'   /dashboard → HTML')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\nShutting down...')
            server.server_close()
    elif '--poll' in sys.argv:
        interval = 300
        for i, a in enumerate(sys.argv):
            if a == '--poll' and i+1 < len(sys.argv):
                interval = int(sys.argv[i+1])
        print(f'Polling every {interval}s...')
        while True:
            data = full_scan()
            print(f"\n[{data['timestamp']}]")
            print(f"  CRTR={data['blackhole']['crtr']} | Git={data['git']['status']} | "
                  f"skill_api={'UP' if data['processes'].get('skill_api') else 'DOWN'} | "
                  f"ollama={'UP' if data['processes'].get('ollama') else 'DOWN'}")
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            time.sleep(interval)
    else:
        data = full_scan()
        print(json.dumps(data, ensure_ascii=False, indent=2))
