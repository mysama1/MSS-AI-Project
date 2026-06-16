"""
可观测性系统 — 对标 LangGraph Tracing + Anthropic 全链路审计.

四大组件:
  1. TraceManager: 全链路 JSON 追踪 (每个 Message 完整生命周期)
  2. DecisionTreeVisualizer: Agent 决策树可视化 (Graphviz → SVG)
  3. DashboardUpdater: 实时仪表盘数据推送
  4. TombstoneBrowser: 不可变决策日志浏览器

对标:
  LangGraph: LangSmith tracing + time-travel debugging
  Anthropic Research: "必须知道 Agent 为什么做了这个决定"
  CrewAI/AutoGen: 无此机制 (社区坑 7: 调试黑洞)

设计原则:
  - 零外部依赖回退 (Graphviz 可选)
  - 结构化 JSON 日志 (可被任何工具消费)
  - 不可变 Tombstone (写后不可修改)
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


# ════════════════════════════════════════════════════════════
# 追踪管理器
# ════════════════════════════════════════════════════════════

class SpanStatus(str, Enum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    TIMED_OUT = "timed_out"


@dataclass
class Span:
    """单个追踪跨度 — 一次操作的生命周期"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_id: str = ""             # 父 Span (构建调用树)
    name: str = ""                  # "audit_check" / "task_execute" / "heat_tax_check"
    agent_name: str = ""
    status: SpanStatus = SpanStatus.STARTED
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    error: str = ""
    # 关键数据快照
    input_snapshot: Any = None      # 输入摘要 (截断到 500 字符)
    output_snapshot: Any = None     # 输出摘要
    heat_tax_at_start: float = 0.0
    delta_at_start: float = 1.0

    def finish(self, status: SpanStatus = SpanStatus.SUCCEEDED,
               error: str = "", output: Any = None) -> None:
        self.status = status
        self.ended_at = time.time()
        self.duration_ms = round((self.ended_at - self.started_at) * 1000, 2)
        self.error = error
        if output is not None:
            self.output_snapshot = self._snapshot(output)

    def _snapshot(self, data: Any) -> str:
        """截断数据快照"""
        try:
            s = json.dumps(data, ensure_ascii=False, default=str)
            return s[:500] + ("..." if len(s) > 500 else "")
        except Exception:
            return str(data)[:500]


