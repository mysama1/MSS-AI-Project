"""
MSS-Agent + Microsoft Agent Framework (MAF) 集成示例.

证明: MSS-Agent 可以套在任何 Agent Framework 外面作为'意义场良心层'.

Usage:
    python maf_integration_demo.py

不依赖 Azure — 用 mock LLM 演示核心概念.
"""
import sys, time
from dataclasses import dataclass

sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project')
from mss_agent import MSSAgent, HeatTaxBudget, HeatTaxLevel
from mss_agent.core.delta import DeltaProtocol
from mss_agent.core.memory import DeltaMemory
from mss_agent.protocols import QuorumFast, ElevationProtocol


# ═══════════════════════════════════════════════════════
# Part 1: Mock MAF Agent (模拟 Microsoft Agent Framework)
# ═══════════════════════════════════════════════════════

@dataclass
class MAFTool:
    """模拟 MAF 的 tool 概念."""
    name: str
    description: str
    handler: callable


class MAFAgent:
    """
    模拟 Microsoft Agent Framework agent.

    真实 MAF 需要:
      from azure.ai.projects import AIProjectClient
      agent = project_client.agents.create_agent(...)

    这里用 mock 复刻 MAF 的核心模式:
      - agent.run(prompt) → think → use_tools → respond
      - 不内置意义场检测
    """
    def __init__(self, name: str, instructions: str, tools: list = None):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.call_count = 0
        self.tool_calls = []
        self.history = []

    def run(self, prompt: str) -> str:
        """模拟 MAF agent 执行."""
        self.call_count += 1
        self.history.append(prompt)

        # 模拟 tool use
        used_tools = []
        for tool in self.tools:
            if tool.name.lower() in prompt.lower():
                result = tool.handler(prompt)
                used_tools.append(tool.name)
                self.tool_calls.append((tool.name, prompt[:40]))

        # 模拟 LLM 响应
        if used_tools:
            response = f"[{self.name}] Used tools: {', '.join(used_tools)}. Task completed."
        else:
            response = f"[{self.name}] Processed: {prompt[:60]}..."

        return response


# ═══════════════════════════════════════════════════════
# Part 2: MSS-Agent Wrapper (套在 MAF 外面)
# ═══════════════════════════════════════════════════════

class MSSAgentWrapper:
    """
    将 MSS-Agent 套在任何 Agent 外面.

    三层拦截:
      1. 意义热税预算 — 这个任务值得做吗?
      2. agent.run() — 通过筛选的才执行
      3. Δ tick — 我陷入重复模式了吗?
    """
    def __init__(self, inner_agent, name: str = None):
        self.inner = inner_agent
        self.name = name or f"MSS-{inner_agent.name}"
        self.tax = HeatTaxBudget(threshold=2.0)
        self.delta = DeltaProtocol()
        self.memory = DeltaMemory()
        self.stats = {"passed": 0, "aborted": 0, "total": 0}

    def run(self, prompt: str) -> dict:
        """
        与 MAF agent.run() 同接口, 但在调用前加 MSS 检测.

        Returns: {aborted, reason, output, heat_tax, delta}
        """
        import hashlib
        task_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        self.stats["total"] += 1

        # ── Layer 1: 热税预算 ──
        meaning_heat, meaning_reason = _assess_meaning(prompt)
        self.tax.charge(HeatTaxLevel.L2_MEANING, meaning_heat, meaning_reason)

        if self.tax.l2_dominant() and meaning_heat > 0.05:
            self.stats["aborted"] += 1
            return {"aborted": True, "reason": f"LOW MEANING: {meaning_reason}",
                    "heat_tax": self.tax.snapshot(), "output": None, "delta": None}

        if self.tax.exceeded():
            self.stats["aborted"] += 1
            return {"aborted": True, "reason": f"HEAT TAX EXCEEDED: {self.tax.total():.3f}",
                    "heat_tax": self.tax.snapshot(), "output": None, "delta": None}

        # ── Layer 2: 执行 ──
        output = self.inner.run(prompt)
        self.stats["passed"] += 1

        # ── Layer 3: Δ tick ──
        novelty = self.memory.novelty_score(prompt)
        diversity = self.memory.diversity_score()
        current_delta = self.delta.tick(task_hash, novelty, diversity)
        self.memory.store(prompt, current_delta)

        return {"aborted": False, "reason": None,
                "output": output, "heat_tax": self.tax.snapshot(),
                "delta": current_delta}

    def health(self) -> dict:
        return {
            "agent": self.name,
            "stats": self.stats,
            "heat_tax": self.tax.snapshot(),
            "delta": self.delta.snapshot(),
            "memory": self.memory.stats(),
        }


