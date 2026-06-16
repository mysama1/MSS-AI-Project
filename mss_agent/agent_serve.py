"""mss-agent serve wrapper."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mssclaw.core.agent_server import serve_agent

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--port", type=int, default=5100)
    ap.add_argument("--vault", default=None)
    args = ap.parse_args()
    serve_agent(model=args.model, port=args.port, vault_path=args.vault)
