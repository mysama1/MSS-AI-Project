"""
PersonalAgent — 私人域 Agent 体系.

与工作 Agent 完全分离:
  - 独立 SwarmBus (personal bus)
  - 独立 PersonalNormField (15条隐私/适宜性规则)
  - 独立热税预算 (L2意义热税阀值不同)
  - 独立数据存储 (~/.mssclaw/personal/)

具体 Agent:
  - LifeAgent: 日历/提醒/健康/天气
  - EntertainAgent: 影视/音乐/阅读/游戏推荐
  - SocialAgent: 消息草拟/社交网络管理
  - ConciergeAgent: 综合门房 (路由到其他三个)
"""
from __future__ import annotations

import json
import os
import threading
import time
from abc import abstractmethod
from datetime import datetime
from typing import Any, Optional

from .base import BaseAgent
from ..core.normative_field import NormativeField, NormDomain, NormLevel
from ..core.personal_norm_field import (
    PersonalDomain, load_personal_rules, create_personal_rules
)
from ..core.heat_tax import HeatTaxBudget
from ..core.delta import DeltaProtocol
from ..core.guardian_engine import GuardianEngine
from ..swarm.swarm import SwarmBus, SwarmNode
from ..swarm.protocol import Message, MessageHeader, MessageType, Priority


# ── 私域常量 ──

PERSONAL_DATA_DIR = os.path.expanduser("~/.mssclaw/personal")


class PersonalAgent(BaseAgent):
    """私人域 Agent 基类 — 继承 BaseAgent 但使用私域规范场.

    关键差异:
      1. norm_field → PersonalNormField (15条, 隐私导向)
      2. 数据隔离 → PERSONAL_DATA_DIR
      3. L2 热税阀值更低 → 私人对话天然高意义密度
      4. 不接受 work bus 的 TASK_ASSIGN
    """

    # 个人偏好存储
    preferences: dict[str, Any] = {}
    _prefs_file: str = ""

    def __init__(self, name: str, bus: SwarmBus = None,
                 heat_budget: HeatTaxBudget = None,
                 delta: DeltaProtocol = None,
                 guardian: GuardianEngine = None):
        # 使用私域规范场
        norm = NormativeField()
        load_personal_rules(norm)

        super().__init__(
            name=name, bus=bus,
            heat_budget=heat_budget,
            delta=delta,
            guardian=guardian,
            norm_field=norm,
        )

        # 数据隔离目录
        os.makedirs(PERSONAL_DATA_DIR, exist_ok=True)
        self._prefs_file = os.path.join(PERSONAL_DATA_DIR, f"{name}_prefs.json")
        self._load_preferences()

    # ── 偏好管理 ──

    def _load_preferences(self) -> None:
        """加载个人偏好"""
        if os.path.exists(self._prefs_file):
            try:
                with open(self._prefs_file, "r", encoding="utf-8") as f:
                    self.preferences = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.preferences = {}

    def save_preferences(self) -> None:
        """持久化个人偏好"""
        with open(self._prefs_file, "w", encoding="utf-8") as f:
            json.dump(self.preferences, f, ensure_ascii=False, indent=2)

    def set_pref(self, key: str, value: Any) -> None:
        self.preferences[key] = value
        self.save_preferences()

    def get_pref(self, key: str, default: Any = None) -> Any:
        return self.preferences.get(key, default)

    # ── 私域规范场检查 ──

    def privacy_check(self, content: str, domain: PersonalDomain) -> dict:
        """隐私检查 — 使用私域规则"""
        verdict = self.norm.check(NormDomain.CONTENT, {"text": content})
        return {
            "domain": domain.value,
            "level": verdict.level.value,
            "rule_name": verdict.rule_name,
            "reason": verdict.reason,
            "blocked": verdict.level == NormLevel.BLOCK,
        }

    # ── 健康检查 (扩展) ──

    def health_check(self) -> dict[str, Any]:
        base = super().health_check()
        base.update({
            "domain": "personal",
            "preferences_loaded": bool(self.preferences),
            "rules_count": len(self.norm._rules),
        })
        return base


# ════════════════════════════════════════════════════════════
# 具体 Agent 实现
# ════════════════════════════════════════════════════════════