def _assess_meaning(prompt: str) -> tuple:
    """评估任务的意义热税."""
    pl = prompt.lower().strip()
    if len(pl) < 5:
        return 0.08, "Prompt too short"
    waste = sum(1 for s in ["改写", "总结", "翻译", "换个说法", "简短点",
                             "重新说", "重写", "重新写", "再说一遍"] if s in pl)
    meaning = sum(1 for s in ["为什么", "分析", "设计", "实现", "评估", "优化",
                               "security", "review", "refactor", "test",
                               "安全", "风险", "架构", "方案", "策略"] if s in pl)
    # Short task with waste signals & no meaning → busywork
    if waste >= 1 and meaning == 0 and len(pl) < 30:
        return 0.06, "Short busywork: no meaningful intent"
    if waste > meaning and waste >= 2:
        return 0.06, "Busywork pattern detected"
    if meaning >= 2:
        return 0.002, "Meaningful intent"
    if meaning >= 1:
        return 0.005, "Some meaning"
    return 0.01, "Neutral"


# ═══════════════════════════════════════════════════════
# Part 3: Multi-Agent with Quorum + Elevation
# ═══════════════════════════════════════════════════════

class MSSOrchestrator:
    """
    MSS 多 Agent 编排器.

    整合:
      - 每个 Agent 带 MSS 检测
      - Quorum-Fast 检测群体收敛 (收敛=坏)
      - Elevation Protocol 解决冲突
    """
    def __init__(self):
        self.agents = {}
        self.quorum = QuorumFast()
        self.elevation = ElevationProtocol()

    def register(self, name: str, maf_agent: MAFAgent):
        self.agents[name] = MSSAgentWrapper(maf_agent, name)

    def broadcast(self, prompt: str) -> dict:
        """广播任务到所有 Agent, 收集结果."""
        results = {}
        for name, agent in self.agents.items():
            results[name] = agent.run(prompt)
            if not results[name]["aborted"]:
                # 报告到 quorum (用意义热税作为 score)
                score = 1.0 - results[name]["heat_tax"]["total"]
                self.quorum.report(name, max(0, score), prompt[:30])
        return results

    def resolve_conflict(self, a_name: str, b_name: str, conflict: str) -> dict:
        """两个 Agent 冲突 → 升维解决."""
        a = self.agents[a_name]
        b = self.agents[b_name]
        return self.elevation.resolve(
            f"Agent {a_name}: {a.inner.instructions[:60]}",
            f"Agent {b_name}: {b.inner.instructions[:60]}",
            conflict,
        )


# ═══════════════════════════════════════════════════════
# Part 4: Demo
# ═══════════════════════════════════════════════════════

