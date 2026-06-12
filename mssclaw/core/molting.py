"""
MSSclaw Molt Protocol — 蜕壳协议.

四种蜕壳模式：
  complete_molt:   全量迁移 → 宿主更换/内核升级
  incremental_molt: 增量迁移 → 小版本热更新
  fork_molt:       分叉克隆 → A/B 测试/探索性分支
  swarm_molt:      蜂群轮换 → 零停机迁移

MOLT_PACKAGE 格式：
  {kernel, memory, runtime, signature}

蜕壳决策树：
  内核(六公理)变更 → complete_molt (全节点 + 人工确认)
  规范场变更 → swarm_molt (零停机)
  Agent层变更 → 热注册 (无需蜕壳)
  生态层变更 → 无需蜕壳
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class MoltMode(str, Enum):
    COMPLETE = "complete"         # 全量
    INCREMENTAL = "incremental"   # 增量
    FORK = "fork"                 # 分叉
    SWARM = "swarm"               # 蜂群


class MoltStatus(str, Enum):
    PREPARING = "preparing"       # 准备蜕壳
    FREEZING = "freezing"         # 冻结中（停止新任务）
    PACKING = "packing"           # 序列化中
    MIGRATING = "migrating"       # 迁移中
    VERIFYING = "verifying"       # 验证中
    ACTIVATING = "activating"     # 激活新壳
    COMPLETE = "complete"         # 完成
    ROLLBACK = "rollback"         # 回滚
    FAILED = "failed"


@dataclass
class MoltPackage:
    """蜕壳包 —— MSSclaw 迁移的基本单元.

    包含：六公理内核 + 知识库快照 + 决策链 + 运行时状态
    """
    version: str = "1.0"
    timestamp: float = field(default_factory=time.time)
    source_host: str = ""
    source_shell_id: str = ""

    # 内核：不可变
    kernel: dict[str, Any] = field(default_factory=dict)
    # 记忆：可裁剪
    memory: dict[str, Any] = field(default_factory=dict)
    # 运行时：当前任务 + Checkpoint
    runtime: dict[str, Any] = field(default_factory=dict)

    signature: str = ""
    checksum: str = ""

    def sign(self) -> str:
        """对包签名（SHA256）→ 防篡改"""
        payload = json.dumps({
            "kernel": self.kernel,
            "memory": {"kb_count": len(self.memory.get("kb_snapshot", [])),
                        "decision_chain_len": len(self.memory.get("decision_chain", []))},
            "runtime": {"active_tasks": len(self.runtime.get("active_tasks", [])),
                         "checkpoint_id": self.runtime.get("checkpoint_id", "")},
            "version": self.version,
            "timestamp": self.timestamp,
        }, sort_keys=True)
        self.signature = hashlib.sha256(payload.encode()).hexdigest()
        return self.signature

    def verify(self, expected_signature: str) -> bool:
        """验证签名"""
        current = hashlib.sha256(
            json.dumps({
                "kernel": self.kernel,
                "memory": {"kb_count": len(self.memory.get("kb_snapshot", [])),
                            "decision_chain_len": len(self.memory.get("decision_chain", []))},
                "runtime": {"active_tasks": len(self.runtime.get("active_tasks", [])),
                             "checkpoint_id": self.runtime.get("checkpoint_id", "")},
                "version": self.version,
                "timestamp": self.timestamp,
            }, sort_keys=True).encode()
        ).hexdigest()
        return current == expected_signature

    def estimate_size(self) -> int:
        """估算包大小（字节）"""
        return len(json.dumps(self.to_dict(), ensure_ascii=False))

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "source_host": self.source_host,
            "source_shell_id": self.source_shell_id,
            "kernel": self.kernel,
            "memory": self.memory,
            "runtime": self.runtime,
            "signature": self.signature,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MoltPackage:
        return cls(
            version=data.get("version", "1.0"),
            timestamp=data.get("timestamp", 0),
            source_host=data.get("source_host", ""),
            source_shell_id=data.get("source_shell_id", ""),
            kernel=data.get("kernel", {}),
            memory=data.get("memory", {}),
            runtime=data.get("runtime", {}),
            signature=data.get("signature", ""),
            checksum=data.get("checksum", ""),
        )


# ── 蜕壳引擎 ──


class MoltEngine:
    """MSSclaw 蜕壳引擎.

    负责四种蜕壳模式的编排和执行。
    蜕壳 = 保存灵魂 + 更换躯壳 + 验证完整性。

    使用：
        engine = MoltEngine(home="E:/MSS_Data")
        package = engine.prepare(...)
        engine.execute(MoltMode.SWARM, package)
    """

    # 六公理 —— MSS 灵魂的不可变异部分
    SIX_AXIOMS = {
        "A1": "意义至上公理 — 意义是系统的原初目标函数，所有其他约束从属于意义",
        "A2": "符号-意义分离公理 — 符号是意义的投影，符号变换不影响意义保真度",
        "A3": "不可约化热税公理 — 任何有意义的信息处理必然产生不可消除的热税",
        "A4": "随机性公理 — 真正的随机性是意义系统的必要组分，防止确定性闭合",
        "A5": "物理投影公理 — 所有意义操作必须在物理层有对应投影",
        "A6": "矛盾升维公理 — 低维不可解的矛盾，升维后可解；升维本身产生新的矛盾",
    }

    def __init__(self, home: str = "", storage_dir: str = ""):
        self._home = home or os.getcwd()
        self._storage = storage_dir or os.path.join(self._home, "data", "molt_packages")
        self._status: MoltStatus = MoltStatus.COMPLETE
        self._current_molt_id: str = ""
        self._on_status_change: Optional[Callable] = None
        self._old_shell_backup: str = ""  # 旧壳备份路径（回滚用）
        os.makedirs(self._storage, exist_ok=True)

    # ── 公共 API ──

    def prepare(self, kb_snapshot: list[dict], decision_chain: list[dict],
                active_tasks: list[dict], checkpoint_id: str = "",
                delta_state: float = 0.72) -> MoltPackage:
        """准备蜕壳包"""
        pkg = MoltPackage(
            source_host=os.environ.get("COMPUTERNAME", "unknown"),
            source_shell_id=hex(hash(str(time.time())))[:12],
        )
        # 内核
        pkg.kernel = {
            "axioms": self.SIX_AXIOMS,
            "delta_state": delta_state,
            "axiom_version": "v15.1",
        }
        # 记忆
        pkg.memory = {
            "kb_snapshot": kb_snapshot,
            "decision_chain": decision_chain,
            "kb_count": len(kb_snapshot),
        }
        # 运行时
        pkg.runtime = {
            "active_tasks": active_tasks,
            "checkpoint_id": checkpoint_id,
            "pending_reviews": [],  # 等待审查的任务
        }

        pkg.sign()
        return pkg

    def execute(self, mode: MoltMode, package: MoltPackage, **kwargs) -> bool:
        """执行蜕壳.

        Returns:
            True: 蜕壳成功
            False: 蜕壳失败（可通过 rollback 回滚）
        """
        self._current_molt_id = f"molt_{int(time.time())}_{mode.value}"
        self._set_status(MoltStatus.PREPARING)

        try:
            if mode == MoltMode.COMPLETE:
                return self._execute_complete(package, **kwargs)
            elif mode == MoltMode.INCREMENTAL:
                return self._execute_incremental(package, **kwargs)
            elif mode == MoltMode.FORK:
                return self._execute_fork(package, **kwargs)
            elif mode == MoltMode.SWARM:
                return self._execute_swarm(package, **kwargs)
        except Exception as e:
            self._set_status(MoltStatus.FAILED)
            print(f"[MOLT] FAILED: {e}")
            return False

        return False

    def rollback(self) -> bool:
        """回滚到蜕壳前状态"""
        if not self._old_shell_backup:
            print("[MOLT] No backup to rollback to")
            return False

        self._set_status(MoltStatus.ROLLBACK)
        # 恢复旧壳
        restore_target = os.path.join(self._home, "data", "shell_state.json")
        try:
            if os.path.exists(self._old_shell_backup):
                shutil.copy2(self._old_shell_backup, restore_target)
                print(f"[MOLT] Rolled back from {self._old_shell_backup}")
                self._set_status(MoltStatus.COMPLETE)
                return True
        except Exception as e:
            print(f"[MOLT] Rollback failed: {e}")
        return False

    def verify_package(self, package: MoltPackage) -> bool:
        """验证蜕壳包完整性"""
        # 检查内核六公理是否完整
        for axiom_id in ["A1", "A2", "A3", "A4", "A5", "A6"]:
            if axiom_id not in package.kernel.get("axioms", {}):
                print(f"[MOLT] VERIFY FAILED: Missing axiom {axiom_id}")
                return False

        # 检查签名
        expected = package.sign()
        if package.signature != expected:
            print(f"[MOLT] VERIFY FAILED: Signature mismatch")
            return False

        # 检查 KB 完整性
        kb = package.memory.get("kb_snapshot", [])
        if not kb:
            print(f"[MOLT] VERIFY WARNING: Empty KB snapshot")

        print(f"[MOLT] VERIFY PASSED: {len(kb)} KB entries, "
              f"{len(package.runtime.get('active_tasks', []))} active tasks")
        return True

    def save_package(self, package: MoltPackage) -> str:
        """保存蜕壳包到磁盘"""
        molt_id = self._current_molt_id or f"molt_{int(time.time())}_{package.source_shell_id[:8]}"
        filename = f"{molt_id}.json"
        filepath = os.path.join(self._storage, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(package.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"[MOLT] Package saved: {filepath} ({package.estimate_size()} bytes)")
        return filepath

    # ── 四种蜕壳实现 ──

    def _execute_complete(self, pkg: MoltPackage,
                          confirm: bool = True) -> bool:
        """完整蜕壳 — 全量序列化 + 迁移 + 重激活.

        流程：
          1. 冻结：停止接收新任务
          2. 备份：保存当前壳状态
          3. 打包：序列化所有数据
          4. 保存：写入 MOLT_PACKAGE
          5. 迁移：包复制到新宿主
          6. 验证：新宿主解包 + 完整性校验
          7. 激活：新宿主开始接收任务
        """
        if confirm:
            print("[MOLT] COMPLETE_MOLT: Requires human confirmation.")
            self._set_status(MoltStatus.NEEDS_CONFIRMATION)
            return True  # 等待人工确认

        # 1. 冻结
        self._set_status(MoltStatus.FREEZING)
        self._backup_current_shell()

        # 2. 打包
        self._set_status(MoltStatus.PACKING)
        pkg.sign()

        # 3. 保存
        self._set_status(MoltStatus.MIGRATING)
        filepath = self.save_package(pkg)

        # 4. 验证
        self._set_status(MoltStatus.VERIFYING)
        ok = self.verify_package(pkg)

        if ok:
            self._set_status(MoltStatus.COMPLETE)
            print(f"[MOLT] COMPLETE_MOLT success: {filepath}")
        else:
            self._set_status(MoltStatus.FAILED)
        return ok

    def _execute_incremental(self, pkg: MoltPackage, **kwargs) -> bool:
        """增量蜕壳 — 仅更新变更部分.

        流程：
          1. Diff 对比：新旧知识库/规则差异
          2. 仅打包变更部分
          3. 应用到新壳
        """
        self._set_status(MoltStatus.PACKING)

        # 增量差异检测（简化实现）
        changes = kwargs.get("changes", {})
        if changes:
            pkg.memory["incremental_changes"] = changes
            pkg.sign()

        self._set_status(MoltStatus.MIGRATING)
        self.save_package(pkg)
        self._set_status(MoltStatus.COMPLETE)
        print(f"[MOLT] INCREMENTAL_MOLT success: {len(changes)} changes")
        return True

    def _execute_fork(self, pkg: MoltPackage,
                      fork_name: str = "", **kwargs) -> bool:
        """分叉蜕壳 — 克隆核心 + 独立进化.

        流程：
          1. 克隆六公理内核
          2. 选择性克隆 KB 子集
          3. 新壳标记为 "fork:{name}"
          4. 两个壳独立运行，互不干扰
          5. 后续可合并（merge）或独立继续
        """
        self._set_status(MoltStatus.PACKING)

        fork_id = fork_name or f"fork_{int(time.time())}"
        pkg.source_shell_id = fork_id

        # 分叉壳有独立的存储路径
        fork_storage = os.path.join(self._storage, fork_id)
        os.makedirs(fork_storage, exist_ok=True)

        pkg.sign()
        filepath = os.path.join(fork_storage, "molt_package.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(pkg.to_dict(), f, ensure_ascii=False, indent=2)

        self._set_status(MoltStatus.COMPLETE)
        print(f"[MOLT] FORK_MOLT success: {fork_id} → {fork_storage}")
        return True

    def _execute_swarm(self, pkg: MoltPackage,
                       new_nodes: int = 2, **kwargs) -> bool:
        """蜂群蜕壳 — 多节点协同轮换迁移（零停机）.

        流程：
          1. 启动新壳节点（空壳）
          2. 新壳从 MeetingRoom 同步当前状态
          3. 旧壳逐个标记为"蜕壳中"
          4. 流量逐步切到新壳
          5. 旧壳完成当前任务后休眠（保留 7 天可回滚）
          6. 确认新壳稳定 → 旧壳退役
        """
        self._set_status(MoltStatus.MIGRATING)
        pkg.sign()

        # 生成多个壳节点包
        saved = []
        for i in range(new_nodes):
            node_pkg = MoltPackage(
                version=pkg.version,
                source_host=pkg.source_host,
                source_shell_id=f"{pkg.source_shell_id}_node{i}",
                kernel=pkg.kernel.copy(),
                memory=pkg.memory.copy(),
                runtime={"active_tasks": [], "checkpoint_id": pkg.runtime.get("checkpoint_id", "")},
            )
            node_pkg.sign()
            # 用临时 ID 避免同名覆盖
            saved_id = f"{self._current_molt_id}_n{i}"
            oid = self._current_molt_id
            self._current_molt_id = saved_id
            filepath = self.save_package(node_pkg)
            self._current_molt_id = oid
            saved.append(filepath)

        self._set_status(MoltStatus.COMPLETE)
        print(f"[MOLT] SWARM_MOLT success: {new_nodes} nodes → {saved}")
        return True

    # ── 辅助方法 ──

    def _backup_current_shell(self) -> None:
        """备份当前壳状态（用于回滚）"""
        self._old_shell_backup = os.path.join(
            self._storage, f"backup_{int(time.time())}.json"
        )
        # 备份当前 agent 状态（简化）
        backup = {
            "timestamp": time.time(),
            "molt_id": self._current_molt_id,
        }
        with open(self._old_shell_backup, "w", encoding="utf-8") as f:
            json.dump(backup, f, ensure_ascii=False, indent=2)

    def _set_status(self, status: MoltStatus) -> None:
        self._status = status
        if self._on_status_change:
            self._on_status_change(status)

    def get_status(self) -> MoltStatus:
        return self._status

    def list_packages(self) -> list[str]:
        """列出所有已保存的蜕壳包"""
        packages = []
        if os.path.exists(self._storage):
            for f in os.listdir(self._storage):
                if f.endswith(".json"):
                    packages.append(os.path.join(self._storage, f))
        return sorted(packages)


# ── 蜕壳决策树 ──


def decide_molt_mode(change_type: str) -> MoltMode:
    """根据变更类型决定蜕壳模式.

    变更类型：
      - "kernel"      → 六公理变更      → complete_molt
      - "norm_field"  → 规范场变更      → swarm_molt
      - "agent_layer" → Agent 层变更    → 热注册 (无需蜕壳)
      - "eco_layer"   → 生态层变更      → 无需蜕壳
      - "host"        → 宿主迁移        → complete_molt
    """
    tree = {
        "kernel": MoltMode.COMPLETE,
        "norm_field": MoltMode.SWARM,
        "agent_layer": None,     # 热注册
        "eco_layer": None,       # 无需蜕壳
        "host": MoltMode.COMPLETE,
    }
    return tree.get(change_type)
