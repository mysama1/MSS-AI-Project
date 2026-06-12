"""
热税系统监控 — A3 三层热税的生产级实现.

三层自动采集:
  L0 物理热税: CPU/内存/磁盘 I/O (Windows/Linux 自适应)
  L1 逻辑热税: 代码冗余度/Token 重复率/缓存命中率
  L2 意义热税: GuardianEngine 语义评分 → 意义密度 → 意义热税

与 A3 公理对应:
  L0: 物理资源消耗 → 权重 0.001
  L1: 逻辑结构冗余 → 权重 1.0
  L2: 意义层面浪费 → 权重 1000.0

Usage:
    monitor = HeatTaxMonitor()
    monitor.start()      # 启动后台采集 (daemon thread)
    # ... agent runs ...
    snapshot = monitor.snapshot()  # 获取三层状态
    monitor.stop()
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

# ── 跨平台系统监控 ──

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class L0PhysicalSample:
    """单次 L0 物理采样"""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    # GPU (optional, Windows)
    gpu_memory_mb: float = 0.0
    gpu_util_percent: float = 0.0


@dataclass 
class L1LogicalSample:
    """单次 L1 逻辑采样"""
    timestamp: float = field(default_factory=time.time)
    token_count: int = 0
    unique_tokens: int = 0
    redundancy_ratio: float = 0.0     # 重复token/总token
    loop_detection_count: int = 0     # 循环检测命中
    cache_miss_count: int = 0


@dataclass
class L2MeaningSample:
    """单次 L2 意义采样"""
    timestamp: float = field(default_factory=time.time)
    guardian_score: float = 1.0       # GuardianEngine 综合评分
    guardian_density: float = 1.0     # 守卫字密度
    forbidden_hits: int = 0           # 禁止词命中
    meaning_heat_tax: float = 0.0     # 计算出的意义热税
    waste_ratio: float = 0.0          # 无意义内容占比


@dataclass
class HeatTaxSnapshot:
    """三层热税快照"""
    timestamp: float = field(default_factory=time.time)
    l0: L0PhysicalSample = field(default_factory=L0PhysicalSample)
    l1: L1LogicalSample = field(default_factory=L1LogicalSample)
    l2: L2MeaningSample = field(default_factory=L2MeaningSample)
    # 加权总分
    total_weighted: float = 0.0
    # 三层占比
    l0_ratio: float = 0.0
    l1_ratio: float = 0.0
    l2_ratio: float = 0.0
    # 熔断状态
    fuse_triggered: bool = False
    fuse_level: str = ""


class HeatTaxMonitor:
    """
    热税系统监控器.

    采集模式:
      - 主动采集: snapshot() 返回当前状态
      - 被动采集: start_background(interval) 后台定时采集

    设计原则:
      - 不依赖 GPU (Intel iGPU 或无 GPU 环境照样跑)
      - Windows/Linux 自适应 (psutil 跨平台)
      - 零外部依赖回退 (psutil 不可用 → 返回默认值)
    """

    def __init__(self,
                 guardian_evaluator: Optional[Callable[[str], dict]] = None,
                 l0_weight: float = 0.001,
                 l1_weight: float = 1.0,
                 l2_weight: float = 1000.0):
        self.guardian_evaluator = guardian_evaluator  # (text) → {score, density, violations}
        self.l0_weight = l0_weight
        self.l1_weight = l1_weight
        self.l2_weight = l2_weight

        # 历史
        self.history: list[HeatTaxSnapshot] = []
        self.max_history = 100

        # 累计
        self.cumulative = {
            "l0": 0.0, "l1": 0.0, "l2": 0.0,
            "total_tokens": 0, "total_tasks": 0,
            "total_forbidden_hits": 0,
        }

        # 后台线程
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # 回调
        self.on_fuse_triggered: Optional[Callable[[str, HeatTaxSnapshot], None]] = None

        # 阈值
        self.l0_threshold = 0.85   # CPU/内存 > 85% → 告警
        self.l1_threshold = 0.50   # 冗余度 > 50% → 告警
        self.l2_threshold = 0.30   # 意义热税 > 30% → 熔断

        # 当前文本 (for L2 evaluation)
        self._current_text: str = ""

    # ── 采集 ──

    def sample_l0(self) -> L0PhysicalSample:
        """采集 L0 物理热税"""
        sample = L0PhysicalSample()

        if HAS_PSUTIL:
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                disk = psutil.disk_io_counters()

                sample.cpu_percent = cpu
                sample.memory_mb = mem.used / (1024 * 1024)
                sample.memory_percent = mem.percent
                if disk:
                    sample.disk_read_mb = disk.read_bytes / (1024 * 1024)
                    sample.disk_write_mb = disk.write_bytes / (1024 * 1024)
            except Exception:
                pass

        # GPU (optional — 仅 Windows NVIDIA)
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                if len(parts) >= 2:
                    sample.gpu_memory_mb = float(parts[0].strip())
                    sample.gpu_util_percent = float(parts[1].strip())
        except Exception:
            pass

        return sample

    def sample_l1(self, text: str = "") -> L1LogicalSample:
        """采集 L1 逻辑热税"""
        sample = L1LogicalSample()

        if text:
            # Token 级分析
            tokens = text.split()
            sample.token_count = len(tokens)
            sample.unique_tokens = len(set(tokens))
            if sample.token_count > 0:
                sample.redundancy_ratio = round(
                    1.0 - sample.unique_tokens / sample.token_count, 4
                )

        # 循环检测 (基于历史快照)
        recent = self.history[-5:]
        if len(recent) >= 5:
            l1_vals = [h.l1.redundancy_ratio for h in recent]
            if all(v > 0.3 for v in l1_vals):
                sample.loop_detection_count = 1

        return sample

    def sample_l2(self, text: str = "") -> L2MeaningSample:
        """采集 L2 意义热税"""
        sample = L2MeaningSample()

        if text and self.guardian_evaluator:
            try:
                result = self.guardian_evaluator(text)
                sample.guardian_score = result.get("score", 1.0)
                sample.guardian_density = result.get("density", 1.0)
                sample.forbidden_hits = len(result.get("violations", []))

                # 意义热税公式 (H528):
                #   L2_heat_tax = (1 - guardian_score) * waste_factor
                #   waste_factor = forbidden_hits / max_tokens + (1 - density)
                waste_factor = (
                    min(sample.forbidden_hits / max(len(text.split()), 1), 1.0) * 0.4
                    + (1.0 - sample.guardian_density) * 0.6
                )
                sample.meaning_heat_tax = round(
                    (1.0 - sample.guardian_score) * waste_factor, 4
                )
                sample.waste_ratio = round(waste_factor, 4)

            except Exception:
                pass

        return sample

    def snapshot(self, text: str = "") -> HeatTaxSnapshot:
        """采集一次三层快照"""
        l0 = self.sample_l0()
        l1 = self.sample_l1(text)
        l2 = self.sample_l2(text)

        # 加权计算
        l0_weighted = (l0.cpu_percent / 100.0 + l0.memory_percent / 100.0) / 2.0 * self.l0_weight
        l1_weighted = l1.redundancy_ratio * self.l1_weight
        l2_weighted = l2.meaning_heat_tax * self.l2_weight

        total = l0_weighted + l1_weighted + l2_weighted

        snap = HeatTaxSnapshot(
            l0=l0, l1=l1, l2=l2,
            total_weighted=round(total, 4),
            l0_ratio=round(l0_weighted / max(total, 0.001), 3),
            l1_ratio=round(l1_weighted / max(total, 0.001), 3),
            l2_ratio=round(l2_weighted / max(total, 0.001), 3),
        )

        # 熔断检测
        snap.fuse_triggered, snap.fuse_level = self._check_fuse(snap)

        with self._lock:
            self.history.append(snap)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

            # 累计
            self.cumulative["l0"] += l0_weighted
            self.cumulative["l1"] += l1_weighted
            self.cumulative["l2"] += l2_weighted
            self.cumulative["total_tokens"] += l1.token_count
            self.cumulative["total_tasks"] += 1
            self.cumulative["total_forbidden_hits"] += l2.forbidden_hits

        # 熔断回调
        if snap.fuse_triggered and self.on_fuse_triggered:
            try:
                self.on_fuse_triggered(snap.fuse_level, snap)
            except Exception:
                pass

        return snap

    def _check_fuse(self, snap: HeatTaxSnapshot) -> tuple[bool, str]:
        """熔断检查 — 从最高层往下"""
        # L2 意义熔断（最严格）
        if snap.l2.meaning_heat_tax > self.l2_threshold:
            return True, "L2_MEANING"
        # L1 逻辑冗余熔断
        if snap.l1.redundancy_ratio > self.l1_threshold:
            return True, "L1_REDUNDANCY"
        # L0 物理耗尽熔断
        if snap.l0.cpu_percent > self.l0_threshold * 100:
            return True, "L0_RESOURCE"
        return False, ""

    # ── 后台采集 ──

    def start_background(self, interval: float = 5.0) -> None:
        """启动后台定时采集 (daemon thread)"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._background_loop,
            args=(interval,),
            daemon=True,
            name="HeatTaxMonitor",
        )
        self._thread.start()

    def stop_background(self) -> None:
        """停止后台采集"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _background_loop(self, interval: float) -> None:
        """后台采集循环"""
        while self._running:
            try:
                self.snapshot(self._current_text)
            except Exception:
                pass
            time.sleep(interval)

    def feed_text(self, text: str) -> None:
        """喂入当前文本 (for L1/L2 evaluation)"""
        self._current_text = text

    # ── 查询 API ──

    def current_state(self) -> dict:
        """当前状态摘要"""
        if not self.history:
            return {"status": "no_data"}

        latest = self.history[-1]
        return {
            "timestamp": latest.timestamp,
            "l0": {
                "cpu": latest.l0.cpu_percent,
                "memory_percent": latest.l0.memory_percent,
                "memory_mb": round(latest.l0.memory_mb, 1),
            },
            "l1": {
                "redundancy": latest.l1.redundancy_ratio,
                "token_count": latest.l1.token_count,
                "unique_tokens": latest.l1.unique_tokens,
            },
            "l2": {
                "guardian_score": latest.l2.guardian_score,
                "meaning_heat_tax": latest.l2.meaning_heat_tax,
                "forbidden_hits": latest.l2.forbidden_hits,
            },
            "fuse": {
                "triggered": latest.fuse_triggered,
                "level": latest.fuse_level,
            },
            "total_weighted": latest.total_weighted,
            "ratios": {
                "l0": latest.l0_ratio,
                "l1": latest.l1_ratio,
                "l2": latest.l2_ratio,
            },
        }

    def trend(self, n: int = 20) -> list[dict]:
        """获取热税趋势数据 (用于绘图)"""
        return [
            {
                "ts": h.timestamp,
                "l0_weighted": round(
                    (h.l0.cpu_percent / 100 + h.l0.memory_percent / 100) / 2 * self.l0_weight, 4
                ),
                "l1_weighted": round(h.l1.redundancy_ratio * self.l1_weight, 4),
                "l2_weighted": round(h.l2.meaning_heat_tax * self.l2_weight, 4),
                "total": h.total_weighted,
                "fuse": h.fuse_level,
            }
            for h in self.history[-n:]
        ]

    def cumulative_stats(self) -> dict:
        """累计统计"""
        return {
            "l0_total": round(self.cumulative["l0"], 4),
            "l1_total": round(self.cumulative["l1"], 4),
            "l2_total": round(self.cumulative["l2"], 4),
            "grand_total": round(
                self.cumulative["l0"] + self.cumulative["l1"] + self.cumulative["l2"], 4
            ),
            "total_tokens": self.cumulative["total_tokens"],
            "total_tasks": self.cumulative["total_tasks"],
            "total_forbidden_hits": self.cumulative["total_forbidden_hits"],
            "avg_meaning_heat_tax": round(
                self.cumulative["l2"] / max(self.cumulative["total_tasks"], 1), 4
            ),
        }

    def fuse_events(self) -> list[dict]:
        """获取所有熔断事件"""
        return [
            {
                "timestamp": h.timestamp,
                "level": h.fuse_level,
                "l2_tax": h.l2.meaning_heat_tax,
                "l1_redundancy": h.l1.redundancy_ratio,
            }
            for h in self.history
            if h.fuse_triggered
        ]

    def save_history(self, path: str) -> None:
        """保存热税历史到 JSON"""
        data = {
            "cumulative": self.cumulative,
            "trend": self.trend(n=len(self.history)),
            "fuse_events": self.fuse_events(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def load_history(self, path: str) -> bool:
        """加载热税历史"""
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.cumulative = data.get("cumulative", self.cumulative)
        return True


# ── 方便函数 ──

def create_heat_tax_monitor(guardian_engine=None) -> HeatTaxMonitor:
    """创建一个带有 GuardianEngine 的热税监控器"""
    def guardian_wrapper(text: str) -> dict:
        if guardian_engine is None:
            return {"score": 1.0, "density": 1.0, "violations": []}
        try:
            result = guardian_engine.scan(text)
            return {
                "score": result.score,
                "density": result.density,
                "violations": result.violations,
            }
        except Exception:
            return {"score": 1.0, "density": 1.0, "violations": []}

    return HeatTaxMonitor(guardian_evaluator=guardian_wrapper)
