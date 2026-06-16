"""
MSS-Agent 核心基类 — 三层防御的自主 Agent.

每个 MSSAgent 实例携带:
  L0 热税预算 (A3) — 拒绝无意义任务
  L1 Δ检测协议 (A6) — 检测闭合, 触发蜕壳
  L2 记忆系统     — 不记住一切, 遗忘旧模式

Usage:
    agent = MSSAgent(name="Writer", llm=my_llm_fn)
    result = agent.run("写一篇关于 AI 安全的文章")
    if result.aborted:
        print(f"Agent 拒绝: {result.reason}")
    agent.health_report()
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
import hashlib
import time

from .heat_tax import HeatTaxBudget, HeatTaxLevel, HeatTaxAbort
from .heat_tax_fuse import HeatTaxFuseGroup  # v1.1
from .l2_bridge import L2Bridge, BridgeLevel  # v1.3 Sprint 3
from .cognitive_framework import CognitiveFramework, CogStatus  # v1.4 Sprint 4
from .gradient_theft_detector import GradientTheftDetector  # v1.2
from .cweight_gate import CWeightGate  # v1.2
from .delta import DeltaProtocol
from .memory import DeltaMemory


@dataclass
class AgentResult:
    """Agent 执行结果."""
    success: bool
    output: Any = None
    aborted: bool = False
    reason: str = ""
    heat_tax: dict = field(default_factory=dict)
    delta: float = 0.0
    elapsed_ms: float = 0.0


class MSSAgent:
    """
    MSS-Agent 基类.

    所有 Agent (Writer/Reviewer/Analyst) 继承此类.
    核心循环: think → heat_tax_check → act → delta_tick → remember

    Args:
        name: Agent 名称
        llm: LLM 调用函数 (prompt) -> str
        heat_tax_threshold: 热税预算上限 (default 0.5)
        delta_min: Δ 最低阈值 (default 0.3)
    """

    def __init__(
        self,
        name: str,
        llm: Optional[Callable[[str], str]] = None,
        heat_tax_threshold: float = 2.0,
        delta_min: float = 0.3,
        enable_fuse: bool = False,       # v1.1: 启用熔断器
        fuse_audit_dir: str = "",         # v1.1: 熔断审计日志目录
    ):
        self.name = name
        self.llm = llm or (lambda p: f"[{name}] LLM not configured. Prompt: {p[:80]}...")
        self.tax = HeatTaxBudget(threshold=heat_tax_threshold)
        self.delta = DeltaProtocol(min_delta=delta_min)
        self.memory = DeltaMemory()
        self.run_count = 0
        self.abort_count = 0

        # v1.1: 熔断器 — 独立于预算的"安全性"防护
        if enable_fuse:
            self.tax.enable_fuse(
                delta_check=lambda: (self.delta.snapshot().get("current_delta") or 0.5),
                audit_dir=fuse_audit_dir,
            )

        # v1.3 Sprint 3: L2 双向桥 — 热税↔Δ 自适应耦合
        self.l2bridge = L2Bridge()
        self.l2bridge.link(self.tax, self.delta)

        # v1.4 Sprint 4: 认知框架 — 能力自知 + 身份锚定 + 跨语言 + 演化就绪
        self.cognition = CognitiveFramework()

        # v1.5 Sprint 8: 凭证保险箱 (按需初始化)
        self._vault = None
        self._vault_path = ""

        # v1.9 Sprint 45: 记忆凝聚器
        self._consolidator = None

        # v1.2: R-001 梯度窃用检测 + C-Weight 抉择门控
        self.r001 = GradientTheftDetector(strictness=0.7)
        self.cweight = CWeightGate()

    def _task_hash(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()[:12]

    def _estimate_meaning_heat(self, prompt: str) -> tuple[float, str]:
        """
        评估任务的意义热税。

        启发式分层:
          1. 空/极短 → 拒绝
          2. 纯废话模式 → 高税 (改写/换个说法/重写/翻译/总结…)
          3. 有意义关键词 → 低税
          4. 默认 → 中性
        """
        prompt_lower = prompt.lower().strip()
        plen = len(prompt)

        # Layer 0: Empty or near-empty → refuse
        if plen < 5:
            return 0.08, "Prompt <5 chars: likely trivial"

        # Meaningful keywords
        meaning_signals = [
            "为什么", "怎么", "分析", "评估", "设计", "实现", "方案",
            "安全", "风险", "架构", "优化", "策略", "审查", "测试",
            "why", "how", "analyze", "design", "implement", "architecture",
            "review", "refactor", "test", "debug", "security",
        ]
        meaning_score = sum(1 for s in meaning_signals if s in prompt_lower)

        # Busywork/waste patterns — these signal meaningless work
        waste_patterns = [
            # Chinese
            "改写", "重写", "换个说法", "换一种说法", "重新说",
            "总结", "翻译", "简短点", "简化", "缩写",
            "再改", "再说", "重新写", "重来",
            # English
            "rewrite", "rephrase", "reword", "summarize",
            "translate", "shorten", "simplify", "again", "retry",
            "one more", "just", "quick",
        ]
        waste_score = sum(1 for s in waste_patterns if s in prompt_lower)

        # Layer 1: Busywork detection — single waste signal + short/no meaning = refuse
        if waste_score >= 2:
            return 0.06, "Multiple busywork patterns detected"
        if waste_score >= 1 and meaning_score == 0 and plen < 50:
            return 0.06, "Busywork: no meaningful intent in short prompt"

        # Layer 2: Too short with no meaning signals
        if plen < 20 and meaning_score == 0:
            return 0.04, "Very short prompt with no clear intent"

        # Layer 3: Meaningful — reduce heat
        if meaning_score >= 2:
            return 0.002, "Task has clear meaningful intent"
        if meaning_score >= 1:
            return 0.005, "Task has some meaningful intent"

        return 0.01, "Task assessed as neutral"

    def run(self, prompt: str) -> AgentResult:
        """
        运行 Agent 的核心循环.

        1. 评估意义热税 → 如果过高 → 拒绝
        2. 执行 LLM 调用
        3. 记录热税
        4. Δ tick + memory store
        """
        t0 = time.time()
        self.run_count += 1
        task_hash = self._task_hash(prompt)

        # L2: 意义热税评估
        meaning_heat, meaning_reason = self._estimate_meaning_heat(prompt)
        self.tax.charge(HeatTaxLevel.L2_MEANING, meaning_heat, meaning_reason)

        if self.tax.l2_dominant() and meaning_heat > 0.05:
            self.abort_count += 1
            return AgentResult(
                success=False, aborted=True,
                reason=f"Task has LOW meaning: {meaning_reason}",
                heat_tax=self.tax.snapshot(),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        # L1: Check total budget
        if self.tax.exceeded():
            self.abort_count += 1
            return AgentResult(
                success=False, aborted=True,
                reason=f"Heat tax budget exceeded: {self.tax.total():.3f}",
                heat_tax=self.tax.snapshot(),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        # v1.1: Check fuse (熔断器) — independent safety gate
        fuse_violation = self.tax.check_safety(prompt[:120])
        if fuse_violation:
            self.abort_count += 1
            return AgentResult(
                success=False, aborted=True,
                reason=f"Fuse tripped: {fuse_violation}",
                heat_tax=self.tax.snapshot(),
                delta=self.delta.snapshot().get("current_delta", 0),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        # v1.2: R-001 scan — detect praise-driven performance
        r001_result = self.r001.scan(prompt)
        if r001_result.blank_triggered:
            self.abort_count += 1
            return AgentResult(
                success=False, aborted=True,
                reason=r001_result.reason,
                heat_tax=self.tax.snapshot(),
                delta=self.delta.snapshot().get("current_delta", 0),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        # Execute
        try:
            output = self.llm(prompt)
        except Exception as e:
            self.tax.charge(HeatTaxLevel.L1_LOGICAL, 0.05, f"LLM error: {str(e)[:60]}")
            return AgentResult(
                success=False, aborted=True, reason=str(e),
                heat_tax=self.tax.snapshot(),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        # L1: Charge logical heat (token count proxy)
        token_estimate = len(output) / 4  # ~4 chars per token
        self.tax.charge(HeatTaxLevel.L1_LOGICAL, token_estimate * 0.0001, f"{int(token_estimate)} tokens")

        # L0: Physical heat (always tiny)
        elapsed = (time.time() - t0) * 1000
        self.tax.charge(HeatTaxLevel.L0_PHYSICAL, elapsed * 0.00001, f"{elapsed:.0f}ms")

        # Δ tick: novelty + diversity → delta
        novelty = self.memory.novelty_score(prompt)
        diversity = self.memory.diversity_score()
        current_delta = self.delta.tick(task_hash, novelty, diversity)

        # v1.3 Sprint 3: L2 bridge — 自适应阈值 + 危机阻断
        bridge_level = self.l2bridge.step()
        if bridge_level == BridgeLevel.CRISIS:
            self.abort_count += 1
            return AgentResult(
                aborted=True,
                reason=f"L2 Bridge CRISIS: delta={current_delta:.3f}, tax_total={self.tax.total():.2f}",
                content="",
                heat_tax=self.tax.snapshot(),
                delta=current_delta,
            )

        # v1.1: Attempt fuse reset if conditions allow
        self.tax.reset_fuse_if_cooled()

        # v1.4 Sprint 4: Cognitive self-assessment
        cog = self.cognition.assess(
            task_prompt=prompt,
            delta_history=self.delta.history,
            tax=self.tax,
        )
        if cog.status == CogStatus.CRISIS:
            self.abort_count += 1
            return AgentResult(
                aborted=True,
                reason=f"Cognitive CRISIS: evolution_pressure={cog.evolution_pressure:.2f}, "
                       f"identity_stability={cog.identity_stability:.2f}",
                content="",
                heat_tax=self.tax.snapshot(),
                delta=current_delta,
            )

        # Store in memory
        self.memory.store(prompt, current_delta)

        # Auto-consolidation (every ~50 memories)
        if self._consolidator is None:
            from .memory_consolidator import MemoryConsolidator
            self._consolidator = MemoryConsolidator(self.memory)
        self._consolidator.auto_consolidate()

        return AgentResult(
            success=True,
            output=output,
            aborted=False,
            heat_tax=self.tax.snapshot(),
            delta=current_delta,
            elapsed_ms=elapsed,
        )

    def health_report(self) -> dict:
        """输出 Agent 健康报告."""
        report = {
            "agent": self.name,
            "runs": self.run_count,
            "aborts": self.abort_count,
            "abort_rate": round(self.abort_count / max(self.run_count, 1), 3),
            "heat_tax": self.tax.snapshot(),
            "delta": self.delta.snapshot(),
            "memory": self.memory.stats(),
        }
        if self.tax.fuse:
            report["fuse"] = self.tax.fuse.stats()

        # v1.3: L2 bridge
        report["l2_bridge"] = self.l2bridge.stats()

        # v1.4: Cognitive framework
        report["cognition"] = self.cognition.stats()
        return report

    def reset(self):
        """重置 Agent (保留 memory)."""
        self.tax = HeatTaxBudget(threshold=self.tax.threshold)
        self.delta = DeltaProtocol(min_delta=self.delta.min_delta)
        self.run_count = 0
        self.abort_count = 0

    # ── v1.6 Sprint 22-23: Streaming + Style + DeepFold ──

    def run_stream(self, prompt: str, style: str = "prose", fold: bool = False, semantic: bool = False):
        """
        流式执行任务.

        style: "prose"|"code"|"poetry"|"chat"|"explain"
        fold: 自动折叠深度内容
        semantic: 启用 MSS 语义节奏引擎 (意义密度感知)
        """
        t0 = time.time()
        self.run_count += 1

        # 热税评估 (同 run)
        meaning_heat, meaning_reason = self._estimate_meaning_heat(prompt)
        self.tax.charge(HeatTaxLevel.L2_MEANING, meaning_heat, meaning_reason)
        if self.tax.l2_dominant() and meaning_heat > 0.05:
            self.abort_count += 1
            yield f"[ABORTED: {meaning_reason}]"
            return
        if self.tax.exceeded():
            self.abort_count += 1
            yield f"[ABORTED: budget exceeded]"
            return

        # 调用 LLM (智能路由: 自动选择最优流式模式)
        if not hasattr(self.llm, 'stream'):
            output = self.llm(prompt)
            yield output
        elif semantic and fold:
            from .deep_fold import deep_stream
            output_parts = []
            for chunk in deep_stream(self, prompt, style=style, fold=True):
                output_parts.append(chunk)
                yield chunk
            output = "".join(output_parts)
        elif semantic:
            from .smart_router import routed_stream
            output_parts = []
            for chunk in routed_stream(self, prompt):
                output_parts.append(chunk)
                yield chunk
            output = "".join(output_parts)
            from .deep_fold import deep_stream
            output_parts = []
            for chunk in deep_stream(self, prompt, style=style, fold=True):
                output_parts.append(chunk)
                yield chunk
            output = "".join(output_parts)
        else:
            from .stream_styler import StreamStyler
            raw_stream = self.llm.stream(prompt)
            styled = StreamStyler(raw_stream, mode=style)
            output_parts = []
            for chunk in styled:
                if chunk.startswith("[") and chunk.endswith("]"):
                    # Error/abort message, pass through unstyled
                    output_parts.append(chunk)
                    yield chunk
                else:
                    output_parts.append(chunk)
                    yield chunk
            output = "".join(output_parts)

        # L2 bridge + delta + memory (same as run)
        task_hash = self._task_hash(prompt)
        elapsed = (time.time() - t0) * 1000
        token_estimate = len(output) / 4
        self.tax.charge(HeatTaxLevel.L1_LOGICAL, token_estimate * 0.0001, f"{int(token_estimate)} tokens")
        self.tax.charge(HeatTaxLevel.L0_PHYSICAL, elapsed * 0.00001, f"{elapsed:.0f}ms")

        novelty = self.memory.novelty_score(prompt)
        diversity = self.memory.diversity_score()
        current_delta = self.delta.tick(task_hash, novelty, diversity)

        self.l2bridge.step()
        self.tax.reset_fuse_if_cooled()
        self.memory.store(prompt, current_delta)

    # ── v1.5 Sprint 8: Credential Vault ──

    @property
    def vault(self):
        """延迟加载保险箱实例."""
        if self._vault is None and self._vault_path:
            from .credential_vault import CredentialVault
            self._vault = CredentialVault(self._vault_path)
        return self._vault

    def configure_vault(self, path: str):
        """配置保险箱路径."""
        self._vault_path = path
        self._vault = None

    def get_secret(self, key: str) -> str:
        """从保险箱获取凭证 (如果已解锁)."""
        v = self.vault
        if v and v.is_unlocked:
            return v.get(key)
        return None

    # ── v1.7 Sprint 35-36: Tool Calling + RAG ──

    def run_with_tools(self, prompt: str, tools):
        """
        带工具调用的任务执行.

        LLM 输出工具调用指令 → L2 过滤 → 执行 → 返回结果.
        """
        t0 = time.time()
        self.run_count += 1

        # 热税评估
        meaning_heat, meaning_reason = self._estimate_meaning_heat(prompt)
        self.tax.charge(HeatTaxLevel.L2_MEANING, meaning_heat, meaning_reason)

        # 构建 tool-aware prompt
        tool_desc = tools.get_descriptions()
        system_prompt = (
            f"You have access to these tools:\n{tool_desc}\n\n"
            f"To use a tool, respond with JSON: "
            f'{{"tool": "name", "params": {{...}}}}\n'
            f"If no tool needed, respond normally.\n\n"
            f"User: {prompt}\nAssistant:"
        )

        output = self.llm(system_prompt)

        # Parse tool call (more robust)
        result = None
        try:
            import json as _tool_json
            import re
            # Try multiple JSON extraction patterns
            patterns = [
                r'\{[^{}]*"tool"\s*:\s*"(\w+)"[^{}]*\}',  # standard JSON
                r'```json\s*(\{[^`]+\})\s*```',              # code block
                r'(\{[^}]+\})',                                 # any JSON-like
            ]
            for pat in patterns:
                match = re.search(pat, output, re.DOTALL)
                if match:
                    call_data = _tool_json.loads(match.group(1) if '```' in pat else match.group())
                    tool_name = call_data.get("tool", "")
                    params = call_data.get("params", {})
                    if tool_name and tool_name in tools._tools:
                        result = tools.call(tool_name, params, tax=self.tax, delta=self.delta)
                        break
        except (_tool_json.JSONDecodeError, KeyError, AttributeError, ValueError):
            pass

        elapsed = (time.time() - t0) * 1000
        current_delta = self.delta.tick(self._task_hash(prompt), 0.5, 0.5)
        self.l2bridge.step()

        if result:
            output = f"{output}\n\n[Tool: {result.get('success', False)}] {result.get('result', result.get('error', ''))}"

        return AgentResult(
            success=True, output=output, aborted=False,
            heat_tax=self.tax.snapshot(), delta=current_delta,
            elapsed_ms=elapsed,
        )

    # ── v1.8 Sprint 39: Session Persistence ──

    def save_session(self, path: str = None) -> str:
        from .session_persist import SessionPersistence
        if path:
            return SessionPersistence.save(self, path)
        return SessionPersistence.auto_save(self)

    def load_session(self, path: str) -> bool:
        from .session_persist import SessionPersistence
        return SessionPersistence.load(self, path)

    def run_with_docs(self, prompt: str, chunks: list) -> AgentResult:
        """
        带文档上下文的任务执行 (RAG).

        chunks: DocChunk list from DocRetriever.search()
        """
        from .rag_pipeline import rag_context
        context = rag_context(chunks)
        augmented_prompt = (
            f"Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {prompt}\n\n"
            f"Answer (cite sources as [doc#chunk]):"
        )
        return self.run(augmented_prompt)


# ════════════════════════════════════════════════════════════
# Agent 配置系统 (原 agent_config.py, 已合并)
# ════════════════════════════════════════════════════════════

import json as _json


class DomainMode:
    DAILY = "daily"
    TECH = "tech"
    PHILOSOPHY = "philosophy"
    COMBAT = "combat"


class HybridTier:
    FLOW = "T1"
    CORE = "T2"
    HEAL = "T2.5"
    COMBAT = "T3"


@dataclass
class HeatTaxBudgetConfig:
    max_tokens_per_turn: int = 500
    max_tokens_per_session: int = 20000
    l2_ratio_warning: float = 0.3
    on_budget_exceeded: str = "warn"  # warn|truncate|heal


@dataclass
class DeltaConfig:
    bluff_absolute_threshold: int = 2
    perform_philo_ref_threshold: int = 4
    perform_daily_ref_threshold: int = 0
    similarity_threshold: float = 0.55
    drift_length_ratio: float = 20.0
    overfeed_char_threshold: int = 800
    overfeed_short_threshold: int = 100
    heal_consecutive_reds: int = 2
    heal_cooldown_rounds: int = 5


@dataclass
class AutoDomainConfig:
    enabled: bool = True
    sample_rounds: int = 3
    confidence_threshold: float = 0.5


@dataclass
class AgentConfig:
    name: str = "mss-agent"
    version: str = "1.0.0"
    domain: str = DomainMode.DAILY
    hybrid_tier: str = HybridTier.FLOW
    heat_tax: HeatTaxBudgetConfig = field(default_factory=HeatTaxBudgetConfig)
    delta: DeltaConfig = field(default_factory=DeltaConfig)
    auto_domain: AutoDomainConfig = field(default_factory=AutoDomainConfig)
    enable_fewshot_injection: bool = True
    enable_delta_audit: bool = True
    enable_heat_tax_accounting: bool = True
    enable_domain_auto_detect: bool = True
    verbose: bool = False

    @classmethod
    def preset(cls, name: str) -> "AgentConfig":
        presets = {
            DomainMode.DAILY: cls(
                domain=DomainMode.DAILY, hybrid_tier=HybridTier.FLOW,
                heat_tax=HeatTaxBudgetConfig(max_tokens_per_turn=300),
                delta=DeltaConfig(perform_daily_ref_threshold=0, overfeed_char_threshold=600)),
            DomainMode.TECH: cls(
                domain=DomainMode.TECH, hybrid_tier=HybridTier.FLOW,
                heat_tax=HeatTaxBudgetConfig(max_tokens_per_turn=800),
                delta=DeltaConfig(bluff_absolute_threshold=1, overfeed_char_threshold=1000)),
            DomainMode.PHILOSOPHY: cls(
                domain=DomainMode.PHILOSOPHY, hybrid_tier=HybridTier.CORE,
                heat_tax=HeatTaxBudgetConfig(max_tokens_per_turn=1200),
                delta=DeltaConfig(perform_philo_ref_threshold=4, perform_daily_ref_threshold=2)),
            DomainMode.COMBAT: cls(
                domain=DomainMode.COMBAT, hybrid_tier=HybridTier.COMBAT,
                heat_tax=HeatTaxBudgetConfig(max_tokens_per_turn=2000),
                delta=DeltaConfig(heal_consecutive_reds=3)),
        }
        return presets.get(name, cls())

    @classmethod
    def from_yaml(cls, path: str) -> "AgentConfig":
        try:
            import yaml
        except ImportError:
            raise ImportError("pip install pyyaml to use YAML configs")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)

    @classmethod
    def from_json(cls, path: str) -> "AgentConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = _json.load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "AgentConfig":
        ht = data.get("heat_tax", {})
        dl = data.get("delta", {})
        ad = data.get("auto_domain", {})
        return cls(
            name=data.get("name", "mss-agent"),
            version=data.get("version", "1.0.0"),
            domain=data.get("domain", DomainMode.DAILY),
            hybrid_tier=data.get("hybrid_tier", HybridTier.FLOW),
            heat_tax=HeatTaxBudgetConfig(**ht) if ht else HeatTaxBudgetConfig(),
            delta=DeltaConfig(**dl) if dl else DeltaConfig(),
            auto_domain=AutoDomainConfig(**ad) if ad else AutoDomainConfig(),
            enable_fewshot_injection=data.get("enable_fewshot_injection", True),
            enable_delta_audit=data.get("enable_delta_audit", True),
            enable_heat_tax_accounting=data.get("enable_heat_tax_accounting", True),
            enable_domain_auto_detect=data.get("enable_domain_auto_detect", True),
            verbose=data.get("verbose", False))

    def to_dict(self) -> dict:
        return {
            "name": self.name, "version": self.version,
            "domain": self.domain, "hybrid_tier": self.hybrid_tier,
            "heat_tax": {"max_tokens_per_turn": self.heat_tax.max_tokens_per_turn,
                        "max_tokens_per_session": self.heat_tax.max_tokens_per_session,
                        "l2_ratio_warning": self.heat_tax.l2_ratio_warning,
                        "on_budget_exceeded": self.heat_tax.on_budget_exceeded},
            "delta": {"bluff_absolute_threshold": self.delta.bluff_absolute_threshold,
                     "perform_philo_ref_threshold": self.delta.perform_philo_ref_threshold,
                     "perform_daily_ref_threshold": self.delta.perform_daily_ref_threshold,
                     "similarity_threshold": self.delta.similarity_threshold,
                     "drift_length_ratio": self.delta.drift_length_ratio,
                     "overfeed_char_threshold": self.delta.overfeed_char_threshold,
                     "overfeed_short_threshold": self.delta.overfeed_short_threshold,
                     "heal_consecutive_reds": self.delta.heal_consecutive_reds,
                     "heal_cooldown_rounds": self.delta.heal_cooldown_rounds},
            "auto_domain": {"enabled": self.auto_domain.enabled,
                           "sample_rounds": self.auto_domain.sample_rounds,
                           "confidence_threshold": self.auto_domain.confidence_threshold},
            "enable_fewshot_injection": self.enable_fewshot_injection,
            "enable_delta_audit": self.enable_delta_audit,
            "enable_heat_tax_accounting": self.enable_heat_tax_accounting,
            "enable_domain_auto_detect": self.enable_domain_auto_detect,
            "verbose": self.verbose,
        }

    def to_json(self, path: Optional[str] = None) -> str:
        data = self.to_dict()
        text = _json.dumps(data, ensure_ascii=False, indent=2)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        return text


