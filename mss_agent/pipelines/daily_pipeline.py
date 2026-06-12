"""
日常管线 — 与意义场管线分离的独立输出通道.

核心原则:
  1. 日常管线产出的文本不进入意义场管线作为约束
  2. 意义场管线的守卫/禁词不压制日常管线的自然语言
  3. 仅通过 DailyPipeline gate 进行节奏控制和场景分配
  4. 僭越防火墙: 日常输出 ≠ 意义场输入

两种拓扑:
  Type A (分离型): 日常→主剧情, 独立运行, 反差铺垫
  Type B (嵌入型): 日常即主线, 并行但独立, 互不污染

Usage:
    pipe = DailyPipeline(agent=my_agent)
    # Type A: pre-plot calm
    scene = pipe.generate("patrol", mode="separated")
    # Type B: embedded daily
    scene = pipe.generate("cook_and_talk", mode="embedded")
"""
from dataclasses import dataclass, field
from typing import Optional, Literal
import random
import time


# ============================================================
# 微起伏类型 — 不是"高潮"，是自然对话节奏
# ============================================================

MICRO_FLUCTUATION_TYPES = {
    "gossip": "聊不在场第三人的八卦 — 语气轻松，话题跳跃",
    "consensus": "反复确认已经说好的事 — 真实人类习惯，不是bug是feature",
    "shared_silence": "没人说话但沉默有意义 — 并肩看远方/听风声/整理思绪",
    "sudden_serious": "玩笑中一个提问让气氛微变 — 不一定是冲突，只是换频",
    "banter": "无信息量的纯社交吐槽 — 今天真热/这破刀/你看他那样",
    "circular_talk": "一个话题绕了三圈又回来 — 不是啰嗦，是人类安全感的节奏",
    "inside_joke": "只属于这两个人的梗 — 不需要解释，观众能猜到有历史",
    "observation_drift": "看着某物发呆走神 — 不是叙事需要，就是人走着走着会想别的",
}

# ============================================================
# 活动模板池 — 按设定分类
# ============================================================

ACTIVITY_POOL = {
    "wuxia": [
        "擦剑", "巡逻", "检查伤势", "生火做饭", "整理行囊",
        "补渔网", "刷马", "晾衣服", "修屋顶", "站岗",
        "磨药", "抄写经书", "练习剑法", "编织草鞋", "酿酒",
    ],
    "post_apocalyptic": [
        "分拣废金属", "过滤雨水", "修设备", "找物资",
        "加固围栏", "看地图", "检查弹药", "给电池充电",
        "种菜", "记录日志", "修理水泵", "蒸馏净水",
    ],
    "scifi": [
        "检查引擎", "看数据曲线", "修拉链", "调天线",
        "倒咖啡", "校准传感器", "给植物补光", "写日志",
        "擦镜头", "测试样本", "清理过滤器", "调整轨道",
    ],
    "modern": [
        "抽烟看窗外", "整理文件夹", "泡茶", "修自行车",
        "晾床单", "喂猫", "擦桌子上的咖啡印",
        "翻看旧笔记", "给手机充电", "修漏水的水龙头",
    ],
}

# ============================================================
# 微起伏调度器 — 不是所有场景都要"高潮"
# ============================================================

@dataclass
class FluctuationSchedule:
    """场景节奏调度."""
    scene_duration_beats: int = 12  # 约 12 个叙事节拍
    fluctuation_density: float = 0.25  # 25% 的节拍有微起伏
    silence_budget: int = 2  # 每组至少 2 个节拍是沉默/空白
    gossip_prob: float = 0.15
    sudden_serious_prob: float = 0.08  # 突然严肃不能太多
    banter_prob: float = 0.20  # 废话/吐槽是最常见的

    def generate_schedule(self) -> list:
        """生成一个场景的节拍序列."""
        beats = []
        for i in range(self.scene_duration_beats):
            r = random.random()
            if r < self.silence_budget / self.scene_duration_beats:
                beats.append({"beat_id": i, "type": "silence", "desc": "集体沉默/空白节拍"})
            elif r < self.fluctuation_density:
                # 按概率分配微起伏类型
                sub_r = random.random()
                if sub_r < self.gossip_prob:
                    beats.append({"beat_id": i, "type": "gossip"})
                elif sub_r < self.gossip_prob + self.sudden_serious_prob:
                    beats.append({"beat_id": i, "type": "sudden_serious"})
                elif sub_r < self.gossip_prob + self.sudden_serious_prob + self.banter_prob:
                    beats.append({"beat_id": i, "type": "banter"})
                else:
                    beats.append({"beat_id": i, "type": random.choice(["consensus", "observation_drift", "circular_talk", "inside_joke"])})
            else:
                beats.append({"beat_id": i, "type": "activity", "desc": "继续手上的日常活动"})
        return beats