class LifeAgent(PersonalAgent):
    """生活管家 — 日历/提醒/健康/天气"""

    role = "Life-Agent"
    capabilities = ["calendar", "reminder", "weather", "health", "life"]
    description = "私人生活管家: 日历管理、事件提醒、健康建议、天气查询"

    def __init__(self, name: str = "Life", bus: SwarmBus = None, **kwargs):
        super().__init__(name=name, bus=bus, **kwargs)
        self._reminders: list[dict] = []
        self._load_reminders()

    def _register_handlers(self) -> None:
        self.swarm.on("life.request")(self._handle_life_request)
        self.swarm.on("life.query")(self._handle_query)
        self.swarm.on("life.reminder")(self._handle_reminder)

    def _load_reminders(self) -> None:
        path = os.path.join(PERSONAL_DATA_DIR, f"{self.name}_reminders.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._reminders = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._reminders = []

    def _save_reminders(self) -> None:
        path = os.path.join(PERSONAL_DATA_DIR, f"{self.name}_reminders.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._reminders, f, ensure_ascii=False, indent=2)

    def add_reminder(self, title: str, at_time: str, note: str = "") -> dict:
        """添加提醒"""
        self._reminders.append({
            "id": f"rem_{int(time.time() * 10000)}",
            "title": title,
            "at": at_time,
            "note": note,
            "created": datetime.now().isoformat(),
            "fired": False,
        })
        self._save_reminders()
        return {"status": "ok", "reminder": self._reminders[-1]}

    def get_upcoming(self, hours: int = 24) -> list[dict]:
        """获取即将到来的提醒"""
        now = datetime.now()
        upcoming = []
        for r in self._reminders:
            if r.get("fired"):
                continue
            try:
                at = datetime.fromisoformat(r["at"])
                if at >= now and (at - now).total_seconds() <= hours * 3600:
                    upcoming.append(r)
            except (ValueError, TypeError):
                pass
        return sorted(upcoming, key=lambda r: r.get("at", ""))

    def _handle_life_request(self, msg: Message) -> None:
        """处理生活请求"""
        payload = msg.payload or {}
        action = payload.get("action", "")
        result = {}

        if action == "add_reminder":
            result = self.add_reminder(
                title=payload.get("title", ""),
                at_time=payload.get("at", ""),
                note=payload.get("note", ""),
            )
        elif action == "get_upcoming":
            result = {"upcoming": self.get_upcoming(
                hours=payload.get("hours", 24)
            )}
        elif action == "get_weather":
            result = {"weather": "需要接入天气 API", "status": "not_configured"}
        elif action == "health_query":
            check = self.privacy_check(
                payload.get("query", ""), PersonalDomain.HEALTH
            )
            result = {"health_check": check, "note": "健康建议仅供参考，请咨询医生"}
        else:
            result = {"error": f"Unknown action: {action}"}

        self.send_to(msg.header.sender, result)

    def _handle_query(self, msg: Message) -> None:
        payload = msg.payload or {}
        query = payload.get("query", "")
        # 内容适宜性检查
        for domain in [PersonalDomain.HEALTH, PersonalDomain.LIFE]:
            check = self.privacy_check(query, domain)
            if check["blocked"]:
                self.send_to(msg.header.sender, {
                    "blocked": True, "reason": check["message"]
                })
                return
        self.send_to(msg.header.sender, {
            "response": f"收到生活查询: {query[:100]}...",
            "status": "acknowledged"
        })

    def _handle_reminder(self, msg: Message) -> None:
        """处理提醒触发"""
        payload = msg.payload or {}
        title = payload.get("title", "提醒")
        self.broadcast({
            "type": "reminder",
            "title": title,
            "note": payload.get("note", ""),
            "at": datetime.now().isoformat(),
        }, priority=Priority.HIGH)


class EntertainAgent(PersonalAgent):
    """娱乐推荐 — 影视/音乐/阅读/游戏"""

    role = "Entertain-Agent"
    capabilities = ["movie", "music", "book", "game", "recommendation"]
    description = "娱乐推荐: 影视、音乐、阅读、游戏推荐与发现"

    def __init__(self, name: str = "Entertain", bus: SwarmBus = None, **kwargs):
        super().__init__(name=name, bus=bus, **kwargs)
        # 娱乐偏好
        self._genre_prefs = self.get_pref("genre_prefs", {})

    def _register_handlers(self) -> None:
        self.swarm.on("entertain.request")(self._handle_request)
        self.swarm.on("entertain.recommend")(self._handle_recommend)

    def _handle_request(self, msg: Message) -> None:
        payload = msg.payload or {}
        content = payload.get("content", "")
        action = payload.get("action", "")

        # 内容适宜性检查
        check = self.privacy_check(content, PersonalDomain.ENTERTAINMENT)
        if check["blocked"]:
            self.send_to(msg.header.sender, {
                "blocked": True, "reason": check["message"]
            })
            return

        if check["level"] == NormLevel.WARN.value:
            # 追加警告但不阻止
            pass

        self.send_to(msg.header.sender, {
            "response": f"娱乐推荐请求已接收: {action}",
            "genre_prefs": self._genre_prefs,
            "status": "ok",
        })

    def _handle_recommend(self, msg: Message) -> None:
        """基于偏好生成推荐"""
        self.send_to(msg.header.sender, {
            "recommendations": [],
            "note": "推荐引擎需要接入外部 API (豆瓣/IMDb/Spotify)",
            "status": "not_configured",
        })

    def update_genre_prefs(self, genre: str, weight: float) -> None:
        """更新类型偏好"""
        self._genre_prefs[genre] = self._genre_prefs.get(genre, 0.5) + weight
        self._genre_prefs[genre] = max(0.0, min(1.0, self._genre_prefs[genre]))
        self.set_pref("genre_prefs", self._genre_prefs)


class SocialAgent(PersonalAgent):
    """社交管理 — 消息草拟/社交网络/语气调整"""

    role = "Social-Agent"
    capabilities = ["messaging", "draft", "tone", "social"]
    description = "社交管理: 消息草拟、语气调整、社交网络辅助"

    def __init__(self, name: str = "Social", bus: SwarmBus = None, **kwargs):
        super().__init__(name=name, bus=bus, **kwargs)
        self._message_history: list[dict] = []
        self._tone_profiles = self.get_pref("tone_profiles", {
            "default": "友好、自然",
            "formal": "正式、礼貌",
            "casual": "轻松、口语化",
            "professional": "专业、简洁",
        })

    def _register_handlers(self) -> None:
        self.swarm.on("social.request")(self._handle_request)
        self.swarm.on("social.draft")(self._handle_draft)

    def _handle_request(self, msg: Message) -> None:
        payload = msg.payload or {}
        content = payload.get("content", "")

        # 社交礼仪检查
        check = self.privacy_check(content, PersonalDomain.SOCIAL)
        if check["blocked"]:
            self.send_to(msg.header.sender, {
                "blocked": True, "reason": check["message"]
            })
            return

        self.send_to(msg.header.sender, {
            "response": "社交请求已接收",
            "tone_profiles": list(self._tone_profiles.keys()),
            "status": "ok",
        })

    def _handle_draft(self, msg: Message) -> None:
        """草拟消息 — 根据语气和场景"""
        payload = msg.payload or {}
        tone = payload.get("tone", "default")
        context = payload.get("context", "")

        result = {
            "draft": f"[{tone}语气草拟] {context[:50]}...",
            "tone": self._tone_profiles.get(tone, self._tone_profiles["default"]),
            "note": "需要 LLM 接入才能生成完整草稿",
        }
        self.send_to(msg.header.sender, result)


class ConciergeAgent(PersonalAgent):
    """综合门房 — 路由到 Life/Entertain/Social Agent

    作为私人域的统一入口，接收用户消息后:
      1. 内容分类 → Life/Entertain/Social
      2. 转发到对应 Agent
      3. 聚合响应
    """

    role = "Concierge-Agent"
    capabilities = ["router", "classify", "personal"]
    description = "私人综合门房: 统一入口，智能路由到生活/娱乐/社交 Agent"

    # 分类关键词映射
    _CLASSIFIER = {
        "life": ["日历", "提醒", "天气", "健康", "作息", "吃饭", "睡觉",
                 "运动", "跑步", "健身", "体重", "血压", "喝水", "吃药",
                 "闹钟", "设置", "时间", "出行", "交通", "购物"],
        "entertain": ["电影", "音乐", "书", "游戏", "推荐", "好看", "好听",
                      "好玩", "剧", "动漫", "综艺", "演唱会", "展览", "博物馆"],
        "social": ["消息", "回复", "微信", "短信", "邮件", "怎么说", "语气",
                   "草拟", "称呼", "朋友圈", "微博", "评论"],
    }

    def __init__(self, name: str = "Concierge", bus: SwarmBus = None,
                 ollama_model: str = "qwen2.5:0.5b", **kwargs):
        super().__init__(name=name, bus=bus, **kwargs)
        self._last_classification: dict[str, str] = {}
        self._ollama_model = ollama_model
        self._ollama_available: bool | None = None  # None=未检测

    def _register_handlers(self) -> None:
        self.swarm.on("concierge.classify")(self._handle_classify)
        self.swarm.on("concierge.route")(self._handle_route)

    def classify(self, content: str, use_llm: bool = True) -> dict[str, float]:
        """分类内容 → {life, entertain, social} 得分
        
        Args:
            content: 用户输入文本
            use_llm: 是否尝试LLM语义分类 (回退到关键词)
        """
        # 尝试 LLM 分类
        if use_llm:
            semantic = self._classify_llm(content)
            if semantic is not None:
                return semantic

        # 回退: 关键词分类
        scores = {"life": 0.0, "entertain": 0.0, "social": 0.0}
        for domain, keywords in self._CLASSIFIER.items():
            for kw in keywords:
                if kw in content:
                    scores[domain] += 1.0
        total = sum(scores.values()) or 1.0
        return {k: round(v / total, 3) for k, v in scores.items()}

    def _check_ollama(self) -> bool:
        """检测 Ollama 是否可用 (缓存结果)"""
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            import urllib.request
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                self._ollama_available = resp.status == 200
            return self._ollama_available
        except Exception:
            self._ollama_available = False
            return False

    def _classify_llm(self, content: str) -> dict | None:
        """使用 Ollama LLM 进行语义分类.
        
        Returns:
            {"life": float, "entertain": float, "social": float} or None (回退)
        """
        if not self._check_ollama():
            return None

        prompt = f"""Classify this message: "{content}"

Categories: life(calendar/reminder/weather/health/food/exercise/shopping), entertain(movie/music/game/book/show), social(message/reply/wechat/email/tone)

Return JSON: {{"category": "..."}}"""

        try:
            import urllib.request
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=json.dumps({
                    "model": self._ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 30,
                        "temperature": 0.1,
                    }
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                response_text = result.get("response", "").strip()

            # 提取 JSON — 兼容两种格式: A: {"category": "entertain"}  B: {"life": 0.0, ...}
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text)
            if json_match:
                raw_scores = json.loads(json_match.group(0))

                # 格式 A: category-based
                if "category" in raw_scores:
                    cat = raw_scores["category"].strip().lower()
                    result_scores = {"life": 0.0, "entertain": 0.0, "social": 0.0}
                    # 模糊匹配: "entertain/movie" → entertain, "life/health" → life
                    matched = False
                    for key in result_scores:
                        if key in cat or cat in key:
                            result_scores[key] = 1.0
                            matched = True
                            break
                    # 全不匹配 → 均匀分布
                    if not matched:
                        result_scores = {"life": 0.333, "entertain": 0.333, "social": 0.334}
                    total = sum(result_scores.values()) or 1.0
                    return {k: round(v / total, 3) for k, v in result_scores.items()}

                # 格式 B: score-based
                result_scores = {
                    "life": float(raw_scores.get("life", 0)),
                    "entertain": float(raw_scores.get("entertain", 0)),
                    "social": float(raw_scores.get("social", 0)),
                }
                total = sum(result_scores.values()) or 1.0
                return {k: round(v / total, 3) for k, v in result_scores.items()}

        except Exception:
            self._ollama_available = False

        return None

    def _handle_classify(self, msg: Message) -> None:
        """分类用户消息"""
        payload = msg.payload or {}
        content = payload.get("content", "")
        scores = self.classify(content, use_llm=self._check_ollama())

        # 确定最佳分类
        best = max(scores, key=scores.get)
        self._last_classification[msg.header.sender] = best

        self.send_to(msg.header.sender, {
            "classification": scores,
            "routed_to": best,
        })

    def _handle_route(self, msg: Message) -> None:
        """路由到具体 Agent"""
        payload = msg.payload or {}
        content = payload.get("content", "")
        scores = self.classify(content, use_llm=self._check_ollama())
        best = max(scores, key=scores.get)

        # 转发到目标 Agent
        target_map = {
            "life": "Life",
            "entertain": "Entertain",
            "social": "Social",
        }

        target = target_map.get(best, "Life")

        # 通过 SwarmBus 转发
        routed = Message(
            header=MessageHeader(
                msg_type=MessageType.INFO_COUPLING,
                sender=self.name,
                receiver=target,
                correlation_id=msg.msg_id,
            ),
            payload={
                "content": content,
                "classification_scores": scores,
                "routed_by": self.name,
            },
        )
        self.swarm.send(routed)