def demo_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def demo():
    # ── 创建 MAF Agents ──
    def flights_api(prompt):
        return {"flights": ["CA123 08:00", "MU456 10:30", "CZ789 12:00"]}

    def hotel_api(prompt):
        return {"hotels": ["Hilton ¥800", "Marriott ¥650", "HomeInn ¥200"]}

    travel_agent = MAFAgent(
        name="TravelAgent",
        instructions="You book flights and hotels. Prioritize direct flights over layovers.",
        tools=[MAFTool("lookup_flights", "Search flights", flights_api),
               MAFTool("search_hotels", "Search hotels", hotel_api)]
    )

    review_agent = MAFAgent(
        name="CodeReviewer",
        instructions="You review code for security issues and code quality.",
    )

    writer_agent = MAFAgent(
        name="Writer",
        instructions="You write clear, concise documentation.",
    )

    # ── 套上 MSS-Agent ──
    orch = MSSOrchestrator()
    orch.register("travel", travel_agent)
    orch.register("reviewer", review_agent)
    orch.register("writer", writer_agent)

    # ═══ Demo 1: 有意义任务 → 通过 ═══
    demo_header("Demo 1: 有意义任务 → 全部通过")
    results = orch.broadcast("设计一个支持国际航班和酒店的 REST API 架构")
    for name, r in results.items():
        status = "OK ✓" if not r["aborted"] else "ABORT ✗"
        delta = f"Δ={r['delta']:.2f}" if r['delta'] else ""
        print(f"  {name:12s} {status}  {delta}")
    print(f"  Quorum: {orch.quorum.status()}")

    # ═══ Demo 2: 无意义任务 → 被拦截 ═══
    demo_header("Demo 2: 无意义改写任务 → MSS 拦截")
    boring_tasks = [
        ("改写一下：你好", True),
        ("分析 TravelAgent 的航班选择策略的安全风险", False),
        ("把上一条重新说一遍", True),
    ]
    agent = orch.agents["writer"]
    for task, expect_abort in boring_tasks:
        r = agent.run(task)
        actual = r["aborted"]
        match = "✓" if actual == expect_abort else "✗ MISMATCH"
        tag = "ABORT" if actual else "OK   "
        reason = r["reason"] if r["aborted"] else "passed"
        print(f"  [{match}] {tag}: \"{task[:40]}\" → {reason[:50]}")

    # ═══ Demo 3: 重复任务 → Δ下降 → 蜕壳告警 ═══
    demo_header("Demo 3: 重复任务 → Δ下降 → 蜕壳检测")
    tester = orch.agents["reviewer"]
    for i in range(6):
        task = "审查这段代码: def login(user, pwd): return db.query(user)" if i < 4 else "审查这段代码的注入风险并给出防护方案"
        r = tester.run(task)
        delta = r['delta'] or 0
        bar = '█' * int(delta * 20)
        alert = " ⚠️ MOLTING" if tester.delta.molting_alert else ""
        aborted = " [ABORTED]" if r["aborted"] else ""
        print(f"  t{i}: Δ={delta:.2f} {bar}{alert}{aborted} | {task[:50]}")

    # ═══ Demo 4: 多Agent冲突 → 升维解决 ═══
    demo_header("Demo 4: Agent冲突 → 升维(不投票)")
    resolution = orch.resolve_conflict(
        "travel", "reviewer",
        "TravelAgent wants direct flights (speed). CodeReviewer wants cheapest (cost). What to do?"
    )
    print(f"  被困维度: {resolution['trapped_dim']}")
    print(f"  升维到:   {resolution['elevation']}")
    print(f"  解决方案: {resolution['resolution'][:120]}")

    # ═══ 健康报告 ═══
    demo_header("Final: 健康报告")
    for name, agent in orch.agents.items():
        h = agent.health()
        print(f"  {name:12s} | passed={h['stats']['passed']} aborted={h['stats']['aborted']} "
              f"| tax={h['heat_tax']['total']:.2f} | Δ={h['delta']['health']} "
              f"| mem={h['memory']['active']}a/{h['memory']['closed']}c")

    print(f"\n{'='*60}")
    print("  MSS-Agent + MAF: 套在外面, 不替代, 做良心.")
    print(f"{'='*60}")


if __name__ == '__main__':
    demo()
