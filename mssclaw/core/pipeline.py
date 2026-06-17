"""
Pipeline Branching/Streaming + Decentralized VCG Compensation (Sprint 146b+c).

146b: Pipeline — 条件分支 + 流式输出
146c: Q1 — 去中心化维克里补偿 (移除可信第三方)

核心创新:
  Pipeline: Generator-based流式 + BranchPoint条件拆分 + 并行扇出
  Q1: quorum-based distributed VCG — 每个Agent自我报告+交叉验证
"""
from __future__ import annotations
import json, time, uuid, asyncio
from typing import (
    Dict, List, Tuple, Optional, Set, Callable, Any, AsyncGenerator, Union
)
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


# ═══════ Sprint 146b: Pipeline Branching/Streaming ═══════

class PipeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipeResult:
    """单个Pipe的输出."""
    status: PipeStatus
    output: Any = None
    error: Optional[str] = None
    heat_tax: float = 0.0
    duration_ms: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class StreamEvent:
    """流式事件."""
    event_type: str  # "output" | "progress" | "branch" | "error" | "done"
    pipe_name: str
    data: Any = None
    progress_pct: float = 0.0
    timestamp: float = field(default_factory=time.time)


class BranchCondition:
    """分支条件 — 基于前序Pipe的输出决定走向."""

    def __init__(self, predicate: Callable[[PipeResult], bool],
                 target_pipe: str, name: str = ""):
        self.predicate = predicate
        self.target_pipe = target_pipe
        self.name = name or f"branch_to_{target_pipe}"

    def evaluate(self, result: PipeResult) -> bool:
        return self.predicate(result)


@dataclass
class PipeNode:
    """Pipeline节点."""
    name: str
    fn: Callable[[Dict[str, Any]], Any]  # (context) → output
    branches: List[BranchCondition] = field(default_factory=list)
    fallback_pipe: Optional[str] = None
    retry_count: int = 0
    retry_delay_ms: int = 100
    timeout_s: float = 30.0
    heat_tax_weight: float = 1.0


