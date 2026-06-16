"""
mssclaw/core/feedback_evolution.py

生物适应性反馈进化机制 — Biological Adaptive Feedback Evolution.

核心理念:
  生物学隐喻: 突变(Mutation) + 选择(Selection) + 繁殖(Reproduction)
  工程落地: 记录 → 识别模式 → 周期性迭代 → 传播改进

四阶段循环:
  1. RECORD   — 记录每次执行结果 (成功/失败/审计发现)
  2. ANALYZE  — 周期性识别重复失败模式 (自然选择)
  3. ADAPT    — 生成改进策略 (突变)
  4. PROPAGATE — 传播到所有 Agent (繁殖)

Usage:
    evo = FeedbackEvolution()
    evo.record("Code-Agent", task_id, success=True, audit_score=0.95)
    evo.record("Code-Agent", task_id, success=False, audit_score=0.3, 
               issues=["eval detected", "meaning hollowing"])
    # ... after N records ...
    adaptations = evo.analyze_and_adapt()
    for a in adaptations:
        print(f"Agent {a.agent} should: {a.adaptation}")
"""
import json, time, os
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
from typing import Optional


@dataclass
class EvolutionRecord:
    """单次执行记录."""
    agent: str
    task_id: str
    success: bool
    audit_score: float = 0.0
    issues: list = field(default_factory=list)   # ["eval detected", "low quality"]
    patterns: list = field(default_factory=list)  # ["logic_error", "security_risk"]
    timestamp: float = field(default_factory=time.time)
    generation: int = 0  # 进化代际


@dataclass
class Adaptation:
    """进化适应策略."""
    agent: str
    pattern: str           # 重复失败的模式
    frequency: int          # 出现次数
    adaptation: str         # 建议的改进
    severity: str = "warning"  # info/warning/critical
    generation: int = 0


