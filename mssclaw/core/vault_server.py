"""
Vault HTTP Server — 本地凭证微服务

用法:
    mss-vault serve                    # 启动 (默认 127.0.0.1:5099)
    mss-vault serve --port 8080       # 自定义端口
    mss-vault serve --no-auth          # 无密码模式 (仅本地回路)

API:
    GET  /health                       # 健康检查
    GET  /get/<key>                    # 获取凭证
    GET  /list[/<category>]            # 列出凭证
    GET  /search/<query>               # 搜索
    POST /unlock  {password: "..."}    # 解锁
    POST /lock                         # 锁定
    GET  /stats                        # 统计面板

安全:
  - 仅监听 127.0.0.1 (不可远程访问)
  - 需先 /unlock 才能访问数据
  - 不记录请求日志中的密码明文
"""
import json
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading


class VaultAPIHandler(BaseHTTPRequestHandler):
    vault = None
    auth_required = True

    def log_message(self, format, *args):
        # Suppress default logging (no password leaks in logs)
        pass

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _error(self, msg, status=400):
        self._json({"error": msg}, status)

    def _check_unlocked(self):
        if not self.vault or self.vault.is_locked:
            self._error("vault locked", 401)
            return False
        return True

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")

        if path == "" or path == "/":
            return self._serve_dashboard()

        if path == "/health":
            return self._json({"status": "ok", "locked": self.vault.is_locked if self.vault else True})

        if not self._check_unlocked():
            return

        if path.startswith("/get/"):
            key = path.split("/get/", 1)[1]
            val = self.vault.get(key)
            if val is None:
                return self._error(f"not found: {key}", 404)
            return self._json({"key": key, "value": val})

        if path == "/list" or path.startswith("/list/"):
            cat = path.split("/list/", 1)[1] if "/list/" in path else None
            qs = parse_qs(urlparse(self.path).query)
            query = qs.get("q", [None])[0]
            keys = self.vault.list_keys(category=cat, query=query)
            return self._json({"count": len(keys), "entries": keys})

        if path.startswith("/search/"):
            query = path.split("/search/", 1)[1]
            keys = self.vault.list_keys(query=query)
            return self._json({"query": query, "count": len(keys), "entries": keys})

        if path == "/stats":
            from mssclaw.core.vault_stats import VaultStats
            from mssclaw.core.vault_health import VaultHealth
            stats = VaultStats.analyze(self.vault)
            health = VaultHealth.check(self.vault)
            return self._json({"stats": stats, "health": health})

        self._error("not found", 404)

    def _serve_dashboard(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(DASHBOARD.encode())

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len)) if content_len > 0 else {}

        path = urlparse(self.path).path.rstrip("/")

        if path == "/unlock":
            pw = body.get("password", "")
            if not pw:
                return self._error("password required")
            if self.vault.unlock(pw):
                return self._json({"status": "unlocked"})
            return self._error("wrong password", 403)

        if path == "/lock":
            self.vault.lock()
            return self._json({"status": "locked"})

        self._error("not found", 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def serve_vault(port: int = 5099, auth_required: bool = True):
    """启动保险箱 HTTP 服务."""
    from mssclaw.core.credential_vault import CredentialVault

    vault_path = Path.home() / ".mssclaw" / "vault.db"
    v = CredentialVault(str(vault_path))
    v.AUTO_LOCK_SECONDS = 9999

    VaultAPIHandler.vault = v
    VaultAPIHandler.auth_required = auth_required

    server = HTTPServer(("127.0.0.1", port), VaultAPIHandler)
    print(f"🔐 Vault API: http://127.0.0.1:{port}")
    print(f"   curl http://127.0.0.1:{port}/health")
    print(f"   curl -X POST http://127.0.0.1:{port}/unlock -d '{{\"password\":\"...\"}}'")
    print(f"   curl http://127.0.0.1:{port}/get/github_token")
    print(f"   curl http://127.0.0.1:{port}/search/github")
    print()
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        v.close()
        server.shutdown()


def cmd_serve(port: int = 5099, no_auth: bool = False):
    serve_vault(port=port, auth_required=not no_auth)


# ═══════════════════════════════════════════
# Web Dashboard (single-page app, no deps)
# ═══════════════════════════════════════════

DASHBOARD = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔐 MSS Vault</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0d1117;color:#c9d1d9;padding:16px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px}
.metric{text-align:center;padding:12px}
.metric .v{font-size:2em;font-weight:bold}
.metric .l{font-size:.75em;color:#8b949e;margin-top:4px}
.grade{display:inline-block;padding:2px 10px;border-radius:4px;font-weight:bold}
.A{background:#238636;color:#fff}.B{background:#1f6feb;color:#fff}.C{background:#d29922;color:#000}.D,.F{background:#da3633;color:#fff}
input,button{padding:8px 12px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9;font-size:14px}
button{background:#238636;border:none;cursor:pointer;margin-left:8px}
button:hover{opacity:.9}
table{width:100%;border-collapse:collapse;margin-top:12px}
th,td{padding:8px;text-align:left;border-bottom:1px solid #30363d;font-size:13px}
th{color:#8b949e}
.locked{text-align:center;padding:40px;font-size:1.2em}
.locked input{margin-top:12px;width:250px}
.bar{height:6px;background:#30363d;border-radius:3px;margin-top:4px}
.bar-fill{height:100%;border-radius:3px;transition:width .3s}
.good{background:#238636}.warn{background:#d29922}.bad{background:#da3633}
</style>
</head>
<body>
<div id="app">
<div class="card locked" id="lock-screen">
  <h2>🔐 MSS Vault</h2>
  <p style="margin:12px 0;color:#8b949e">保险箱已锁定</p>
  <input type="password" id="pw" placeholder="主密码" onkeydown="if(event.key==='Enter')unlock()">
  <button onclick="unlock()">解锁</button>
  <p id="err" style="color:#da3633;margin-top:8px"></p>
</div>
<div id="main" style="display:none">
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <h2>🔐 MSS Vault</h2>
    <div>
      <input type="text" id="search" placeholder="搜索凭证..." oninput="search()" style="width:200px">
      <button onclick="refresh()">刷新</button>
      <button onclick="lock()" style="background:#30363d">锁定</button>
    </div>
  </div>
</div>
<div class="grid" id="metrics"></div>
<div class="card">
  <h3 style="margin-bottom:8px">凭证列表 <span id="count" style="color:#8b949e;font-size:.8em"></span></h3>
  <table><thead><tr><th>Key</th><th>分类</th><th>标签</th></tr></thead><tbody id="entries"></tbody></table>
</div>
<div class="card" id="warnings" style="display:none">
  <h3 style="color:#d29922">⚠️ 安全提醒</h3>
  <div id="warn-list"></div>
</div>
</div>
</div>
<script>
const API='';
async function api(p,m){let o={method:m||'GET'};if(m==='POST'){o.headers={'Content-Type':'application/json'};o.body=JSON.stringify(p)}let r=await fetch(API+p,p?('/'+Object.values(p).join('/')):'',o);return r.json()}
async function unlock(){let p=document.getElementById('pw').value;let r=await fetch(API+'/unlock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})});let d=await r.json();if(d.status==='unlocked'){document.getElementById('lock-screen').style.display='none';document.getElementById('main').style.display='block';refresh()}else{document.getElementById('err').textContent='密码错误'}}
async function lock(){await fetch(API+'/lock',{method:'POST'});location.reload()}
async function refresh(){try{let[s,h]=await Promise.all([fetch(API+'/stats').then(r=>r.json()),fetch(API+'/list').then(r=>r.json())]);document.getElementById('metrics').innerHTML=[{l:'凭证总数',v:(h.entries||[]).length},{l:'健康分',v:(s.health||{}).health_score+'/'+100,cls:(s.health||{}).grade||'A'},{l:'弱密码',v:(s.health||{}).weak_passwords?((s.health||{}).weak_passwords||[]).length:0,cls:((s.health||{}).weak_passwords||[]).length>0?'bad':'good'},{l:'重复',v:(s.health||{}).duplicate_passwords?((s.health||{}).duplicate_passwords||[]).length:0}].map(function(m){return'<div class="card metric"><div class="v '+(m.cls||'')+'">'+m.v+'</div><div class="l">'+m.l+'</div></div>'}).join('');document.getElementById('count').textContent=(h.entries||[]).length+'条';var icons={api_key:'🔌',password:'🔑',token:'🎫',personal_info:'🪪'};document.getElementById('entries').innerHTML=(h.entries||[]).map(function(e){return'<tr><td>'+(icons[e.category]||'📌')+' '+e.key+'</td><td>'+e.category+'</td><td>'+(e.tags||[]).join(', ')+'</td></tr>'}).join('');var w=s.health||{};if(w.weak_passwords&&w.weak_passwords.length>0){document.getElementById('warnings').style.display='block';document.getElementById('warn-list').innerHTML=w.weak_passwords.map(function(x){return'<p>🔸 '+x.key+': '+x.warning+'</p>'}).join('')}}catch(e){}}var si;function search(){clearTimeout(si);si=setTimeout(async function(){var q=document.getElementById('search').value;if(!q)return refresh();var r=await fetch(API+'/search/'+q).then(r=>r.json());document.getElementById('count').textContent=(r.entries||[]).length+'条';var icons={api_key:'🔌',password:'🔑',token:'🎫',personal_info:'🪪'};document.getElementById('entries').innerHTML=(r.entries||[]).map(function(e){return'<tr><td>'+(icons[e.category]||'📌')+' '+e.key+'</td><td>'+e.category+'</td><td>'+(e.tags||[]).join(', ')+'</td></tr>'}).join('')},300)}refresh();
</script>
</body>
</html>"""