# ============================================================
# 管线分离核心
# ============================================================

class PipelineFirewall:
    """
    僭越防火墙 — 日常管线 ≠ 意义场管线.

    规则:
      1. 日常管线的输出标记为 'daily' scope
      2. 意义场管线只读取 'meaning' scope 的约束
      3. 两管线的 guards/forbidden_words 完全独立
      4. 交叉引用必须通过调度器显式调用
    """

    def __init__(self):
        self.daily_scope: dict = {}   # 日常管线私有状态
        self.meaning_scope: dict = {}  # 意义场管线私有状态
        self.cross_refs: list = []     # 合法交叉引用记录

    def write_daily(self, key: str, value):
        """只写日常 scope."""
        self.daily_scope[key] = value

    def write_meaning(self, key: str, value):
        """只写意义场 scope."""
        self.meaning_scope[key] = value

    def cross_reference(self, from_pipeline: str, to_key: str, reason: str):
        """显式交叉引用 — 必须提供理由."""
        ref = {
            "from": from_pipeline,
            "to": to_key,
            "reason": reason,
            "ts": time.time(),
        }
        self.cross_refs.append(ref)
        return ref

    def audit(self) -> dict:
        """审计管线隔离状态."""
        daily_keys = set(self.daily_scope.keys())
        meaning_keys = set(self.meaning_scope.keys())
        overlap = daily_keys & meaning_keys
        return {
            "daily_entries": len(daily_keys),
            "meaning_entries": len(meaning_keys),
            "overlap": list(overlap),  # 应为空
            "cross_refs": len(self.cross_refs),
            "isolation_ok": len(overlap) == 0,
        }


# ============================================================
# 日常管线主类
# ============================================================

class DailyPipeline:
    """
    日常管线 — 生成设定内自然日常场景.

    Args:
        agent: MSSAgent 实例 (携带热税/Δ/记忆)
        setting: 设定类型 (wuxia/post_apocalyptic/scifi/modern)
    """

    def __init__(self, agent=None, setting: str = "wuxia"):
        self.agent = agent
        self.setting = setting
        self.firewall = PipelineFirewall()
        self.scheduler = FluctuationSchedule()
        self.activity_pool = ACTIVITY_POOL.get(setting, ACTIVITY_POOL["modern"])
        self.history: list = []

    def generate(self, activity: str, mode: Literal["separated", "embedded"] = "separated",
                 character_count: int = 2) -> dict:
        """
        生成一个日常场景.

        Args:
            activity: 活动名 (擦剑/巡逻/做饭...)
            mode: 'separated'=Type A 分离型 / 'embedded'=Type B 嵌入型
            character_count: 角色数
        """
        schedule = self.scheduler.generate_schedule()

        # 随机选择微起伏类型（不是每个节拍都有）
        fluctuations = [
            b for b in schedule
            if b["type"] not in ("silence", "activity")
        ]

        scene = {
            "setting": self.setting,
            "activity": activity,
            "character_count": character_count,
            "mode": mode,
            "schedule": schedule,
            "fluctuations": fluctuations,
            "fluctuation_types": list(set(b["type"] for b in fluctuations)),
            "is_embedded": mode == "embedded",
            "pipeline_scope": "daily",
        }

        # 写入日常 scope
        self.firewall.write_daily(f"scene_{len(self.history)}", scene)
        self.history.append(scene)

        # 如果是嵌入型，需要通知意义场管线（通过合法交叉引用）
        if mode == "embedded":
            self.firewall.cross_reference(
                from_pipeline="daily",
                to_key=f"scene_{len(self.history)-1}",
                reason="嵌入型日常场景携带叙事推进，需意义场管线感知但不可干预"
            )

        return scene

    def generate_context_prompt(self, activity: str, mode: Literal["separated", "embedded"] = "separated") -> str:
        """
        生成日常感增强 prompt — 可直接喂给 SFT 模型.
        核心：鼓励"一边做事一边自然对话 + 微起伏".
        """
        mode_hint = ""
        if mode == "separated":
            mode_hint = "这是主剧情前的宁静日常，不要塞入剧情冲突。"
        else:
            mode_hint = "这段日常本身携带微弱的叙事推进，但保持自然不做作。"

        prompt = f"""为视频提示词添加日常活动中的自然交互（一边做事一边说话）。

设定: {self.setting}
活动: {activity}
要求:
1. 活动（{activity}）始终在画面中进行，与对话交替推进
2. 对话自然、口语化，包含微起伏：吐槽/八卦/沉默/突然严肃/废话
3. 不要强行塞入高潮或剧情冲突
4. {mode_hint}
5. 节奏感：有快有慢，有说有停，像真实人类的日常

增强后的画面描述:"""
        return prompt

    def audit(self) -> dict:
        """审计管线健康状态."""
        return self.firewall.audit()