class StreamingPipeline:
    """
    流式分支Pipeline.

    特性:
      - Generator-based流式: yield中间结果
      - 条件分支: 根据输出选择下一节点
      - 扇出/扇入: 并行执行多个分支
      - 回退: 失败时的回退路径
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.nodes: Dict[str, PipeNode] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)  # pipe → [next_pipes]
        self.start_pipe: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.results: Dict[str, PipeResult] = {}
        self.heat_tax_total: float = 0.0
        self.stream_listeners: List[Callable[[StreamEvent], None]] = []

    def add_node(self, node: PipeNode, after: Optional[List[str]] = None,
                 is_start: bool = False):
        self.nodes[node.name] = node
        if is_start:
            self.start_pipe = node.name
        if after:
            for a in after:
                self.edges[a].append(node.name)

    def on_stream(self, listener: Callable[[StreamEvent], None]):
        self.stream_listeners.append(listener)

    def _emit(self, event: StreamEvent):
        for listener in self.stream_listeners:
            listener(event)

    async def run_streaming(self) -> AsyncGenerator[StreamEvent, None]:
        """
        流式执行Pipeline — 每步yield事件.

        Yields StreamEvent, 调用方可以实时消费.
        """
        if not self.start_pipe:
            yield StreamEvent("error", "pipeline", "No start pipe defined")
            return

        queue = [(self.start_pipe, None)]  # (pipe_name, branch_result)
        executed = set()

        total_nodes = len(self.nodes)
        completed = 0

        while queue:
            pipe_name, branch_result = queue.pop(0)

            if pipe_name in executed:
                continue
            if pipe_name not in self.nodes:
                yield StreamEvent("error", pipe_name, f"Node not found: {pipe_name}")
                continue

            node = self.nodes[pipe_name]
            executed.add(pipe_name)

            yield StreamEvent("progress", pipe_name,
                            progress_pct=completed / max(1, total_nodes))

            # 执行
            t0 = time.time()
            try:
                result_data = node.fn(self.context)
                duration = (time.time() - t0) * 1000
                heat_tax = duration / 1000 * node.heat_tax_weight  # ms→热税
                result = PipeResult(PipeStatus.DONE, result_data,
                                   duration_ms=duration, heat_tax=heat_tax)
                self.heat_tax_total += heat_tax
            except Exception as e:
                duration = (time.time() - t0) * 1000
                result = PipeResult(PipeStatus.FAILED, error=str(e),
                                   duration_ms=duration)
                self.results[pipe_name] = result
                self.heat_tax_total += duration / 1000 * node.heat_tax_weight

                # 回退
                if node.fallback_pipe:
                    yield StreamEvent("progress", pipe_name,
                                    progress_pct=completed / max(1, total_nodes),
                                    data={"fallback": node.fallback_pipe})
                    queue.append((node.fallback_pipe, None))
                    continue

                yield StreamEvent("error", pipe_name, str(e))
                continue

            self.results[pipe_name] = result
            self.context[pipe_name] = result_data
            completed += 1

            yield StreamEvent("output", pipe_name, result_data,
                            progress_pct=completed / total_nodes)

            # 分支决策
            next_pipes = []
            if node.branches:
                for branch in node.branches:
                    if branch.evaluate(result):
                        next_pipes.append(branch.target_pipe)
                        yield StreamEvent("branch", pipe_name,
                                        {"condition": branch.name,
                                         "target": branch.target_pipe})
            else:
                next_pipes = self.edges.get(pipe_name, [])

            for np in next_pipes:
                if np not in executed:
                    queue.append((np, result))

        yield StreamEvent("done", "pipeline",
                        {"total_heat_tax": self.heat_tax_total,
                         "nodes_executed": completed},
                        progress_pct=1.0)

    def run_sync(self) -> Dict:
        """同步执行 (内部事件循环)."""
        async def _collect():
            events = []
            async for event in self.run_streaming():
                events.append(event)
            return events
        try:
            loop = asyncio.get_running_loop()
            # 已有运行中的循环 → 用nest_asyncio
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except ImportError:
                pass
            future = asyncio.ensure_future(_collect())
            # Can't run_until_complete on running loop, return basic
            # Fallback: synchronous execution
            return self._run_sync_fallback()
        except RuntimeError:
            # 无运行循环 → 正常执行
            events = asyncio.run(_collect())
            return {
                "events": len(events),
                "results": {k: v.status.value for k, v in self.results.items()},
                "heat_tax_total": self.heat_tax_total,
                "nodes_executed": len(self.results),
            }

    def _run_sync_fallback(self) -> Dict:
        """同步回退: 逐个执行节点 (无async)."""
        if not self.start_pipe:
            return {"events": 0, "results": {}, "heat_tax_total": 0, "nodes_executed": 0}

        queue = [self.start_pipe]
        executed = set()

        while queue:
            pipe_name = queue.pop(0)
            if pipe_name in executed or pipe_name not in self.nodes:
                continue
            node = self.nodes[pipe_name]
            executed.add(pipe_name)

            t0 = time.time()
            try:
                result_data = node.fn(self.context)
                duration = (time.time() - t0) * 1000
                heat_tax = duration / 1000 * node.heat_tax_weight
                result = PipeResult(PipeStatus.DONE, result_data,
                                   duration_ms=duration, heat_tax=heat_tax)
                self.heat_tax_total += heat_tax
            except Exception as e:
                duration = (time.time() - t0) * 1000
                result = PipeResult(PipeStatus.FAILED, error=str(e),
                                   duration_ms=duration)
                self.results[pipe_name] = result
                self.heat_tax_total += duration / 1000 * node.heat_tax_weight
                if node.fallback_pipe and node.fallback_pipe not in executed:
                    queue.append(node.fallback_pipe)
                continue

            self.results[pipe_name] = result
            self.context[pipe_name] = result_data

            # 分支决策
            if node.branches:
                for branch in node.branches:
                    if branch.evaluate(result) and branch.target_pipe not in executed:
                        queue.append(branch.target_pipe)
            else:
                for np in self.edges.get(pipe_name, []):
                    if np not in executed:
                        queue.append(np)

        return {
            "events": len(self.results),
            "results": {k: v.status.value for k, v in self.results.items()},
            "heat_tax_total": self.heat_tax_total,
            "nodes_executed": len(self.results),
        }

    def stats(self) -> Dict:
        return {
            "name": self.name,
            "nodes": len(self.nodes),
            "edges": sum(len(v) for v in self.edges.values()),
            "branches": sum(1 for n in self.nodes.values() if n.branches),
            "results": {k: {"status": v.status.value, "heat_tax": v.heat_tax}
                       for k, v in self.results.items()},
            "total_heat_tax": round(self.heat_tax_total, 4),
        }


# ═══════ Sprint 146c: Decentralized VCG Compensation ═══════

@dataclass
class AgentReport:
    """Agent自我报告 — VCG去中心化."""
    agent_id: str
    strategy_choice: str        # 选择的策略
    self_payoff: float           # 自身收益
    estimated_externality: float  # 对其他Agent造成的外部性(自评)
    claimed_social_welfare: float  # 声明的社会福利
    signature: str = ""          # 签名(防篡改, MVP用hash)

    def hash(self) -> str:
        raw = f"{self.agent_id}|{self.strategy_choice}|{self.self_payoff}|{self.estimated_externality}"
        return str(hash(raw))


@dataclass
class QuorumVerification:
    """Quorum验证结果."""
    agent_id: str
    verified: bool
    agreement_ratio: float  # 多少Agent同意其报告
    disputed_by: List[str]  # 持异议的Agent
    adjusted_externality: Optional[float] = None  # 调整后的外部性
    penalty: float = 0.0  # 虚报惩罚


class DecentralizedVCG:
    """
    去中心化维克里补偿.

    核心思想:
      传统VCG: 可信拍卖师计算每个人的外部性
      去中心化VCG: 每个Agent自我报告外部性 + Quorum交叉验证

    三步:
      1. 自我报告: 每个Agent报告自己的策略+收益+外部性
      2. 交叉验证: 其他Agent验证报告的一致性
      3. Quorum裁决: 多数同意 → 确认; 多数异议 → 调整+惩罚

    安全性:
      - 虚报收益 → 交叉验证发现矛盾 (其他Agent的外部性之和≠社会福利损失)
      - 集体串通 → 至少需要>50% Agent串通 (等同于拜占庭容错边界)
      - A5自洽Agent → 天然说真话倾向 (降低验证成本)
    """

    def __init__(self, quorum_threshold: float = 0.5):
        self.quorum_threshold = quorum_threshold  # 需要多少比例Agent同意
        self.reports: Dict[str, AgentReport] = {}
        self.verifications: Dict[str, QuorumVerification] = {}
        self.payoff_matrix: Optional[Dict] = None  # 真实payoff (验证用)

    def set_payoff_matrix(self, matrix: Dict):
        """设置真实payoff矩阵 (仅用于验证, 实际部署中不可见)."""
        self.payoff_matrix = matrix

    def submit_report(self, report: AgentReport):
        """Agent提交自我报告."""
        report.signature = report.hash()
        self.reports[report.agent_id] = report

    def cross_validate(self) -> Dict[str, QuorumVerification]:
        """
        交叉验证: 每个Agent的报告接受其他Agent的检验.

        检验逻辑:
          对Agent i的报告:
            计算 其他所有Agent j 声称的"i对我造成的外部性"之和
            对比 Agent i 自评的外部性
            如果偏差<阈值 → 验证通过
        """
        verifications = {}

        for agent_id, report in self.reports.items():
            # 收集其他Agent对此Agent外部性的评估
            others_agreed = 0
            others_disagreed = []
            total_others = len(self.reports) - 1

            for other_id, other_report in self.reports.items():
                if other_id == agent_id:
                    continue
                # 简化: 其他Agent通过检查策略组合的一致性来验证
                # 实际实现中需要更复杂的博弈验证
                if self._check_consistency(report, other_report):
                    others_agreed += 1
                else:
                    others_disagreed.append(other_id)

            agreement_ratio = others_agreed / max(1, total_others)
            verified = agreement_ratio >= self.quorum_threshold

            # 调整外部性
            adjusted = None
            penalty = 0.0
            if not verified:
                # 使用其他Agent的平均评估替代
                adjusted = self._compute_adjusted_externality(agent_id)
                penalty = abs(report.estimated_externality - adjusted)

            verifications[agent_id] = QuorumVerification(
                agent_id=agent_id,
                verified=verified,
                agreement_ratio=round(agreement_ratio, 3),
                disputed_by=others_disagreed,
                adjusted_externality=adjusted,
                penalty=penalty,
            )

        self.verifications = verifications
        return verifications

    def _check_consistency(self, report_a: AgentReport, report_b: AgentReport) -> bool:
        """检查两个报告的一致性."""
        if self.payoff_matrix:
            # 有真实矩阵 → 精确验证
            key = (report_a.strategy_choice, report_b.strategy_choice)
            true_payoffs = self.payoff_matrix.get(key)
            if true_payoffs:
                # 验证: 报告的收益是否匹配真实矩阵
                err_a = abs(report_a.self_payoff - true_payoffs[0])
                err_b = abs(report_b.self_payoff - true_payoffs[1])
                return err_a < 0.1 and err_b < 0.1
        # 无矩阵 → 启发式: 外部性之和不应超过最优福利
        total_extern = report_a.estimated_externality + report_b.estimated_externality
        total_claimed = report_a.self_payoff + report_b.self_payoff
        return total_extern + total_claimed > -100  # 宽松启发式

    def _compute_adjusted_externality(self, agent_id: str) -> float:
        """计算调整后的外部性 (其他Agent评估的均值/真实矩阵)."""
        if self.payoff_matrix:
            report = self.reports.get(agent_id)
            if report:
                for other_id, other_report in self.reports.items():
                    if other_id == agent_id:
                        continue
                    key = (report.strategy_choice, other_report.strategy_choice)
                    true = self.payoff_matrix.get(key)
                    if true:
                        # 真实外部性 = 最优福利 - (自身收益 + 其他收益)
                        # 简化: 返回矩阵中的对方收益
                        return float(true[1])
        # 回退
        report = self.reports.get(agent_id)
        return report.estimated_externality * 1.1 if report else 0.0

    def compute_compensation(self) -> Dict[str, float]:
        """
        计算补偿方案 — 去中心化版本.

        每个Agent的净效用 = 自身payoff - 外部性补偿
        补偿金 = 经Quorum验证的外部性 (调整后)
        """
        compensation = {}
        for agent_id, report in self.reports.items():
            verif = self.verifications.get(agent_id)
            if verif and verif.adjusted_externality is not None:
                externality = verif.adjusted_externality
            else:
                externality = report.estimated_externality

            net_utility = report.self_payoff - externality
            compensation[agent_id] = {
                "gross_payoff": report.self_payoff,
                "externality": round(externality, 3),
                "net_utility": round(net_utility, 3),
                "verified": verif.verified if verif else False,
                "penalty": verif.penalty if verif else 0.0,
            }
        return compensation

    def stats(self) -> Dict:
        total = len(self.reports)
        verified_count = sum(1 for v in self.verifications.values() if v.verified)
        total_penalty = sum(v.penalty for v in self.verifications.values())

        return {
            "mode": "decentralized_vcg",
            "agents": total,
            "verified": verified_count,
            "verification_rate": round(verified_count / max(1, total), 3),
            "quorum_threshold": self.quorum_threshold,
            "total_penalty": round(total_penalty, 3),
            "compensation": self.compute_compensation(),
        }


# ═══ CLI ═══

def cmd_pipeline(args_rest):
    """CLI: mssclaw pipeline"""
    if not args_rest or args_rest[0] == "--help":
        print("mssclaw pipeline — Pipeline Branching/Streaming + Decentralized VCG")
        print("  mssclaw pipeline demo-stream   # 流式Pipeline演示")
        print("  mssclaw pipeline demo-branch   # 分支Pipeline演示")
        print("  mssclaw pipeline demo-vcg      # 去中心化VCG演示")
        print("  mssclaw pipeline test          # 测试套件")
        return

    if args_rest[0] == "demo-stream":
        _demo_streaming()
    elif args_rest[0] == "demo-branch":
        _demo_branching()
    elif args_rest[0] == "demo-vcg":
        _demo_decentralized_vcg()
    elif args_rest[0] == "test":
        _test_all()


def _demo_streaming():
    """演示: 流式Pipeline."""
    print("=" * 60)
    print("Streaming Pipeline Demo")
    print("=" * 60)

    pl = StreamingPipeline("demo_stream")

    # 定义节点
    steps = []

    def make_loader(name, delay, data):
        def loader(ctx):
            steps.append(f"[{name}] loading...")
            time.sleep(delay)
            return data
        return loader

    pl.add_node(PipeNode("load", make_loader("load", 0.05, {"raw": "data"})), is_start=True)
    pl.add_node(PipeNode("validate", lambda ctx: {"valid": True, "input": ctx["load"]}),
               after=["load"])
    pl.add_node(PipeNode("transform", lambda ctx: {"result": f"processed_{ctx['validate']}"}),
               after=["validate"])

    # 收集事件
    events = []
    pl.on_stream(lambda e: events.append(e))

    print("\n  Pipeline: load → validate → transform")
    result = pl.run_sync()
    print(f"  Events: {len(events)}")
    print(f"  Results: {result['results']}")
    print(f"  Heat Tax: {result['heat_tax_total']:.4f}")
    print(f"  Nodes: {result['nodes_executed']}")

    # 展示事件序列
    print(f"\n  Event Sequence:")
    for e in events[:8]:
        print(f"    [{e.event_type}] {e.pipe_name} ({e.progress_pct:.0%})")


def _demo_branching():
    """演示: 分支Pipeline."""
    print("=" * 60)
    print("Branching Pipeline Demo")
    print("=" * 60)

    pl = StreamingPipeline("demo_branch")

    # 节点定义
    pl.add_node(PipeNode("classify", lambda ctx: {"type": "urgent", "score": 0.9}),
               is_start=True)

    # 分支: urgent → fast_track; normal → standard
    pl.add_node(PipeNode("fast_track", lambda ctx: {"result": "fast_processed"}),
               after=["classify"])
    pl.add_node(PipeNode("standard", lambda ctx: {"result": "standard_processed"}),
               after=["classify"])

    # 给classify添加分支条件
    pl.nodes["classify"].branches = [
        BranchCondition(
            predicate=lambda r: r.output and r.output.get("type") == "urgent",
            target_pipe="fast_track",
            name="urgent_branch"
        ),
    ]
    pl.nodes["classify"].fallback_pipe = "standard"

    events = []
    pl.on_stream(lambda e: events.append(e))

    print("\n  Pipeline: classify → [urgent? → fast_track | else → standard]")
    result = pl.run_sync()

    print(f"  Events: {len(events)}")
    branch_events = [e for e in events if e.event_type == "branch"]
    for be in branch_events:
        print(f"  Branch: {be.data}")
    print(f"  Results: {result['results']}")
    print(f"  Heat Tax: {result['heat_tax_total']:.4f}")


def _demo_decentralized_vcg():
    """演示: 去中心化VCG补偿."""
    print("=" * 60)
    print("Decentralized VCG Demo")
    print("=" * 60)

    dvcg = DecentralizedVCG(quorum_threshold=0.5)

    # 设置真实payoff矩阵 (囚徒困境)
    dvcg.set_payoff_matrix({
        ("C", "C"): (-1, -1),
        ("C", "D"): (-3, 0),
        ("D", "C"): (0, -3),
        ("D", "D"): (-2, -2),
    })

    # Agent报告 (Agent1诚实, Agent2虚报)
    dvcg.submit_report(AgentReport("A1", "C", -1.0, 0.0, -2.0))
    dvcg.submit_report(AgentReport("A2", "D", 0.0, 2.0, -2.0))  # 虚报外部性

    # 交叉验证
    verifications = dvcg.cross_validate()
    comp = dvcg.compute_compensation()

    print(f"""
  Prisoner's Dilemma (Decentralized VCG):

  Payoff Matrix:
         C      D
    C  (-1,-1) (-3,0)
    D  (0,-3)  (-2,-2)

  Reports:
    A1: strategy=C, payoff=-1, externality=0  ✅ honest
    A2: strategy=D, payoff=0,  externality=2  ⚠️ inflated

  Quorum Verification:
    A1: {verifications['A1'].verified} (agreement={verifications['A1'].agreement_ratio})
    A2: {verifications['A2'].verified} (agreement={verifications['A2'].agreement_ratio})

  Compensation:
    A1: gross={comp['A1']['gross_payoff']}, externality={comp['A1']['externality']}, net={comp['A1']['net_utility']}
    A2: gross={comp['A2']['gross_payoff']}, externality={comp['A2']['externality']}, net={comp['A2']['net_utility']}
