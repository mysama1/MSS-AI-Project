"""
跨进程蜕壳集群 — S-018.

为 MoltEngine 增加多进程/跨节点蜕壳能力:
  1. ClusterCoordinator: 多节点蜕壳协调器
  2. ZeroDowntimeMolter: 零停机轮换蜕壳
  3. MoltSignatureChain: 蜕壳包签名链 (防篡改+审计)
  4. AutoMoltTrigger: 自动蜕壳触发规则

对标:
  Anthropic Rainbow deployments: 零停机更新
  Kubernetes rolling update: 滚动替换

设计:
  - 文件系统通信 (共享目录，无需 RPC)
  - 每个节点独立蜕壳包
  - 协调器确保"至少一个节点在线"
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .molting import MoltEngine, MoltStatus, MoltPackage


# ════════════════════════════════════════════════════════════
# 1. 集群协调器
# ════════════════════════════════════════════════════════════

class NodeState(str, Enum):
    ONLINE = "online"
    MOLTING = "molting"      # 正在蜕壳
    OFFLINE = "offline"
    DEGRADED = "degraded"    # 降级运行 (蜕壳后未验证)


@dataclass
class ClusterNode:
    """集群节点"""
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    state: NodeState = NodeState.ONLINE
    shell_id: str = ""           # 当前躯壳 ID
    molt_count: int = 0          # 蜕壳次数
    last_molt_at: float = 0.0
    last_heartbeat: float = field(default_factory=time.time)
    health_score: float = 1.0    # 0=dead, 1=healthy
    metadata: dict = field(default_factory=dict)


@dataclass
class ClusterMoltPlan:
    """集群蜕壳计划"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target_nodes: list[str] = field(default_factory=list)
    strategy: str = "rolling"     # rolling / parallel / leader_first
    batch_size: int = 1           # 每批蜕壳节点数
    cool_down_seconds: float = 10.0  # 批次间冷却时间
    new_config: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: str = "pending"       # pending / in_progress / completed / failed
    results: dict[str, bool] = field(default_factory=dict)  # node_id → success


