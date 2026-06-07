"""MSS-Agent CLI — 命令行快速评估任务意义.

Usage:
  mss-agent check "改写一下：你好"       # 检查任务是否会被拦截
  mss-agent status                       # 查看会话热税统计
  mss-agent run "设计REST API架构"        # 执行一次 Agent run (mock LLM)
"""
import sys, json
sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project')
from mss_agent import MSSAgent


def check(prompt: str):
    agent = MSSAgent(name="cli", llm=lambda p: f"OK: {p[:40]}")
    result = agent.run(prompt)
    if result.aborted:
        print(f"🛑 ABORTED: {result.reason}")
    else:
        print(f"✅ PASSED: {result.output}")
    print(f"   热税: {agent.tax.total():.2f} | Δ: {agent.delta.health()} | "
          f"执行: {agent.run_count} | 拦截: {agent.abort_count}")


def status():
    agent = MSSAgent(name="cli-status", llm=lambda p: "OK")
    # Simulate a few runs
    for p in ["设计API","改写:你好","分析安全","优化查询"]:
        agent.run(p)
    report = agent.health_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))


def run(prompt: str):
    agent = MSSAgent(name="cli-runner", llm=lambda p: f"[Mock] Processed: {p[:60]}")
    result = agent.run(prompt)
    print(f"Output: {result.output}")
    print(f"Aborted: {result.aborted}")
    if result.reason:
        print(f"Reason: {result.reason}")


def help():
    print("""MSS-Agent CLI — 意义场自我审计 Agent

Commands:
  check <prompt>   检查任务是否会被热税拦截
  status           查看健康报告 (含热税 + Δ + 记忆)
  run <prompt>     执行一次 Agent 调用 (mock LLM)
  help             显示此帮助

Examples:
  mss-agent check "改写一下：你好"
  mss-agent status
  mss-agent run "设计一个安全的REST API"

GitHub: https://github.com/mysama1/MSS-AI-Project
PyPI:   https://pypi.org/project/mss-agent/
""")


def main():
    args = sys.argv[1:]
    if not args:
        help()
    elif args[0] == "check" and len(args) > 1:
        check(" ".join(args[1:]))
    elif args[0] == "status":
        status()
    elif args[0] == "run" and len(args) > 1:
        run(" ".join(args[1:]))
    else:
        help()