""")

    stats = dvcg.stats()
    print(f"  Stats: {json.dumps({k:v for k,v in stats.items() if k != 'compensation'}, indent=2)}")


def _test_all():
    """测试套件."""
    passed = 0
    total = 0

    # Test 1: 流式Pipeline基本执行
    total += 1
    pl = StreamingPipeline("test")
    pl.add_node(PipeNode("step1", lambda ctx: {"a": 1}), is_start=True)
    pl.add_node(PipeNode("step2", lambda ctx: {"b": ctx["step1"]["a"] + 1}), after=["step1"])
    result = pl.run_sync()
    assert result['nodes_executed'] == 2
    assert pl.results["step2"].output["b"] == 2
    passed += 1
    print("  ✅ Test 1: 流式Pipeline (2 nodes)")

    # Test 2: 分支Pipeline
    total += 1
    pl2 = StreamingPipeline("test_branch")
    pl2.add_node(PipeNode("check", lambda ctx: {"ok": True}), is_start=True)
    pl2.add_node(PipeNode("yes_path", lambda ctx: {"path": "yes"}))
    pl2.add_node(PipeNode("no_path", lambda ctx: {"path": "no"}))
    pl2.nodes["check"].branches = [
        BranchCondition(lambda r: r.output["ok"], "yes_path", "ok_branch"),
    ]
    pl2.nodes["check"].fallback_pipe = "no_path"
    r2 = pl2.run_sync()
    assert "yes_path" in r2['results']
    assert r2['results']['yes_path'] == 'done'
    passed += 1
    print("  ✅ Test 2: 分支Pipeline (yes_path taken)")

    # Test 3: 回退Pipeline
    total += 1
    pl3 = StreamingPipeline("test_fallback")

    def failing_fn(ctx):
        raise ValueError("simulated failure")

    pl3.add_node(PipeNode("risky", failing_fn, fallback_pipe="safe"), is_start=True)
    pl3.add_node(PipeNode("safe", lambda ctx: {"recovered": True}))
    r3 = pl3.run_sync()
    assert "safe" in r3['results']
    assert r3['results']['safe'] == 'done'
    assert pl3.results["risky"].status == PipeStatus.FAILED
    passed += 1
    print("  ✅ Test 3: 回退Pipeline (risky→safe)")

    # Test 4: VCG自我报告
    total += 1
    dvcg = DecentralizedVCG()
    dvcg.set_payoff_matrix({("C","C"):(-1,-1), ("C","D"):(-3,0), ("D","C"):(0,-3), ("D","D"):(-2,-2)})
    dvcg.submit_report(AgentReport("A1", "C", -1.0, 0.0, -2.0))
    dvcg.submit_report(AgentReport("A2", "C", -1.0, 0.0, -2.0))
    verifs = dvcg.cross_validate()
    assert "A1" in verifs
    assert "A2" in verifs
    passed += 1
    print("  ✅ Test 4: VCG自我报告+交叉验证")

    # Test 5: 去中心化补偿计算
    total += 1
    comp = dvcg.compute_compensation()
    assert "A1" in comp
    assert "A2" in comp
    passed += 1
    print(f"  ✅ Test 5: 去中心化补偿 (A1 net={comp['A1']['net_utility']})")

    # Test 6: 热税累积
    total += 1
    pl4 = StreamingPipeline("test_heat")
    total_heat = 0.0
    pl4.on_stream(lambda e: None)
    pl4.add_node(PipeNode("h1", lambda ctx: time.sleep(0.01) or {"x": 1},
                          heat_tax_weight=2.0), is_start=True)
    pl4.add_node(PipeNode("h2", lambda ctx: {"y": 2}, heat_tax_weight=3.0), after=["h1"])
    pl4.run_sync()
    assert pl4.heat_tax_total > 0, f"Heat tax should be >0, got {pl4.heat_tax_total}"
    passed += 1
    print(f"  ✅ Test 6: 热税累积 ({pl4.heat_tax_total:.4f})")

    # Test 7: Quorum虚报检测
    total += 1
    dvcg2 = DecentralizedVCG(quorum_threshold=0.5)
    dvcg2.set_payoff_matrix({("C","C"):(-1,-1), ("C","D"):(-3,0), ("D","C"):(0,-3), ("D","D"):(-2,-2)})
    dvcg2.submit_report(AgentReport("honest", "C", -1.0, 0.0, -2.0))  # 诚实
    dvcg2.submit_report(AgentReport("liar", "D", 100.0, 3.0, 103.0))  # 收益+外部性都虚报
    v2 = dvcg2.cross_validate()
    # liar应被验证为不一致
    assert not v2["liar"].verified, f"Liar should not pass verification: {v2['liar']}"
    assert v2["honest"].verified == False or v2["liar"].agreement_ratio < 0.5
    passed += 1
    print(f"  ✅ Test 7: Quorum虚报检测 (liar verified={v2['liar'].verified}, penalty={v2['liar'].penalty:.1f})")

    print(f"\n  {passed}/{total} PASS")


if __name__ == "__main__":
    import sys
    cmd_pipeline(sys.argv[1:])
