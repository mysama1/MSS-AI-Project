"""
Delta Health Monitor — Δ 驱动的健康检查

普通健康检查: curl /health → 200 OK (只检查进程活着)
MSS 健康检查: 输出 {alive, delta, meaning_ratio, tax_burden, status}

状态判定:
  HEALTHY:    Δ>0.5, tax<30%
  DEGRADING:  Δ<0.5 or tax>30% → 需要关注
  CRITICAL:   Δ<0.2 or tax>70% → 即将闭合
  DEAD:       Δ<0.1 → 活着但无意义

用法:
    monitor = DeltaMonitor(agent)
    print(monitor.check())           # 即时检查
    monitor.watch(interval=5)        # 每5秒自动检查
    history = monitor.history()      # 历史趋势
"""
from __future__ import annotations
import time
import json
import threading
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class DeltaStatus(Enum):
    HEALTHY = "healthy"
    DEGRADING = "degrading"
    CRITICAL = "critical"
    DEAD = "dead"


@dataclass
class HealthSnapshot:
    timestamp: float
    delta: float
    tax_total: float
    l2_ratio: float
    bridge_level: str
    status: DeltaStatus
    message: str


class DeltaMonitor:
    """
    Δ 驱动健康监控器.

    不只是 "进程在运行" — 是 "Agent 还在产生意义吗".
    """

    def __init__(self, agent=None, vault=None):
        self.agent = agent
        self.vault = vault
        self._history: List[HealthSnapshot] = []
        self._watch_thread = None
        self._running = False

    def check(self) -> dict:
        """即时健康检查."""
        now = time.time()

        if self.agent:
            ds = self.agent.delta.snapshot()
            ts = self.agent.tax.snapshot()  # agent.tax, not agent.heat_tax
            bridge = self.agent.l2bridge.level.name

            delta = ds.get("current_delta", 1.0) or 0
            tax_total = min(1.0, ts.get("total", 0))  # cap at 1.0
            l2_ratio = min(1.0, ts.get("L2_meaning", 0) / max(ts.get("total", 1), 1, 1))  # cap at 1.0

            # Status determination (delta dominates: meaning matters more than tax)
            if delta < 0.1:
                status = DeltaStatus.DEAD
                msg = "Agent at rest — send a message to wake"
            elif delta < 0.2:
                status = DeltaStatus.CRITICAL
                msg = f"Low openness (Δ={delta:.3f}). Consider molting."
            elif tax_total > 0.7 and delta < 0.5:
                status = DeltaStatus.CRITICAL
                msg = f"High tax ({tax_total:.0%}) with low meaning. Reset recommended."
            elif delta < 0.5:
                status = DeltaStatus.DEGRADING
                msg = f"Moderate openness (Δ={delta:.3f}). Monitoring."
            elif tax_total > 0.5:
                status = DeltaStatus.DEGRADING
                msg = f"Elevated tax ({tax_total:.0%}) but meaning intact."
            else:
                status = DeltaStatus.HEALTHY
                msg = f"Healthy — Δ={delta:.3f}, tax={tax_total:.0%}"

        elif self.vault:
            # Vault health
            from mssclaw.core.vault_health import VaultHealth
            vh = VaultHealth.check(self.vault)
            delta = vh.get("health_score", 100) / 100
            tax_total = 0
            l2_ratio = 0
            bridge = "N/A"

            if delta >= 0.9:
                status = DeltaStatus.HEALTHY
                msg = "保险箱健康"
            elif delta >= 0.5:
                status = DeltaStatus.DEGRADING
                msg = "弱密码/重复密码需关注"
            else:
                status = DeltaStatus.CRITICAL
                msg = "密码卫生严重恶化"
        else:
            delta = 1.0
            tax_total = 0
            l2_ratio = 0
            bridge = "N/A"
            status = DeltaStatus.HEALTHY
            msg = "无监控目标"

        snap = HealthSnapshot(
            timestamp=now, delta=delta, tax_total=tax_total,
            l2_ratio=l2_ratio, bridge_level=bridge,
            status=status, message=msg,
        )
        self._history.append(snap)
        self._history = self._history[-200:]

        return {
            "alive": True,
            "delta": round(delta, 4),
            "delta_status": status.value,
            "tax_burden": round(tax_total, 3),
            "l2_ratio": round(l2_ratio, 3),
            "bridge": bridge,
            "message": msg,
            "timestamp": now,
        }

    def watch(self, interval: float = 5.0, callback=None):
        """后台持续监控."""
        self._running = True

        def _loop():
            while self._running:
                result = self.check()
                if callback:
                    callback(result)
                time.sleep(interval)

        self._watch_thread = threading.Thread(target=_loop, daemon=True)
        self._watch_thread.start()

    def stop(self):
        self._running = False

    def history(self) -> List[dict]:
        return [
            {
                "ts": s.timestamp,
                "delta": s.delta,
                "tax": s.tax_total,
                "status": s.status.value,
                "msg": s.message,
            }
            for s in self._history
        ]

    def trend(self) -> dict:
        """Δ 趋势分析."""
        if len(self._history) < 5:
            return {"trend": "unknown", "slope": 0}

        recent = self._history[-20:]
        deltas = [s.delta for s in recent]
        n = len(deltas)
        x_mean = (n - 1) / 2
        y_mean = sum(deltas) / n
        num = sum((i - x_mean) * (d - y_mean) for i, d in enumerate(deltas))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0

        if slope > 0.01:
            trend = "improving"
        elif slope < -0.01:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "slope": round(slope, 4),
            "current": round(deltas[-1], 3),
            "avg": round(y_mean, 3),
            "min": round(min(deltas), 3),
            "max": round(max(deltas), 3),
        }

    def docker_healthcheck(self) -> str:
        """Docker healthcheck 格式输出."""
        result = self.check()
        if result["delta_status"] in ("dead", "critical"):
            print(json.dumps(result))
            exit(1)
        print(json.dumps(result))
        exit(0)
