"""
Agent HTTP Server — Agent 微服务

和 Vault API 配对: Vault 管凭证, Agent 管智能.

用法:
    mss-agent serve --model qwen2.5:7b

API:
    POST /run     {"prompt": "...", "style": "prose", "semantic": true}
    POST /stream  {"prompt": "..."}  → SSE 流式
    GET  /health
    GET  /report
"""
import json
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class AgentAPIHandler(BaseHTTPRequestHandler):
    agent = None

    def log_message(self, *args):
        pass

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _error(self, msg, status=400):
        self._json({"error": msg}, status)

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")

        if path == "/health" or path == "":
            return self._json({
                "status": "ok",
                "agent": self.agent.name if self.agent else "none",
                "model": str(getattr(self.agent, 'llm', 'none')),
                "bridge": self.agent.l2bridge.level.name if self.agent else "N/A",
            })

        if path == "/report":
            if not self.agent:
                return self._error("no agent")
            return self._json(self.agent.health_report())

        self._error("not found", 404)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len)) if content_len > 0 else {}

        if path == "/run":
            prompt = body.get("prompt", "")
            if not prompt:
                return self._error("prompt required")

            style = body.get("style", "auto")
            semantic = body.get("semantic", False)

            t0 = time.time()
            result = self.agent.run(prompt)
            elapsed = time.time() - t0

            return self._json({
                "output": result.output,
                "aborted": result.aborted,
                "delta": result.delta,
                "elapsed_ms": round(elapsed * 1000),
                "bridge": self.agent.l2bridge.level.name,
                "heat_tax": result.heat_tax.get("total", 0),
            })

        if path == "/stream":
            prompt = body.get("prompt", "")
            if not prompt:
                return self._error("prompt required")

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            try:
                for chunk in self.agent.run_stream(prompt, semantic=True):
                    self.wfile.write(f"data: {json.dumps({'text': chunk})}\n\n".encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
            except Exception as e:
                self.wfile.write(f"data: {json.dumps({'error': str(e)})}\n\n".encode())

            return

        if path == "/reset":
            self.agent.reset()
            return self._json({"status": "reset"})

        self._error("not found", 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def serve_agent(model: str = "qwen2.5:7b", port: int = 5100, vault_path: str = None):
    """启动 Agent HTTP 服务."""
    from mssclaw.core.agent import MSSAgent
    from mssclaw.core.llm_backend import OllamaBackend, create_backend

    print(f"🤖 MSS Agent API")
    print(f"   模型: {model}")
    print(f"   端口: {port}")

    # Check Ollama
    be = create_backend("auto", model=model)
    if isinstance(be, OllamaBackend):
        models = be.list_models()
        if model not in models:
            avail = [m for m in models if not m.startswith("mss-ai-v3")][:3]
            print(f"   ⚠️  {model} 不可用, 尝试: {avail[0] if avail else 'dummy'}")
            if avail:
                model = avail[0]
                be = create_backend("auto", model=model)

    agent = MSSAgent(name="api-agent", llm=be)

    if vault_path:
        agent.configure_vault(vault_path)
        print(f"   🔐 Vault: {vault_path}")

    agent.cognition.register_capability("api_serve", tier=3)
    agent.cognition.anchor_identity("api-agent", "MSS API Agent", strategy="virus")

    AgentAPIHandler.agent = agent

    server = HTTPServer(("127.0.0.1", port), AgentAPIHandler)
    print(f"\n   端点: http://127.0.0.1:{port}")
    print(f"   curl -X POST http://127.0.0.1:{port}/run -d '{{\"prompt\":\"hello\"}}'")
    print(f"   curl http://127.0.0.1:{port}/report")
    print(f"\n   Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