class FeedbackEvolution:
    """生物适应性反馈进化引擎.

    用法:
        evo = FeedbackEvolution()
        # 记录每次执行
        evo.record("Code-Agent", "task_1", True, 0.95)
        # 每 N 条记录后触发进化
        if evo.ready_to_evolve():
            adaptations = evo.analyze_and_adapt()
            for a in adaptations:
                print(f"Adapt: {a.agent} → {a.adaptation}")
    """

    def __init__(self, db_path: str = "data/evolution.json",
                 evolve_every: int = 20,    # 每N条记录触发一次进化
                 mutation_rate: float = 0.3):  # 突变率 (探索新策略比例)
        self._path = Path(db_path)
        self._records: list[EvolutionRecord] = []
        self._adaptations: list[Adaptation] = []
        self._generation = 1
        self._evolve_every = evolve_every
        self._mutation_rate = mutation_rate
        self._pattern_counts: dict[str, int] = defaultdict(int)
        self._load()

    def _load(self):
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._records = [EvolutionRecord(**r) for r in data.get("records", [])]
            self._generation = data.get("generation", 1)
            self._pattern_counts = defaultdict(int, data.get("pattern_counts", {}))

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "generation": self._generation,
            "records": [r.__dict__ for r in self._records],
            "adaptations": [a.__dict__ for a in self._adaptations],
            "pattern_counts": dict(self._pattern_counts),
        }
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ═══ 1. RECORD: 记录 ═══

    def record(self, agent: str, task_id: str, success: bool,
               audit_score: float = 0.0, issues: list = None,
               patterns: list = None):
        """记录一次执行结果."""
        record = EvolutionRecord(
            agent=agent, task_id=task_id, success=success,
            audit_score=audit_score, issues=issues or [],
            patterns=patterns or [], generation=self._generation,
        )
        self._records.append(record)

        # 更新模式计数
        for p in (patterns or []):
            self._pattern_counts[p] += 1

        # 从 issues 中提取模式
        for issue in (issues or []):
            self._pattern_counts[issue] += 1

        self._save()

    # ═══ 2. ANALYZE: 识别模式 ═══

    def ready_to_evolve(self) -> bool:
        """是否应该触发进化."""
        recent = len([r for r in self._records if r.generation == self._generation])
        return recent >= self._evolve_every

    def analyze_and_adapt(self) -> list[Adaptation]:
        """分析失败模式, 生成改进策略."""
        if not self.ready_to_evolve():
            return []

        adaptations = []
        recent = [r for r in self._records if r.generation == self._generation]

        # 按 Agent 分组分析
        by_agent = defaultdict(list)
        for r in recent:
            by_agent[r.agent].append(r)

        for agent, agent_records in by_agent.items():
            failures = [r for r in agent_records if not r.success]
            total = len(agent_records)
            fail_rate = len(failures) / max(total, 1)

            if fail_rate > 0.3:
                # 高失败率: 分析常见模式
                issue_counts = defaultdict(int)
                for f in failures:
                    for issue in f.issues:
                        issue_counts[issue] += 1

                for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1])[:3]:
                    if count >= 2:  # 重复出现 ≥2 次
                        adaptation = self._suggest_adaptation(agent, issue, count)
                        adaptations.append(adaptation)

            # 审计评分趋势
            scores = [r.audit_score for r in agent_records if r.audit_score > 0]
            if len(scores) >= 5:
                avg_score = sum(scores) / len(scores)
                if avg_score < 0.5:
                    adaptations.append(Adaptation(
                        agent=agent, pattern="low_quality_trend",
                        frequency=len(scores),
                        adaptation=f"Audit avg={avg_score:.2f} — increase prompt specificity and add error handling patterns",
                        severity="critical" if avg_score < 0.3 else "warning",
                        generation=self._generation,
                    ))

        self._adaptations.extend(adaptations)
        self._generation += 1
        self._save()
        return adaptations

    def _suggest_adaptation(self, agent: str, issue: str, count: int) -> Adaptation:
        """根据问题模式生成进化策略."""
        adaptations = {
            "eval detected": {
                "adaptation": "Add prompt constraint: 'Do NOT use eval/exec. Use safer alternatives.'",
                "severity": "critical",
            },
            "meaning hollowing": {
                "adaptation": "Add prompt: 'Write substantive, purposeful code with clear logic.'",
                "severity": "warning",
            },
            "low quality": {
                "adaptation": "Increase max_tokens and add 'Write well-documented, tested code' to prompt.",
                "severity": "warning",
            },
            "syntax error": {
                "adaptation": "Enable compile() syntax check before returning. Add 'Ensure code compiles' to prompt.",
                "severity": "critical",
            },
            "logic_contradiction": {
                "adaptation": "Add Chain-of-Thought reasoning step to prompt: 'First explain the logic, then write code.'",
                "severity": "critical",
            },
        }
        default = {"adaptation": f"Investigate '{issue}' pattern. Consider prompt engineering or model switch.",
                   "severity": "warning"}
        rule = adaptations.get(issue, default)
        return Adaptation(agent=agent, pattern=issue, frequency=count,
                         adaptation=rule["adaptation"], severity=rule["severity"],
                         generation=self._generation)

    # ═══ 3. MUTATION: 探索性变异 ═══

    def mutate(self, current_prompt: str) -> str:
        """随机变异提示词 — 探索新策略."""
        import random
        mutations = [
            lambda p: p + "\nIMPORTANT: Write clean, well-documented code.",
            lambda p: p + "\nThink step-by-step before writing code.",
            lambda p: p + "\nFocus on error handling and edge cases.",
            lambda p: p + "\nUse type hints and docstrings.",
            lambda p: p.replace("Return ONLY the code", "Write the code with brief comments"),
        ]
        if random.random() < self._mutation_rate:
            return random.choice(mutations)(current_prompt)
        return current_prompt

    # ═══ 4. STATUS ═══

    def status(self) -> dict:
        return {
            "generation": self._generation,
            "total_records": len(self._records),
            "total_adaptations": len(self._adaptations),
            "ready_to_evolve": self.ready_to_evolve(),
            "top_patterns": sorted(self._pattern_counts.items(), key=lambda x: -x[1])[:5],
            "latest_adaptations": [a.__dict__ for a in self._adaptations[-5:]],
        }

    # ═══ 5. EVOLUTION BRIDGE — 连接 L2 反馈环 ═══

    def trigger_evolution(self, agents: dict = None) -> list:
        """触发一次完整进化循环: 分析 → 适应 → 推送.

        Args:
            agents: {agent_name: agent_instance} 字典, agent 需有 receive_adaptation() 方法
        Returns:
            本次产出的 Adaptation 列表
        """
        if not self.ready_to_evolve():
            return []

        adaptations = self.analyze_and_adapt()
        if not adaptations:
            return []

        # 推送到注册的 agents
        if agents:
            for agent_name, agent in agents.items():
                if hasattr(agent, 'receive_adaptation'):
                    applied = agent.receive_adaptation(adaptations)
                    if applied > 0:
                        self._log(f"Pushed {applied} adaptations to {agent_name}")

        return adaptations

    def _log(self, msg: str) -> None:
        """内部日志."""
        if not hasattr(self, '_log_entries'):
            self._log_entries: list = []
        self._log_entries.append({"time": time.time(), "msg": msg})


class EvolutionBridge:
    """演化桥接器 — 连接 FeedbackEvolution 到所有 Agent.

    定期触发 analyze_and_adapt() 并将 Adaptation 推送到注册的 Agent.
    这是 L2 意义层到 L0 执行层的完整闭环。

    Usage:
        bridge = EvolutionBridge(evo_engine)
        bridge.register_agent("Code-Agent", code_agent)
        bridge.register_agent("Plan-Agent", plan_agent)
        bridge.tick()  # 每次任务后调用, 自动判断是否触发演化
    """

    def __init__(self, evolution_engine: FeedbackEvolution = None, 
                 min_interval_seconds: float = 300):
        self.evo = evolution_engine or FeedbackEvolution()
        self.agents: dict = {}
        self.min_interval = min_interval_seconds
        self._last_evolution: float = 0
        self._tick_count: int = 0

    def register_agent(self, name: str, agent) -> None:
        """注册一个 Agent 到演化桥."""
        self.agents[name] = agent

    def tick(self) -> int:
        """每次任务后调用. 自动判断是否触发演化. 返回 applied 数."""
        self._tick_count += 1

        # 每 N 个 tick 或超过 min_interval 秒触发
        now = time.time()
        if (self._tick_count % 10 == 0 or 
            (now - self._last_evolution) > self.min_interval):
            if self.evo.ready_to_evolve():
                adaptations = self.evo.trigger_evolution(self.agents)
                self._last_evolution = now
                return len(adaptations)

        return 0

    def status(self) -> dict:
        return {
            "agents_registered": len(self.agents),
            "ticks": self._tick_count,
            "last_evolution": self._last_evolution,
            "evo_status": self.evo.status(),
        }
