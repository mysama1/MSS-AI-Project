"""
MSSclaw MeetingRoom — 公共数据库 + 会议室.

Agent 间异步通信的中心枢纽。

功能：
  - 话题线程（Thread）：每个话题一个隔离频道
  - Checkpoint 持久化（每 5 分钟 + 关键事件触发）
  - 大会模式（全 Agent 同步）+ 小会模式（双 Agent）
  - SOP 模板注入
  - 反意义污染过滤（所有讨论经过规范场）
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class ThreadStatus(str, Enum):
    OPEN = "open"
    ACTIVE = "active"
    PAUSED = "paused"       # 等待人工
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class MeetingType(str, Enum):
    GRAND = "grand"        # 大会: 全 Agent
    MINI = "mini"          # 小会: 双 Agent
    AD_HOC = "ad_hoc"      # 临时: 指定参与者


@dataclass
class ThreadPost:
    """一条讨论帖"""
    id: str = field(default_factory=lambda: f"post_{int(time.time()*1000)}")
    author: str = ""            # Agent 名
    content: str = ""
    content_type: str = "text"  # text | code | json | link
    timestamp: float = field(default_factory=time.time)
    reply_to: str = ""          # 回复某帖的 id
    attachments: list[str] = field(default_factory=list)  # 文件路径/链接
    meaning_score: float = 1.0  # 意义评分（反污染用）


@dataclass
class Thread:
    """一个讨论话题"""
    id: str = field(default_factory=lambda: f"thread_{int(time.time()*1000)}")
    topic: str = ""
    description: str = ""
    status: ThreadStatus = ThreadStatus.OPEN
    created_by: str = ""        # Agent 名
    created_at: float = field(default_factory=time.time)
    posts: list[ThreadPost] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    sop_template: str = ""      # SOP 模板引用
    checkpoint_at: float = 0.0  # 最后持久化时间
    meaning_pollution_level: float = 0.0  # 意义污染等级 0-1

    def add_post(self, author: str, content: str, content_type: str = "text",
                 attachments: list[str] = None) -> ThreadPost:
        post = ThreadPost(
            author=author,
            content=content,
            content_type=content_type,
            attachments=attachments or [],
        )
        self.posts.append(post)
        return post

    def last_activity(self) -> float:
        if not self.posts:
            return self.created_at
        return self.posts[-1].timestamp


# ── SOP 模板库 ──


class SOPTemplates:
    """标准作业流程模板库.

    模板可以在 MeetingRoom 中注入到线程。
    Agent 可以引用 SOP 模板来标准化任务流程。
    """

    TEMPLATES = {
        "paper_writing": {
            "name": "论文撰写 SOP",
            "steps": [
                "1. 确定核心命题和贡献点",
                "2. 实验设计和数据收集",
                "3. 方法论描述（可复现性>美观性）",
                "4. 实验结果表格和图表",
                "5. 讨论：与基线比较 + 局限性",
                "6. 结论：一页内说清楚核心贡献",
                "7. 同行评审前自检清单",
            ],
            "review_checklist": [
                "贡献是否明确？",
                "实验是否可复现？",
                "是否有诚实基线？",
                "是否有跨学科锚定？",
            ],
        },
        "sft_training": {
            "name": "SFT 训练 SOP",
            "steps": [
                "1. 数据准备：format → dedup → split",
                "2. 环境检查：torch cuda unsloth 版本对齐",
                "3. 基线评估：训练前跑 benchmark",
                "4. 训练：低 epoch 先试跑 → 确认 loss 下降 → 全量",
                "5. 验证：8 组场景全覆盖测试",
                "6. 模型保存 + 清理旧模型",
                "7. 训练报告归档到 KB",
            ],
        },
        "kb_entry": {
            "name": "知识库入库 SOP",
            "steps": [
                "1. 扫描现有条目避免重复",
                "2. 分配 H-ID（连续递增）",
                "3. 写入完整 JSON：title/type/layer/summary/content/references",
                "4. 更新 _master_index.md",
                "5. 交叉引用检查（前后条目一致性）",
            ],
        },
        "code_review": {
            "name": "代码审查 SOP",
            "steps": [
                "1. 自动检查：语法 + 导入 + 类型",
                "2. 安全审查：规范场扫描",
                "3. 架构审查：是否遵循项目模式",
                "4. 测试覆盖：关键路径有测试",
                "5. 文档：docstring + 用法示例",
            ],
        },
    }

    @classmethod
    def get(cls, name: str) -> Optional[dict]:
        return cls.TEMPLATES.get(name)

    @classmethod
    def list(cls) -> list[str]:
        return list(cls.TEMPLATES.keys())


# ── MeetingRoom ──


class MeetingRoom:
    """MSS 集团公共会议室.

    持久化到磁盘，支持 Checkpoint 恢复。
    所有讨论接受意义污染检查。
    """

    def __init__(self, db_path: str = "", checkpoint_interval: float = 300.0):
        self._path = db_path or "data/meeting_room.json"
        self._checkpoint_interval = checkpoint_interval  # 默认 5 分钟
        self._threads: dict[str, Thread] = {}
        self._lock = threading.Lock()
        self._pollution_threshold: float = 0.7
        self._pollution_checker: Optional[Callable] = None  # 外部意义污染检测器
        self._load()

    # ── 线程管理 ──

    def create_thread(self, topic: str, created_by: str, description: str = "",
                      tags: list[str] = None, sop: str = "") -> Thread:
        """创建新话题线程"""
        thread = Thread(
            topic=topic,
            description=description,
            created_by=created_by,
            tags=tags or [],
            sop_template=sop,
        )
        with self._lock:
            self._threads[thread.id] = thread
        self._checkpoint()
        return thread

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        return self._threads.get(thread_id)

    def list_threads(self, status: ThreadStatus = None, tag: str = None) -> list[Thread]:
        threads = list(self._threads.values())
        if status:
            threads = [t for t in threads if t.status == status]
        if tag:
            threads = [t for t in threads if tag in t.tags]
        return sorted(threads, key=lambda t: t.last_activity(), reverse=True)

    def close_thread(self, thread_id: str, resolution: str = "") -> None:
        """关闭话题"""
        t = self._threads.get(thread_id)
        if t:
            t.status = ThreadStatus.RESOLVED
            t.add_post("SYSTEM", f"[线程关闭] {resolution}")
            self._checkpoint()

    # ── 帖子管理 ──

    def post(self, thread_id: str, author: str, content: str,
             content_type: str = "text", attachments: list[str] = None) -> Optional[ThreadPost]:
        """在话题下发帖"""
        t = self._threads.get(thread_id)
        if not t:
            return None
        if t.status in (ThreadStatus.ARCHIVED,):
            return None

        # 意义污染检查
        if self._pollution_checker:
            pollution = self._pollution_checker(content)
            if pollution > self._pollution_threshold:
                # 标记但不禁言（Agent 间讨论不应过度审查）
                t.meaning_pollution_level = max(t.meaning_pollution_level, pollution)

        post = t.add_post(author, content, content_type, attachments)
        t.status = ThreadStatus.ACTIVE
        self._checkpoint()
        return post

    def get_recent_posts(self, thread_id: str, limit: int = 20) -> list[ThreadPost]:
        t = self._threads.get(thread_id)
        if not t:
            return []
        return t.posts[-limit:]

    # ── 大会/小会 ──

    def start_grand_meeting(self, agenda: str, participants: list[str]) -> Thread:
        """启动大会：全 Agent 同步"""
        thread = self.create_thread(
            topic=f"大会: {agenda[:60]}",
            created_by="PLAN",
            description=f"[大会] {agenda}\n参与者: {', '.join(participants)}",
            tags=["grand_meeting"],
        )
        thread.add_post("PLAN", f"## 大会议题\n\n{agenda}")
        return thread

    def start_mini_meeting(self, agent_a: str, agent_b: str, topic: str) -> Thread:
        """启动小会：双 Agent 对齐"""
        desc = f"[小会] {agent_a} ↔ {agent_b}: {topic}"
        thread = self.create_thread(
            topic=f"小会: {topic[:60]}",
            created_by=agent_a,
            description=desc,
            tags=["mini_meeting", agent_a, agent_b],
        )
        return thread

    # ── SOP 注入 ──

    def inject_sop(self, thread_id: str, sop_name: str) -> bool:
        """向话题注入 SOP 模板"""
        t = self._threads.get(thread_id)
        if not t:
            return False

        template = SOPTemplates.get(sop_name)
        if not template:
            return False

        t.sop_template = sop_name
        content = f"## SOP: {template['name']}\n\n" + "\n".join(template["steps"])
        t.add_post("SYSTEM", content, content_type="sop")
        self._checkpoint()
        return True

    # ── 持久化 ──

    def checkpoint(self) -> None:
        self._checkpoint()

    def _checkpoint(self) -> None:
        """持久化到磁盘（防状态失忆 — 坑 6）"""
        now = time.time()
        # 检查是否有活跃线程需要保存
        active_threads = [t for t in self._threads.values()
                          if t.status == ThreadStatus.ACTIVE]
        last_checkpoints = [t.checkpoint_at for t in active_threads]
        needs_save = not last_checkpoints or \
                     any(now - ct > self._checkpoint_interval for ct in last_checkpoints)

        if needs_save:
            self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path) or "data", exist_ok=True)
        now = time.time()
        data = {
            "saved_at": now,
            "threads": {}
        }
        with self._lock:
            for tid, t in self._threads.items():
                t.checkpoint_at = now
                data["threads"][tid] = {
                    "id": t.id,
                    "topic": t.topic,
                    "description": t.description,
                    "status": t.status.value,
                    "created_by": t.created_by,
                    "created_at": t.created_at,
                    "tags": t.tags,
                    "sop_template": t.sop_template,
                    "meaning_pollution_level": t.meaning_pollution_level,
                    "posts": [
                        {
                            "id": p.id,
                            "author": p.author,
                            "content": p.content,
                            "content_type": p.content_type,
                            "timestamp": p.timestamp,
                            "reply_to": p.reply_to,
                            "attachments": p.attachments,
                        }
                        for p in t.posts
                    ],
                }

        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, encoding="utf-8") as f:
                    data = json.load(f)
                    for td in data.get("threads", {}).values():
                        t = Thread(
                            id=td["id"],
                            topic=td["topic"],
                            description=td.get("description", ""),
                            status=ThreadStatus(td["status"]),
                            created_by=td["created_by"],
                            created_at=td["created_at"],
                            tags=td.get("tags", []),
                            sop_template=td.get("sop_template", ""),
                            checkpoint_at=td.get("checkpoint_at", 0.0),
                            meaning_pollution_level=td.get("meaning_pollution_level", 0.0),
                        )
                        for pd in td.get("posts", []):
                            t.posts.append(ThreadPost(
                                id=pd["id"], author=pd["author"],
                                content=pd["content"],
                                content_type=pd.get("content_type", "text"),
                                timestamp=pd["timestamp"],
                                reply_to=pd.get("reply_to", ""),
                                attachments=pd.get("attachments", []),
                            ))
                        self._threads[t.id] = t
        except Exception:
            self._threads = {}

    # ── 统计 ──

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            total_posts = sum(len(t.posts) for t in self._threads.values())
            return {
                "total_threads": len(self._threads),
                "active_threads": sum(1 for t in self._threads.values()
                                      if t.status == ThreadStatus.ACTIVE),
                "total_posts": total_posts,
                "recent_activity": [
                    {"topic": t.topic, "posts": len(t.posts),
                     "last": t.last_activity()}
                    for t in sorted(self._threads.values(),
                                    key=lambda x: x.last_activity(), reverse=True)[:5]
                ],
            }

    def search(self, query: str) -> list[dict]:
        """简单全文搜索"""
        results = []
        q = query.lower()
        for t in self._threads.values():
            matches = []
            for p in t.posts:
                if q in p.content.lower() or q in p.author.lower():
                    matches.append({"author": p.author, "excerpt": p.content[:100]})
            if matches:
                results.append({"thread": t.topic, "thread_id": t.id, "matches": matches[:5]})
        return results