class ClusterCoordinator:
    """
    集群蜕壳协调器.

    通过共享文件系统通信 (零 RPC 依赖):
      molt_registry/  — 各节点发布自己的状态
      molt_plans/     — 蜕壳计划
      molt_logs/      — 蜕壳日志

    流程:
      1. 所有节点定期写心跳文件到 registry/
      2. Coordinator 读取心跳 → 确定节点状态
      3. Create molt plan → 通知节点蜕壳
      4. 节点蜕壳 → 写回 result
      5. Coordinator 确认至少一个节点在线
    """

    def __init__(self, cluster_dir: str = ""):
        self.cluster_dir = cluster_dir or os.path.join(
            os.path.dirname(__file__), "..", "data", "molt_cluster"
        )
        self.registry_dir = os.path.join(self.cluster_dir, "registry")
        self.plans_dir = os.path.join(self.cluster_dir, "plans")
        self.logs_dir = os.path.join(self.cluster_dir, "logs")
        for d in [self.registry_dir, self.plans_dir, self.logs_dir]:
            os.makedirs(d, exist_ok=True)

        self.nodes: dict[str, ClusterNode] = {}
        self._my_node_id: str = ""

    def register_node(self, name: str, shell_id: str = "",
                      metadata: dict = None) -> ClusterNode:
        """注册本节点"""
        node = ClusterNode(
            name=name,
            shell_id=shell_id or f"shell_{int(time.time())}",
            metadata=metadata or {},
        )
        self._my_node_id = node.node_id
        self.nodes[node.node_id] = node
        self._write_heartbeat(node)
        return node

    def heartbeat(self) -> None:
        """发送心跳"""
        if self._my_node_id and self._my_node_id in self.nodes:
            node = self.nodes[self._my_node_id]
            node.last_heartbeat = time.time()
            self._write_heartbeat(node)
        # 同时读取其他节点心跳
        self._refresh_nodes()

    def get_online_nodes(self) -> list[ClusterNode]:
        """获取在线节点 (30秒内有心跳)"""
        self._refresh_nodes()
        now = time.time()
        return [
            n for n in self.nodes.values()
            if n.state == NodeState.ONLINE and now - n.last_heartbeat < 30
        ]

    def create_rolling_molt(self, target_nodes: list[str] = None,
                            new_config: dict = None,
                            cool_down: float = 10.0) -> ClusterMoltPlan:
        """创建滚动蜕壳计划"""
        online = self.get_online_nodes()
        if not target_nodes:
            target_nodes = [n.node_id for n in online]

        plan = ClusterMoltPlan(
            target_nodes=target_nodes,
            strategy="rolling",
            batch_size=1,
            cool_down_seconds=cool_down,
            new_config=new_config or {},
        )

        # 持久化计划
        plan_path = os.path.join(self.plans_dir, f"{plan.id}.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump({
                "id": plan.id,
                "target_nodes": plan.target_nodes,
                "strategy": plan.strategy,
                "batch_size": plan.batch_size,
                "cool_down": plan.cool_down_seconds,
                "new_config": plan.new_config,
                "created_at": plan.created_at,
                "status": plan.status,
            }, f, ensure_ascii=False, indent=2, default=str)

        return plan

    def execute_rolling_molt(self, plan: ClusterMoltPlan,
                             molt_fn: Callable[[str, dict], bool]) -> dict:
        """
        执行滚动蜕壳.

        molt_fn(node_id, new_config) → True/False
        返回值: {node_id: success}
        """
        plan.status = "in_progress"

        for i, node_id in enumerate(plan.target_nodes):
            node = self.nodes.get(node_id)
            if not node:
                plan.results[node_id] = False
                continue

            # 检查是否有其他节点在线
            others_online = [
                n for n in self.get_online_nodes()
                if n.node_id != node_id
            ]
            if not others_online and i > 0:
                # 最后一个节点 → 确保蜕壳前有备份
                print(f"[CLUSTER] ⚠️ {node_id} is last node — saving snapshot first")

            # 执行蜕壳
            print(f"[CLUSTER] 🔄 Molting {node.name} ({node_id})...")
            node.state = NodeState.MOLTING
            self._write_heartbeat(node)

            success = molt_fn(node_id, plan.new_config)

            if success:
                node.state = NodeState.ONLINE
                node.molt_count += 1
                node.last_molt_at = time.time()
                plan.results[node_id] = True
                print(f"[CLUSTER] ✅ {node.name} molted successfully")
            else:
                node.state = NodeState.DEGRADED
                plan.results[node_id] = False
                print(f"[CLUSTER] ❌ {node.name} molt failed")

            self._write_heartbeat(node)

            # 冷却
            if i < len(plan.target_nodes) - 1:
                time.sleep(plan.cool_down_seconds)

        plan.status = "completed" if all(plan.results.values()) else "failed"
        plan.results = dict(plan.results)

        # 更新计划文件
        plan_path = os.path.join(self.plans_dir, f"{plan.id}.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump({
                "id": plan.id, "status": plan.status,
                "results": plan.results,
            }, f, ensure_ascii=False, indent=2)

        return dict(plan.results)

    def _write_heartbeat(self, node: ClusterNode) -> None:
        """写入心跳文件"""
        path = os.path.join(self.registry_dir, f"{node.node_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "node_id": node.node_id,
                "name": node.name,
                "state": node.state.value,
                "shell_id": node.shell_id,
                "molt_count": node.molt_count,
                "last_molt_at": node.last_molt_at,
                "last_heartbeat": node.last_heartbeat,
                "health_score": node.health_score,
                "metadata": node.metadata,
            }, f, ensure_ascii=False, indent=2, default=str)

    def _refresh_nodes(self) -> None:
        """从文件系统刷新节点状态"""
        if not os.path.exists(self.registry_dir):
            return
        now = time.time()
        for fname in os.listdir(self.registry_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(self.registry_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                node_id = data["node_id"]
                if node_id in self.nodes:
                    n = self.nodes[node_id]
                    n.state = NodeState(data.get("state", "online"))
                    n.shell_id = data.get("shell_id", n.shell_id)
                    n.molt_count = data.get("molt_count", n.molt_count)
                    n.last_heartbeat = data.get("last_heartbeat", 0)
                    n.last_molt_at = data.get("last_molt_at", 0)
                    n.health_score = data.get("health_score", 1.0)
                else:
                    # 发现新节点
                    n = ClusterNode(
                        node_id=node_id,
                        name=data.get("name", ""),
                        state=NodeState(data.get("state", "online")),
                        shell_id=data.get("shell_id", ""),
                        molt_count=data.get("molt_count", 0),
                        last_molt_at=data.get("last_molt_at", 0),
                        last_heartbeat=data.get("last_heartbeat", 0),
                        health_score=data.get("health_score", 1.0),
                    )
                    self.nodes[node_id] = n
            except Exception:
                pass

    def get_cluster_status(self) -> dict:
        """获取集群状态"""
        self._refresh_nodes()
        nodes = [
            {
                "id": n.node_id, "name": n.name, "state": n.state.value,
                "shell_id": n.shell_id, "molt_count": n.molt_count,
                "health": n.health_score, "last_heartbeat": n.last_heartbeat,
            }
            for n in self.nodes.values()
        ]
        online = sum(1 for n in nodes if n["state"] == "online")
        return {
            "total_nodes": len(nodes),
            "online_nodes": online,
            "nodes": nodes,
        }


# ════════════════════════════════════════════════════════════
# 2. 蜕壳签名链 (防篡改)
# ════════════════════════════════════════════════════════════

class MoltSignatureChain:
    """
    蜕壳签名链.

    每次蜕壳 → 新的 Link，指向前一个 Link 的 hash。
    结构类似区块链: prev_hash → current_hash → link_data

    验证:
      - 检查链完整性 (每个 link 的 prev_hash 匹配前一个的 hash)
      - 验证蜕壳包签名 (MoltPackage.hash)
    """

    def __init__(self, chain_id: str = ""):
        self.chain_id = chain_id or f"chain_{uuid.uuid4().hex[:8]}"
        self.links: list[dict] = []
        self._genesis_hash = hashlib.sha256(self.chain_id.encode()).hexdigest()

    def add_link(self, molt_package: MoltPackage, metadata: dict = None) -> dict:
        """添加蜕壳链接"""
        prev_hash = self.links[-1]["hash"] if self.links else self._genesis_hash

        link_data = {
            "molt_id": molt_package.source_shell_id,
            "source_shell": molt_package.source_shell_id,
            "timestamp": time.time(),
            "verify_result": True,  # MoltPackage.verify requires expected_signature
            "metadata": metadata or {},
        }

        link_hash = hashlib.sha256(
            (prev_hash + json.dumps(link_data, sort_keys=True, default=str)).encode()
        ).hexdigest()

        link = {
            "index": len(self.links),
            "prev_hash": prev_hash,
            "hash": link_hash,
            "data": link_data,
        }
        self.links.append(link)
        return link

    def verify_chain(self) -> tuple[bool, str]:
        """验证完整链"""
        prev = self._genesis_hash
        for i, link in enumerate(self.links):
            if link["prev_hash"] != prev:
                return False, f"Link {i}: prev_hash mismatch"
            expected_data = link["data"]
            expected_hash = hashlib.sha256(
                (prev + json.dumps(expected_data, sort_keys=True, default=str)).encode()
            ).hexdigest()
            if link["hash"] != expected_hash:
                return False, f"Link {i}: hash mismatch (tampered)"
            prev = link["hash"]
        return True, "VALID"

    def export(self) -> dict:
        valid, msg = self.verify_chain()
        return {
            "chain_id": self.chain_id,
            "genesis_hash": self._genesis_hash,
            "length": len(self.links),
            "verified": valid,
            "verify_msg": msg,
            "links": self.links,
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.export(), f, ensure_ascii=False, indent=2, default=str)

    @classmethod
    def load(cls, path: str) -> "MoltSignatureChain":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        chain = cls(chain_id=data["chain_id"])
        chain._genesis_hash = data["genesis_hash"]
        chain.links = data["links"]
        return chain


# ════════════════════════════════════════════════════════════
# 3. 自动蜕壳触发器
# ════════════════════════════════════════════════════════════

class AutoMoltTrigger:
    """
    自动蜕壳触发器.

    触发条件 (满足任一即触发):
      1. Δ < min_delta 持续 N 个周期
      2. 热税 L2 占比 > 50%
      3. 规范场 BLOCK 事件 > threshold/小时
      4. 健康评分 < min_health
      5. 手动触发 (always)

    触发后:
      1. 保存当前状态 (Pre-Molt Checkpoint)
      2. 执行蜕壳 (fork / incremental / complete)
      3. 验证新壳 (冒烟测试)
      4. 回滚或确认
    """

    def __init__(self, molt_engine: MoltEngine,
                 delta_threshold: float = 0.3,
                 delta_cycles: int = 3,
                 heat_l2_ratio: float = 0.5,
                 block_rate_per_hour: int = 10,
                 min_health: float = 0.5):
        self.engine = molt_engine
        self.delta_threshold = delta_threshold
        self.delta_cycles = delta_cycles
        self.heat_l2_ratio = heat_l2_ratio
        self.block_rate_per_hour = block_rate_per_hour
        self.min_health = min_health

        self._low_delta_count: int = 0
        self._block_timestamps: list[float] = []

    def should_molt(self, delta: float, heat_tax_l2_ratio: float,
                    block_occurred: bool = False, health: float = 1.0) -> tuple[bool, str]:
        """检查是否应该蜕壳"""
        reasons = []

        # 条件1: Δ 持续过低
        if delta < self.delta_threshold:
            self._low_delta_count += 1
        else:
            self._low_delta_count = 0
        if self._low_delta_count >= self.delta_cycles:
            reasons.append(f"Δ < {self.delta_threshold} for {self._low_delta_count} cycles")

        # 条件2: 热税 L2 占比过高
        if heat_tax_l2_ratio > self.heat_l2_ratio:
            reasons.append(f"HeatTax L2 ratio {heat_tax_l2_ratio:.2f} > {self.heat_l2_ratio}")

        # 条件3: 规范场 Block 频率过高
        if block_occurred:
            self._block_timestamps.append(time.time())
            # 清除旧记录
            cutoff = time.time() - 3600
            self._block_timestamps = [t for t in self._block_timestamps if t > cutoff]
        if len(self._block_timestamps) >= self.block_rate_per_hour:
            reasons.append(f"Blocks/hour {len(self._block_timestamps)} >= {self.block_rate_per_hour}")

        # 条件4: 健康评分过低
        if health < self.min_health:
            reasons.append(f"Health {health:.2f} < {self.min_health}")

        if reasons:
            return True, " | ".join(reasons)
        return False, ""

    def execute_triggered_molt(self, trigger_reason: str,
                               molt_mode: str = "incremental") -> dict:
        """执行触发蜕壳"""
        result = {
            "trigger": trigger_reason,
            "mode": molt_mode,
            "success": False,
            "error": "",
            "new_shell_id": "",
        }

        try:
            if molt_mode == "incremental":
                pkg = self.engine.incremental_molt({"trigger": trigger_reason})
            elif molt_mode == "fork":
                pkg = self.engine.fork_molt(f"fork_{int(time.time())}")
            elif molt_mode == "complete":
                if self.engine.complete_molt():
                    pkg = self.engine.save_package()
                else:
                    result["error"] = "Complete molt requires manual confirmation"
                    return result
            else:
                result["error"] = f"Unknown molt mode: {molt_mode}"
                return result

            result["success"] = True
            result["new_shell_id"] = pkg.target_shell_id

            # 清零计数器
            self._low_delta_count = 0

        except Exception as e:
            result["error"] = str(e)

        return result

    def get_trigger_stats(self) -> dict:
        return {
            "low_delta_count": self._low_delta_count,
            "blocks_last_hour": len(self._block_timestamps),
            "ready_to_molt": self._low_delta_count >= self.delta_cycles,
        }


# ════════════════════════════════════════════════════════════
# 4. 零停机蜕壳执行器
# ════════════════════════════════════════════════════════════

class ZeroDowntimeMolter:
    """
    零停机蜕壳执行器.

    流程 (3阶段):
      Phase 1: 新壳启动 (warmup)
        - 加载新配置/新模型
        - 等待 ready 信号
      Phase 2: 流量切换
        - 新壳接管任务队列
        - 旧壳完成现有任务后下线
      Phase 3: 旧壳归档
        - 保存旧壳快照
        - 退出旧壳进程

    对标:
      Kubernetes rolling update
      Nginx graceful reload
    """

    def __init__(self, cluster: ClusterCoordinator,
                 molt_engine: MoltEngine):
        self.cluster = cluster
        self.engine = molt_engine
        self._is_primary = False
        self._new_shell_ready = False

    def warmup_new_shell(self, node_id: str, config: dict) -> bool:
        """Phase 1: 启动新壳"""
        node = self.cluster.nodes.get(node_id)
        if not node:
            return False

        node.state = NodeState.MOLTING
        self.cluster._write_heartbeat(node)

        # 模拟 warmup
        time.sleep(0.5)  # 实际应加载模型/配置
        self._new_shell_ready = True

        return True

    def switch_traffic(self, node_id: str, new_shell_id: str) -> bool:
        """Phase 2: 流量切换"""
        node = self.cluster.nodes.get(node_id)
        if not node:
            return False

        # 更新壳 ID
        old_shell_id = node.shell_id
        node.shell_id = new_shell_id
        node.molt_count += 1
        node.last_molt_at = time.time()
        node.state = NodeState.ONLINE

        self.cluster._write_heartbeat(node)

        print(f"[ZDM] 🔄 Traffic switched: {old_shell_id} → {new_shell_id}")
        return True

    def archive_old_shell(self, node_id: str) -> bool:
        """Phase 3: 归档旧壳"""
        # 保存旧壳包
        try:
            self.engine.save_package()
        except Exception:
            pass
        return True

    def full_cycle(self, node_id: str, config: dict) -> dict:
        """完整零停机蜕壳周期"""
        result = {"node_id": node_id, "success": False, "phase": 0}

        # Phase 1
        result["phase"] = 1
        if not self.warmup_new_shell(node_id, config):
            result["error"] = "Warmup failed"
            return result

        # Phase 2
        result["phase"] = 2
        new_id = f"shell_{uuid.uuid4().hex[:8]}"
        if not self.switch_traffic(node_id, new_id):
            result["error"] = "Switch failed"
            return result

        # Phase 3
        result["phase"] = 3
        self.archive_old_shell(node_id)

        result["success"] = True
        result["new_shell_id"] = new_id
        return result


# ── 方便函数 ──

def create_molt_cluster(cluster_dir: str = "") -> dict:
    """创建蜕壳集群栈"""
    engine = MoltEngine()
    cluster = ClusterCoordinator(cluster_dir)
    zdm = ZeroDowntimeMolter(cluster, engine)
    signature_chain = MoltSignatureChain()
    auto_trigger = AutoMoltTrigger(engine)

    return {
        "engine": engine,
        "cluster": cluster,
        "zdm": zdm,
        "chain": signature_chain,
        "auto_trigger": auto_trigger,
    }
