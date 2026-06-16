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
