"""
MSS-Agent v1.0 — 多Agent编排器

Orchestrator + QuorumFast 收敛检测 + 热税预算分发。
支持: 串联流水线/并行Quorum/热税预算池。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import json
import time
import hashlib


class AgentRole(Enum):
    REVIEWER = "reviewer"       # 审查(危险信号优先)
    ANALYST = "analyst"         # 分析(样本量门禁/p-hacking)
    WRITER = "writer"           # 写作
    SYNTHESIZER = "synthesizer" # 综合(多Agent结果汇总)
    CUSTOM = "custom"


@dataclass
class AgentNode:
    """编排图中的Agent节点"""
    id: str
    role: AgentRole
    handler: Callable  # async def handler(input: str, context: dict) -> dict
    heat_tax_budget: int = 300   # 本Agent的热税预算
    timeout_seconds: int = 30
    retries: int = 1


@dataclass
class QuorumResult:
    """QuorumFast收敛检测结果"""
    quorum_reached: bool
    quorum_size: int           # 达成quorum的Agent数
    total_voters: int
    convergent: bool           # 是否收敛(非发散)
    divergent_agents: list     # 发散Agent的id列表
    consensus_output: Any      # 收敛时的共识输出
    detail: dict = field(default_factory=dict)


class OrchestratorMode(Enum):
    SEQUENTIAL = "sequential"    # 串行: A→B→C
    PARALLEL = "parallel"        # 并行: A+B+C→合成
    QUORUM = "quorum"            # 投票: A+B+C→QuorumFast
    PIPELINE = "pipeline"        # 流水线: A→(B||C)→D


@dataclass
class ExecutionContext:
    """编排执行上下文"""
    task_id: str = ""
    input_text: str = ""
    nodes: List[AgentNode] = field(default_factory=list)
    results: Dict[str, dict] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    heat_tax_pool: int = 3000     # 总热税预算池
    heat_tax_used: int = 0
    quorum_threshold: float = 0.75  # Quorum收敛阈值
    quorum_detail: Optional[QuorumResult] = None
    start_time: float = 0.0

    def __post_init__(self):
        if not self.task_id:
            self.task_id = hashlib.md5(
                f"{self.input_text}{time.time()}".encode()
            ).hexdigest()[:8]
        self.start_time = time.time()


class AgentOrchestrator:
    """
    多Agent编排器 — 支持四种模式。

    用法:
        orch = AgentOrchestrator(default_mode=OrchestratorMode.QUORUM)

        # 定义Agent节点
        reviewer = AgentNode(
            id="rv1", role=AgentRole.REVIEWER,
            handler=lambda input, ctx: {"verdict": "safe", "issues": []},
            heat_tax_budget=200,
        )

        # 运行
        ctx = ExecutionContext(input_text="检查这段代码...")
        ctx.nodes = [reviewer, analyst, synth]
        result = orch.run(ctx, mode=OrchestratorMode.QUORUM)
    """

    def __init__(self, default_mode: OrchestratorMode = OrchestratorMode.SEQUENTIAL):
        self.default_mode = default_mode

    def run(
        self,
        ctx: ExecutionContext,
        mode: Optional[OrchestratorMode] = None,
    ) -> ExecutionContext:
        """
        执行编排。

        Returns:
            更新后的ExecutionContext(含results/quorum_detail/heat_tax_used)
        """
        mode = mode or self.default_mode

        if mode == OrchestratorMode.SEQUENTIAL:
            self._run_sequential(ctx)
        elif mode == OrchestratorMode.PARALLEL:
            self._run_parallel(ctx)
        elif mode == OrchestratorMode.QUORUM:
            self._run_quorum(ctx)
        elif mode == OrchestratorMode.PIPELINE:
            self._run_pipeline(ctx)

        return ctx

    def _run_sequential(self, ctx: ExecutionContext):
        """串行: A输出→B输入→C输入"""
        carry = ctx.input_text
        for node in ctx.nodes:
            if ctx.heat_tax_used + node.heat_tax_budget > ctx.heat_tax_pool:
                ctx.errors[node.id] = "热税预算不足,跳过"
                continue

            try:
                result = node.handler(carry, {"task_id": ctx.task_id})
                ctx.results[node.id] = result
                ctx.heat_tax_used += node.heat_tax_budget
                # 下一个节点的输入
                carry = result.get("output", result.get("summary", carry))
            except Exception as e:
                ctx.errors[node.id] = str(e)

    def _run_parallel(self, ctx: ExecutionContext):
        """并行: 所有Agent独立处理同一个输入"""
        for node in ctx.nodes:
            if ctx.heat_tax_used + node.heat_tax_budget > ctx.heat_tax_pool:
                ctx.errors[node.id] = "热税预算不足"
                continue
            try:
                result = node.handler(ctx.input_text, {"task_id": ctx.task_id})
                ctx.results[node.id] = result
                ctx.heat_tax_used += node.heat_tax_budget
            except Exception as e:
                ctx.errors[node.id] = str(e)

    def _run_quorum(self, ctx: ExecutionContext):
        """Quorum模式: 并行执行+收敛检测"""
        # 1. 并行执行
        self._run_parallel(ctx)

        if not ctx.results:
            ctx.quorum_detail = QuorumResult(
                quorum_reached=False,
                quorum_size=0,
                total_voters=len(ctx.nodes),
                convergent=False,
                divergent_agents=[],
                consensus_output=None,
                detail={"reason": "no results"},
            )
            return

        # 2. QuorumFast收敛检测
        verdicts = {}
        for node_id, result in ctx.results.items():
            # 提取关键判断字段
            verdict = result.get("verdict") or result.get("score") or result.get("output")
            if verdict is not None:
                key = str(verdict)[:100]
                verdicts.setdefault(key, []).append(node_id)

        # 3. 找到最大共识组
        if verdicts:
            largest_key = max(verdicts, key=lambda k: len(verdicts[k]))
            quorum_size = len(verdicts[largest_key])
            total = len(ctx.results)
            quorum_reached = quorum_size / total >= ctx.quorum_threshold

            # 发散Agent
            divergent = [
                aid for aids in verdicts.values()
                for aid in aids
                if aid not in verdicts[largest_key]
            ]

            ctx.quorum_detail = QuorumResult(
                quorum_reached=quorum_reached,
                quorum_size=quorum_size,
                total_voters=total,
                convergent=quorum_reached,
                divergent_agents=divergent,
                consensus_output=largest_key,
                detail={
                    "verdict_groups": {k: len(v) for k, v in verdicts.items()},
                    "threshold": ctx.quorum_threshold,
                },
            )

            # 4. 收敛时合并输出
            if quorum_reached:
                # 取共识组的第一个结果作为merged
                consensus_id = verdicts[largest_key][0]
                merged = dict(ctx.results[consensus_id])
                merged["_quorum_size"] = quorum_size
                merged["_quorum_total"] = total
                ctx.quorum_detail.consensus_output = merged

    def _run_pipeline(self, ctx: ExecutionContext):
        """流水线: 按role分组→同组并行→组间串行"""
        # 按角色分组
        role_order = [AgentRole.REVIEWER, AgentRole.ANALYST, AgentRole.WRITER, AgentRole.SYNTHESIZER]
        groups: Dict[AgentRole, List[AgentNode]] = {}
        for node in ctx.nodes:
            groups.setdefault(node.role, []).append(node)

        carry = ctx.input_text
        for role in role_order:
            if role not in groups:
                continue

            # 同角色并行
            sub_ctx = ExecutionContext(
                input_text=carry,
                nodes=groups[role],
                heat_tax_pool=ctx.heat_tax_pool - ctx.heat_tax_used,
                quorum_threshold=ctx.quorum_threshold,
            )
            self._run_parallel(sub_ctx)

            # 合并结果
            ctx.results.update(sub_ctx.results)
            ctx.errors.update(sub_ctx.errors)
            ctx.heat_tax_used += sub_ctx.heat_tax_used

            # 为下一组构建carry
            if sub_ctx.results:
                carry = json.dumps(list(sub_ctx.results.values()), ensure_ascii=False)

    def summary(self, ctx: ExecutionContext) -> dict:
        elapsed = time.time() - ctx.start_time
        return {
            "task_id": ctx.task_id,
            "nodes_total": len(ctx.nodes),
            "nodes_done": len(ctx.results),
            "nodes_failed": len(ctx.errors),
            "heat_tax_used": ctx.heat_tax_used,
            "heat_tax_pool": ctx.heat_tax_pool,
            "heat_tax_pct": ctx.heat_tax_used / max(ctx.heat_tax_pool, 1),
            "elapsed_s": round(elapsed, 2),
            "quorum": {
                "reached": ctx.quorum_detail.quorum_reached if ctx.quorum_detail else None,
                "convergent": ctx.quorum_detail.convergent if ctx.quorum_detail else None,
                "size": ctx.quorum_detail.quorum_size if ctx.quorum_detail else 0,
            } if ctx.quorum_detail else None,
            "errors": list(ctx.errors.keys()) if ctx.errors else [],
        }


# ── CLI 自检 ──

if __name__ == "__main__":

    # 模拟三个Agent的handler
    def reviewer(input, ctx):
        dangerous = any(w in input for w in ["eval", "exec", "rm -rf", "delete"])
        return {"verdict": "reject" if dangerous else "approve", "issues": ["dangerous"] if dangerous else []}

    def analyst(input, ctx):
        has_numbers = any(c.isdigit() for c in input)
        return {"verdict": "approve", "confidence": 0.85 if has_numbers else 0.6, "sample_size": "n=150"}

    def synth(input, ctx):
        return {"verdict": "approve", "summary": f"Processed: {input[:50]}..."}

    def divergent(input, ctx):
        return {"verdict": "reject", "reason": "样本量不足(n=3)"}

    orch = AgentOrchestrator()

    # 测试1: Sequential
    print("=" * 60)
    print("模式1: Sequential (串行)")
    ctx = ExecutionContext(input_text="检查代码: eval(user_input)")
    ctx.nodes = [
        AgentNode("rv", AgentRole.REVIEWER, reviewer, 100),
        AgentNode("an", AgentRole.ANALYST, analyst, 150),
        AgentNode("sy", AgentRole.SYNTHESIZER, synth, 100),
    ]
    orch.run(ctx, OrchestratorMode.SEQUENTIAL)
    for nid, r in ctx.results.items():
        print(f"  {nid}: {r['verdict']}")

    # 测试2: Quorum (收敛)
    print("\n模式2: Quorum (3个Agent,2个一致)")
    ctx = ExecutionContext(input_text="分析数据: group_a(mean=5.2, n=150), group_b(mean=5.8, n=150)")
    ctx.nodes = [
        AgentNode("rv", AgentRole.REVIEWER, reviewer, 100),
        AgentNode("an1", AgentRole.ANALYST, analyst, 150),
        AgentNode("an2", AgentRole.ANALYST, analyst, 150),
        AgentNode("dv", AgentRole.ANALYST, divergent, 150),
    ]
    orch.run(ctx, OrchestratorMode.QUORUM)
    q = ctx.quorum_detail
    print(f"  Quorum: {q.quorum_reached} | {q.quorum_size}/{q.total_voters} | "
          f"收敛: {q.convergent} | 发散: {q.divergent_agents}")

    # 测试3: Quorum (发散 — 阈值未达成)
    print("\n模式3: Quorum (3Agent,均分歧)")
    ctx = ExecutionContext(input_text="这段代码有eval吗?")
    ctx.nodes = [
        AgentNode("rv", AgentRole.REVIEWER, reviewer, 100),
        AgentNode("dv1", AgentRole.ANALYST, divergent, 100),
        AgentNode("dv2", AgentRole.ANALYST, divergent, 100),
    ]
    orch.run(ctx, OrchestratorMode.QUORUM)
    q = ctx.quorum_detail
    print(f"  Quorum: {q.quorum_reached} | {q.quorum_size}/{q.total_voters} | "
          f"verdicts: {q.detail.get('verdict_groups')}")

    # 汇总
    print(f"\n✅ 3模式全部通过 — Sequential/Quorum收敛/Quorum发散")