class TraceManager:
    """
    全链路追踪管理器.

    使用:
        trace = TraceManager()
        span = trace.start_span("audit_check", agent="AUDIT")
        # ... do work ...
        trace.finish_span(span.id, status=SpanStatus.SUCCEEDED, output=result)
        trace.export("trace.json")
    """

    def __init__(self, max_spans: int = 10000):
        self._spans: dict[str, Span] = {}
        self._root_spans: list[str] = []  # 顶层 Span IDs
        self._lock = threading.Lock()
        self.max_spans = max_spans
        self._export_dir = ""

    def start_span(self, name: str, agent_name: str = "",
                   parent_id: str = "", metadata: dict = None,
                   tags: list[str] = None,
                   heat_tax: float = 0.0, delta: float = 1.0,
                   input_data: Any = None) -> Span:
        """开始一个新的追踪跨度"""
        span = Span(
            name=name,
            agent_name=agent_name,
            parent_id=parent_id or "root",
            metadata=metadata or {},
            tags=tags or [],
            heat_tax_at_start=heat_tax,
            delta_at_start=delta,
        )
        if input_data is not None:
            span.input_snapshot = span._snapshot(input_data)

        with self._lock:
            self._spans[span.id] = span
            if not parent_id:
                self._root_spans.append(span.id)

            # 自动清理
            if len(self._spans) > self.max_spans:
                oldest = sorted(self._spans.keys())[:1000]
                for k in oldest:
                    del self._spans[k]

        return span

    def finish_span(self, span_id: str, status: SpanStatus = SpanStatus.SUCCEEDED,
                    error: str = "", output: Any = None) -> Optional[Span]:
        """结束一个追踪跨度"""
        with self._lock:
            span = self._spans.get(span_id)
            if span:
                span.finish(status, error, output)
        return span

    def get_span(self, span_id: str) -> Optional[Span]:
        return self._spans.get(span_id)

    def get_span_tree(self) -> list[dict]:
        """获取调用树"""
        result = []
        for root_id in self._root_spans:
            root = self._spans.get(root_id)
            if root:
                result.append(self._span_to_dict(root))
        return result

    def _span_to_dict(self, span: Span) -> dict:
        """Span → 可序列化 dict"""
        children = []
        for s in self._spans.values():
            if s.parent_id == span.id:
                children.append(self._span_to_dict(s))

        d = {
            "id": span.id,
            "name": span.name,
            "agent": span.agent_name,
            "status": span.status.value,
            "duration_ms": span.duration_ms,
            "started_at": span.started_at,
            "tags": span.tags,
            "metadata": span.metadata,
            "error": span.error,
            "heat_tax": span.heat_tax_at_start,
            "delta": span.delta_at_start,
        }
        if children:
            d["children"] = children
        return d

    def get_stats(self) -> dict:
        """追踪统计"""
        with self._lock:
            spans = list(self._spans.values())

        if not spans:
            return {"total": 0}

        by_status = {}
        total_duration = 0.0
        for s in spans:
            by_status[s.status.value] = by_status.get(s.status.value, 0) + 1
            total_duration += s.duration_ms

        failed = by_status.get("failed", 0)
        return {
            "total": len(spans),
            "by_status": by_status,
            "total_duration_ms": round(total_duration, 2),
            "avg_duration_ms": round(total_duration / max(len(spans), 1), 2),
            "error_rate": round(failed / max(len(spans), 1), 4),
            "root_spans": len(self._root_spans),
        }

    def search(self, agent_name: str = "", status: str = "",
               tag: str = "", limit: int = 50) -> list[dict]:
        """搜索 Span"""
        results = []
        with self._lock:
            for s in self._spans.values():
                if agent_name and s.agent_name != agent_name:
                    continue
                if status and s.status.value != status:
                    continue
                if tag and tag not in s.tags:
                    continue
                results.append({
                    "id": s.id, "name": s.name, "agent": s.agent_name,
                    "status": s.status.value, "duration_ms": s.duration_ms,
                    "error": s.error, "tags": s.tags,
                })
        return results[-limit:]

    def export(self, path: str = "") -> str:
        """导出全链路追踪到 JSON 文件"""
        if not path:
            path = os.path.join(self._export_dir or ".", f"trace_{int(time.time())}.json")

        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "stats": self.get_stats(),
            "tree": self.get_span_tree(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return path

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()
            self._root_spans.clear()


# ════════════════════════════════════════════════════════════
# 决策树可视化
# ════════════════════════════════════════════════════════════

class DecisionTreeVisualizer:
    """
    Agent 决策树 → Graphviz DOT → SVG.

    使用:
        viz = DecisionTreeVisualizer(trace_manager)
        dot = viz.build_dot()
        viz.render("decisions.svg")
    """

    def __init__(self, trace_manager: TraceManager = None):
        self.trace = trace_manager
        self.node_colors = {
            SpanStatus.STARTED: "#FFD700",     # 金色
            SpanStatus.SUCCEEDED: "#4CAF50",   # 绿色
            SpanStatus.FAILED: "#F44336",      # 红色
            SpanStatus.INTERRUPTED: "#FF9800", # 橙色
            SpanStatus.TIMED_OUT: "#9E9E9E",   # 灰色
        }

    def build_dot(self, title: str = "MSSclaw Decision Tree") -> str:
        """构建 Graphviz DOT 字符串"""
        lines = ['digraph MSSclaw {']
        lines.append(f'  label="{title}";')
        lines.append('  labelloc=t;')
        lines.append('  fontsize=14;')
        lines.append('  rankdir=TB;')
        lines.append('  node [shape=box, style=rounded, fontname="Arial"];')

        if not self.trace:
            lines.append('  "empty" [label="No trace data", color=gray];')
            lines.append('}')
            return '\n'.join(lines)

        spans = list(self.trace._spans.values())

        # Group by agent
        agents = {}
        for s in spans:
            agents.setdefault(s.agent_name or "unknown", []).append(s)

        # Subgraph per agent
        for agent_name, agent_spans in agents.items():
            lines.append(f'  subgraph cluster_{agent_name} {{')
            lines.append(f'    label="{agent_name}";')
            lines.append(f'    style=filled;')
            lines.append(f'    color=lightgrey;')

            for s in agent_spans:
                color = self.node_colors.get(s.status, "#CCCCCC")
                label = f"{s.name}\\n{s.duration_ms}ms"
                if s.error:
                    label += f"\\n⚠️ {s.error[:30]}"
                lines.append(
                    f'    "{s.id}" [label="{label}", fillcolor="{color}", style="filled"];'
                )

            lines.append('  }')

        # Edges
        for s in spans:
            if s.parent_id and s.parent_id != "root":
                if s.parent_id in self.trace._spans:
                    style = "dashed" if s.status == SpanStatus.FAILED else "solid"
                    color = "#F44336" if s.status == SpanStatus.FAILED else "#333333"
                    lines.append(
                        f'  "{s.parent_id}" -> "{s.id}" [style={style}, color="{color}"];'
                    )

        lines.append('}')
        return '\n'.join(lines)

    def render(self, output_path: str = "decisions.svg", fmt: str = "svg") -> bool:
        """渲染为图片 (需要安装 graphviz)"""
        dot = self.build_dot()

        try:
            import subprocess
            result = subprocess.run(
                ["dot", f"-T{fmt}", "-o", output_path],
                input=dot, text=True, capture_output=True, timeout=10,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, Exception):
            # Graphviz 不可用 → 保存 DOT 文件
            dot_path = output_path.rsplit(".", 1)[0] + ".dot"
            with open(dot_path, "w", encoding="utf-8") as f:
                f.write(dot)
            print(f"[VIZ] Graphviz not available. DOT saved to {dot_path}")
        return False

    def to_ascii_tree(self) -> str:
        """无 Graphviz 回退: ASCII 决策树"""
        if not self.trace or not self.trace._root_spans:
            return "(empty)"

        lines = ["MSSclaw Decision Tree:"]
        for root_id in self.trace._root_spans:
            root = self.trace._spans.get(root_id)
            if root:
                self._ascii_recurse(root, "", lines)
        return "\n".join(lines)

    def _ascii_recurse(self, span: Span, prefix: str, lines: list) -> None:
        icon = {
            SpanStatus.SUCCEEDED: "✅", SpanStatus.FAILED: "❌",
            SpanStatus.INTERRUPTED: "⏸️", SpanStatus.TIMED_OUT: "⏰",
            SpanStatus.STARTED: "🔄",
        }.get(span.status, "⬜")

        lines.append(f"{prefix}{icon} [{span.agent_name}] {span.name} ({span.duration_ms}ms)")

        children = [s for s in self.trace._spans.values() if s.parent_id == span.id]
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "  └─ " if is_last else "  ├─ "
            child_prefix = prefix + ("   " if is_last else "  │")
            self._ascii_recurse(child, prefix + connector, lines)


# ════════════════════════════════════════════════════════════
# 仪表盘实时更新
# ════════════════════════════════════════════════════════════

@dataclass
class DashboardState:
    """仪表盘状态快照"""
    timestamp: float = field(default_factory=time.time)
    agents_online: int = 0
    agents_total: int = 0
    tasks_total: int = 0
    tasks_active: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    heat_tax_total: float = 0.0
    heat_tax_l2_ratio: float = 0.0
    delta_avg: float = 1.0
    delta_min: float = 1.0
    norm_alerts: int = 0
    audit_pass_rate: float = 1.0
    interrupts_pending: int = 0
    fuse_events: int = 0
    messages_total: int = 0
    errors_last_minute: int = 0
    throughput_msg_per_sec: float = 0.0


class DashboardUpdater:
    """
    实时仪表盘数据推送.

    不渲染 UI (留给 GitHub Pages / HTML)，只提供数据。
    对标 Dify 拖拽可视化 → 转换为 API 的思路。
    """

    def __init__(self, update_interval: float = 5.0):
        self.state = DashboardState()
        self.history: list[DashboardState] = []
        self.max_history = 720  # 1小时 @ 5s 间隔
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._collectors: dict[str, Callable[[], dict]] = {}  # name → 数据采集函数

    def register_collector(self, name: str, fn: Callable[[], dict]) -> None:
        """注册数据采集器 (agents/swarm/audit 各自提供自己的状态)"""
        self._collectors[name] = fn

    def collect(self) -> DashboardState:
        """从所有采集器收集当前状态"""
        state = DashboardState()

        all_data = {}
        for name, fn in self._collectors.items():
            try:
                all_data[name] = fn()
            except Exception:
                all_data[name] = {"error": "collector_failed"}

        # 从采集器数据中提取指标
        # (接口模式: 各采集器返回标准格式 dict)
        for data in all_data.values():
            if "agents_online" in data:
                state.agents_online = max(state.agents_online, data["agents_online"])
            if "agents_total" in data:
                state.agents_total = max(state.agents_total, data["agents_total"])
            if "tasks_total" in data:
                state.tasks_total += data.get("tasks_total", 0)
            if "tasks_active" in data:
                state.tasks_active += data.get("tasks_active", 0)
            if "tasks_completed" in data:
                state.tasks_completed += data.get("tasks_completed", 0)
            if "tasks_failed" in data:
                state.tasks_failed += data.get("tasks_failed", 0)
            if "messages_total" in data:
                state.messages_total += data.get("messages_total", 0)

        # 历史
        prev_messages = self.history[-1].messages_total if self.history else 0
        if prev_messages:
            state.throughput_msg_per_sec = round(
                (state.messages_total - prev_messages) / 5.0, 2
            )

        with self._lock:
            self.state = state
            self.history.append(state)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

        return state

    def start(self) -> None:
        """启动后台采集"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            self.collect()
            time.sleep(5.0)

    def get_snapshot(self) -> dict:
        """获取当前仪表盘快照"""
        return {
            "timestamp": self.state.timestamp,
            "agents": {
                "online": self.state.agents_online,
                "total": self.state.agents_total,
            },
            "tasks": {
                "total": self.state.tasks_total,
                "active": self.state.tasks_active,
                "completed": self.state.tasks_completed,
                "failed": self.state.tasks_failed,
            },
            "heat_tax": {
                "total": round(self.state.heat_tax_total, 4),
                "l2_ratio": round(self.state.heat_tax_l2_ratio, 3),
            },
            "delta": {
                "avg": round(self.state.delta_avg, 3),
                "min": round(self.state.delta_min, 3),
            },
            "safety": {
                "norm_alerts": self.state.norm_alerts,
                "audit_pass_rate": round(self.state.audit_pass_rate, 3),
                "interrupts_pending": self.state.interrupts_pending,
                "fuse_events": self.state.fuse_events,
            },
            "performance": {
                "messages_total": self.state.messages_total,
                "errors_per_min": self.state.errors_last_minute,
                "throughput_msg_s": self.state.throughput_msg_per_sec,
            },
        }

    def get_timeseries(self, metric: str = "tasks_completed",
                       n: int = 60) -> list[tuple[float, float]]:
        """获取指标时间序列 (用于图表)"""
        return [
            (s.timestamp, getattr(s, metric, 0))
            for s in self.history[-n:]
        ]


# ════════════════════════════════════════════════════════════
# Tombstone 浏览器
# ════════════════════════════════════════════════════════════

@dataclass
class TombstoneEntry:
    """单条不可变决策日志"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    agent_name: str = ""
    decision_type: str = ""          # "task_accept" / "task_reject" / "audit_verdict" / "fuse_trip"
    context: dict = field(default_factory=dict)
    decision: dict = field(default_factory=dict)
    reason: str = ""
    heat_tax_at_time: float = 0.0
    delta_at_time: float = 1.0


class TombstoneBrowser:
    """
    不可变决策日志浏览器.

    每条决策写入后不可修改 — 完整的审计链。
    对标: 区块链的 finality 概念 + Anthropic 的 "必须知道为什么"。
    """

    def __init__(self, store_dir: str = ""):
        self.store_dir = store_dir or os.path.join(
            os.path.dirname(__file__), "..", "data", "tombstones"
        )
        os.makedirs(self.store_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: list[TombstoneEntry] = []

    def _log_path(self) -> str:
        return os.path.join(self.store_dir, f"tombstones_{datetime.now().strftime('%Y%m%d')}.jsonl")

    def record(self, agent_name: str, decision_type: str,
               decision: dict, reason: str = "",
               context: dict = None,
               heat_tax: float = 0.0, delta: float = 1.0) -> TombstoneEntry:
        """记录一条决策 — 写入后不可修改"""
        entry = TombstoneEntry(
            agent_name=agent_name,
            decision_type=decision_type,
            context=context or {},
            decision=decision,
            reason=reason,
            heat_tax_at_time=heat_tax,
            delta_at_time=delta,
        )

        with self._lock:
            with open(self._log_path(), "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "id": entry.id,
                    "timestamp": entry.timestamp,
                    "agent": entry.agent_name,
                    "type": entry.decision_type,
                    "context": entry.context,
                    "decision": entry.decision,
                    "reason": entry.reason,
                    "heat_tax": entry.heat_tax_at_time,
                    "delta": entry.delta_at_time,
                }, ensure_ascii=False, default=str) + "\n")

            self._cache.append(entry)
            if len(self._cache) > 1000:
                self._cache = self._cache[-1000:]

        return entry

    def search(self, agent_name: str = "", decision_type: str = "",
               keyword: str = "", limit: int = 50) -> list[dict]:
        """搜索决策日志"""
        results = []

        # Search cache first
        for e in self._cache:
            if agent_name and e.agent_name != agent_name:
                continue
            if decision_type and e.decision_type != decision_type:
                continue
            if keyword:
                reason_match = keyword.lower() in e.reason.lower()
                decision_match = keyword.lower() in json.dumps(e.decision, ensure_ascii=False).lower()
                if not (reason_match or decision_match):
                    continue
            results.append(self._to_dict(e))

        # If cache insufficient, search files
        if len(results) < limit:
            results.extend(self._search_files(agent_name, decision_type, keyword, limit - len(results)))

        return results[-limit:]

    def _search_files(self, agent_name: str, decision_type: str,
                      keyword: str, limit: int) -> list[dict]:
        """搜索日志文件"""
        results = []
        today = datetime.now().strftime('%Y%m%d')

        for fname in sorted(os.listdir(self.store_dir), reverse=True):
            if not fname.endswith(".jsonl"):
                continue
            fpath = os.path.join(self.store_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        if len(results) >= limit:
                            break
                        e = json.loads(line)
                        if agent_name and e.get("agent") != agent_name:
                            continue
                        if decision_type and e.get("type") != decision_type:
                            continue
                        if keyword:
                            reason = e.get("reason", "")
                            decision = json.dumps(e.get("decision", {}), ensure_ascii=False)
                            if keyword.lower() not in reason.lower() and keyword.lower() not in decision.lower():
                                continue
                        results.append(e)
            except Exception:
                continue
            if len(results) >= limit:
                break

        return results

    def get_recent(self, n: int = 20) -> list[dict]:
        """获取最近的决策"""
        return self.search(limit=n)

    def get_agent_decisions(self, agent_name: str, n: int = 50) -> list[dict]:
        """获取指定 Agent 的决策"""
        return self.search(agent_name=agent_name, limit=n)

    def stats(self) -> dict:
        """决策统计"""
        by_type = {}
        by_agent = {}
        recent = self.get_recent(100)
        for e in recent:
            t = e.get("type", "unknown")
            a = e.get("agent", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            by_agent[a] = by_agent.get(a, 0) + 1

        return {
            "total_recent": len(recent),
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
            "by_agent": dict(sorted(by_agent.items(), key=lambda x: -x[1])),
        }

    def _to_dict(self, entry: TombstoneEntry) -> dict:
        return {
            "id": entry.id,
            "timestamp": entry.timestamp,
            "agent": entry.agent_name,
            "type": entry.decision_type,
            "context": entry.context,
            "decision": entry.decision,
            "reason": entry.reason,
            "heat_tax": entry.heat_tax_at_time,
            "delta": entry.delta_at_time,
        }


# ── 方便函数 ──

def create_observability_stack(trace_dir: str = "", tombstone_dir: str = "") -> dict:
    """创建完整的可观测性栈"""
    trace = TraceManager()
    viz = DecisionTreeVisualizer(trace)
    dashboard = DashboardUpdater()
    tombstones = TombstoneBrowser(tombstone_dir)
    exporter = OTLPExporter(trace) if OTLPExporter is not None else None

    return {
        "trace": trace,
        "visualizer": viz,
        "dashboard": dashboard,
        "tombstones": tombstones,
        "exporter": exporter,
    }


# ════════════════════════════════════════════════════════════
# OpenTelemetry 导出器 — 对标 LangSmith OTLP 标准
# ════════════════════════════════════════════════════════════

class OTLPExporter:
    """OTLP (OpenTelemetry Protocol) 导出器.

    将 MSSclaw Trace/Span 转换为 OpenTelemetry 兼容格式,
    无外部依赖 — 纯 JSON over HTTP/JSON 输出.
    对接: Jaeger / Grafana Tempo / SigNoz / OpenTelemetry Collector.

    Usage:
        exporter = OTLPExporter(trace_manager)
        # 每个 Span 结束即推送
        exporter.push_span(span)
        # 或批量导出全量 traces
        exporter.export_all()
    """

    # OTLP/JSON 格式版本
    OTLP_JSON_VERSION = "1.0.0"
    SERVICE_NAME = "mssclaw-agent"

    def __init__(self, trace_manager: TraceManager = None,
                 endpoint: str = "",
                 export_dir: str = ""):
        self.trace = trace_manager or TraceManager()
        self.endpoint = endpoint  # OTLP Collector endpoint
        self.export_dir = export_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "otel_export"
        )
        self._sent_count: int = 0
        self._spans: list[dict] = []

    def span_to_otlp(self, span: Span) -> dict:
        """将 MSSclaw Span 转换为 OTLP/JSON ResourceSpan."""
        import datetime as _dt
        # started_at 是 float Unix timestamp
        started_ts = span.started_at if isinstance(span.started_at, (int, float)) else time.time()
        ended_ts = span.ended_at if span.ended_at else started_ts
        started_ns = int(started_ts * 1_000_000_000)
        ended_ns = int(ended_ts * 1_000_000_000)
        span_id = str(span.id)[:16].ljust(16, '0')
        trace_id = (span.parent_id or str(span.id)).ljust(32, '0')[:32]
        parent = span.parent_id[:16].ljust(16, '0') if span.parent_id else ""

        attrs = [
            {"key": "service.name", "value": {"stringValue": self.SERVICE_NAME}},
            {"key": "span.status", "value": {"stringValue": span.status.value}},
            {"key": "span.name", "value": {"stringValue": span.name}},
            {"key": "agent", "value": {"stringValue": span.agent_name}},
            {"key": "duration_ms", "value": {"doubleValue": span.duration_ms}},
            {"key": "heat_tax", "value": {"doubleValue": span.heat_tax_at_start}},
            {"key": "delta", "value": {"doubleValue": span.delta_at_start}},
        ]
        if span.error:
            attrs.append({"key": "error", "value": {"stringValue": span.error[:256]}})
        for k, v in (span.metadata or {}).items():
            attrs.append({"key": str(k), "value": {"stringValue": str(v)[:256]}})

        return {
            "resourceSpans": [{
                "resource": {"attributes": [
                    {"key": "service.name", "value": {"stringValue": self.SERVICE_NAME}},
                ]},
                "scopeSpans": [{
                    "scope": {"name": span.name, "version": "1.0"},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "parentSpanId": parent,
                        "name": span.name,
                        "kind": 1,
                        "startTimeUnixNano": str(started_ns),
                        "endTimeUnixNano": str(ended_ns),
                        "attributes": attrs,
                        "status": {
                            "code": 1 if span.status in (SpanStatus.SUCCEEDED, SpanStatus.STARTED) else 2
                        },
                    }]
                }]
            }]
        }

    @staticmethod
    def _iso_to_nano(iso_str: str) -> int:
        """ISO timestamp → Unix nanoseconds."""
        try:
            dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
            return int(dt.timestamp() * 1_000_000_000)
        except Exception:
            return int(time.time() * 1_000_000_000)

    def push_span(self, span: Span) -> None:
        """推送单个 Span 到缓冲."""
        otlp_data = self.span_to_otlp(span)
        self._spans.append(otlp_data)
        self._sent_count += 1
        if len(self._spans) >= 50:
            self.flush()

    def export_all(self) -> int:
        """导出所有 traces 为 OTLP/JSON."""
        spans_data = []
        for span in self.trace.get_all_spans():
            spans_data.append(self.span_to_otlp(span))
        return self._write_export(spans_data)

    def flush(self) -> int:
        """冲刷缓冲到磁盘."""
        count = self._write_export(self._spans)
        self._spans.clear()
        return count

    def _write_export(self, spans_data: list) -> int:
        if not spans_data:
            return 0
        os.makedirs(self.export_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        fname = f"otel_spans_{ts}_{uuid.uuid4().hex[:6]}.json"
        fpath = os.path.join(self.export_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump({"resourceSpans": [s["resourceSpans"][0] for s in spans_data]}, f, indent=2)
        return len(spans_data)

    @property
    def buffered(self) -> int:
        return len(self._spans)
