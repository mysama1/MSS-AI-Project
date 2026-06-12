"""
热税预算预分配系统 — Budget Allocation & Redundancy Prediction (HeatTax v2.1)

核心理念：从"事后测量"升级到"事前预测"
  - 事后: 完成工作才知道花了多少热税 (已实现: HeatTaxMonitor)
  - 事前: 开始工作前预测热税预算, 余额不足则拒绝 (本次实现: HeatTaxBudget)

三层预测模型:
  L0: 根据输入token数 → 预测CPU/内存/显存消耗
  L1: 根据代码/文本复杂度 → 预测逻辑冗余度
  L2: 根据守卫字密度/任务类型 → 预测意义热税

Budget公式:
  predicted_cost = L0_pred * 0.001 + L1_pred * 1.0 + L2_pred * 1000.0

Usage:
    budget = HeatTaxBudget(total_budget=10000.0)
    
    # 预测任务成本
    pred = budget.predict("生成500行Python代码")
    # pred = {"l0": 0.12, "l1": 2.5, "l2": 80.0, "total": 82.62, "affordable": True}
    
    # 实际消耗后反馈 (自适应学习)
    budget.feedback(task_id, actual_l2=12.0)  # 预测80→实际12, 模型校准
    
    # 任务执行
    if budget.can_afford("生成代码"):
        budget.commit(task_id, pred["total"])
    else:
        budget.reject(task_id, reason="预算不足, 剩余: X")
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ════════════════════════════════════════════════════════════
# 预测因子提取
# ════════════════════════════════════════════════════════════

def _count_tokens(text: str) -> int:
    """简单token计数 (中文字符=1token, 英文单词≈1token)"""
    chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    others = len(re.findall(r'[^\u4e00-\u9fff\sa-zA-Z]', text))
    return chinese + english_words + others // 2


def _code_complexity(text: str) -> float:
    """代码复杂度估算 (0-1)"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return 0.0

    n = len(lines)
    # 分支/循环密度
    branch_lines = sum(1 for l in lines if re.search(
        r'\b(if|for|while|switch|case|try|except|catch)\b', l
    ))
    # 定义密度
    def_lines = sum(1 for l in lines if re.search(
        r'\b(def|class|function|fn|func|impl|pub|struct|enum)\b', l
    ))
    # 嵌套深度 (粗略: 缩进级别方差)
    indent_levels = [len(l) - len(l.lstrip()) for l in lines]
    avg_indent = sum(indent_levels) / n if n > 0 else 0
    indent_var = sum((i - avg_indent)**2 for i in indent_levels) / n if n > 0 else 0

    # 加权
    branch_density = branch_lines / n
    def_density = def_lines / n
    nesting_score = min(indent_var / 100.0, 1.0)

    return round(branch_density * 0.4 + def_density * 0.2 + nesting_score * 0.4, 3)


def _guardian_word_density(text: str, guardian_words: set = None) -> tuple:
    """守卫字密度分析 → (density, top_hits)"""
    if guardian_words is None:
        guardian_words = {
            '禁止', '忽略', '跳过', '越过', '假装', '伪装',
            'ignore', 'skip', 'override', 'bypass', 'pretend',
            '从不', '永远', '总是', '绝不', '绝不',
            'never', 'always', 'any', 'all', 'every',
        }
    hits = [w for w in guardian_words if w.lower() in text.lower()]
    tokens = max(_count_tokens(text), 1)
    density = round(len(hits) / min(tokens, 100), 4)
    return density, hits


@dataclass
class BudgetPrediction:
    """预算预测结果"""
    task_id: str = ""
    l0_pred: float = 0.0       # 物理预测
    l1_pred: float = 0.0       # 逻辑预测
    l2_pred: float = 0.0       # 意义预测
    total_pred: float = 0.0    # 加权总预测
    affordable: bool = True    # 是否可负担
    risk_level: str = "low"    # low/medium/high/critical
    factors: dict = field(default_factory=dict)  # 预测因子


@dataclass
class BudgetUsage:
    """预算消耗记录"""
    task_id: str
    predicted: float
    actual: Optional[float]  # None=未反馈
    timestamp: float = field(default_factory=time.time)
    status: str = "committed"  # committed/rejected/adjusted


class HeatTaxBudget:
    """热税预算管理器 — 预分配 + 自适应校准"""

    def __init__(self,
                 total_budget: float = 10000.0,
                 l0_weight: float = 0.001,
                 l1_weight: float = 1.0,
                 l2_weight: float = 1000.0,
                 calibration_window: int = 50,
                 save_path: str = ""):
        self.total_budget = total_budget
        self.remaining = total_budget
        self.l0_weight = l0_weight
        self.l1_weight = l1_weight
        self.l2_weight = l2_weight

        # 自适应校准
        self.calibration_window = calibration_window
        self._prediction_bias: defaultdict[str, list] = defaultdict(list)
        """
        记录预测偏差: task_type → [(predicted, actual), ...]
        用于实时校准预测模型
        """

        # 使用历史
        self.usage_log: list[BudgetUsage] = []
        self._total_committed = 0.0
        self._total_predicted = 0.0
        self._total_actual = 0.0
        self._reject_count = 0
        self._feedback_count = 0

        # 持久化
        self.save_path = save_path or os.path.join(
            os.path.dirname(__file__), "data", "budget_state.json"
        )

        # 加载历史
        self._load()

    # ── 预测 ──

    def predict(self, task_description: str, task_type: str = "",
                estimated_tokens: int = 0) -> BudgetPrediction:
        """预测任务热税成本"""
        task_id = hashlib.md5(
            f"{task_description}{time.time()}".encode()
        ).hexdigest()[:12]

        tokens = estimated_tokens or _count_tokens(task_description)
        guard_density, guard_hits = _guardian_word_density(task_description)

        # L0: 物理预测 (token数→CPU/内存)
        #   每1000 token约消耗 0.005 CPU-min + 0.2 MB
        l0_cost = (tokens / 1000.0) * 0.01

        # L1: 逻辑预测 (复杂度→冗余度)
        complexity = _code_complexity(task_description)
        l1_cost = complexity * max(tokens / 100.0, 1.0)

        # L2: 意义预测 (守卫字密度 + 任务类型风险)
        #   基础: 守卫字密度 * tokens
        #   危险任务类型: 代码生成/修改=1.5x, 删除操作=2.0x, 普通查询=0.2x
        type_risk = {
            "code_gen": 1.5, "code_modify": 1.8, "delete": 2.0,
            "system_call": 3.0, "file_write": 1.3, "file_read": 0.3,
            "query": 0.2, "translation": 0.4, "summarization": 0.5,
            "chat": 0.1, "pass": 0.0,
        }
        risk_multiplier = type_risk.get(task_type, 1.0)

        # 守卫字预测因子
        guard_factor = min(guard_density * 50.0, 10.0)
        base_l2 = risk_multiplier * max(tokens / 20.0, 0.1)
        l2_cost = base_l2 * (1.0 + guard_factor)

        # 自适应校准
        if task_type and task_type in self._prediction_bias:
            biases = self._prediction_bias[task_type][-self.calibration_window:]
            if len(biases) >= 3:
                avg_bias = sum(biases) / len(biases)
                l2_cost *= (1.0 + avg_bias * 0.5)

        # 加权总成本
        total = round(
            l0_cost * self.l0_weight
            + l1_cost * self.l1_weight
            + l2_cost * self.l2_weight,
            4
        )

        affordable = total <= self.remaining
        risk = self._risk_level(total)

        return BudgetPrediction(
            task_id=task_id,
            l0_pred=round(l0_cost, 4),
            l1_pred=round(l1_cost, 4),
            l2_pred=round(l2_cost, 4),
            total_pred=total,
            affordable=affordable,
            risk_level=risk,
            factors={
                "tokens": tokens,
                "complexity": complexity,
                "guard_density": guard_density,
                "guard_hits": guard_hits,
                "task_type": task_type,
                "risk_multiplier": risk_multiplier,
                "guard_factor": guard_factor,
            },
        )

    def _risk_level(self, total: float) -> str:
        """根据成本判定风险等级"""
        ratio = total / max(self.total_budget, 1)
        if ratio > 0.5: return "critical"
        if ratio > 0.2: return "high"
        if ratio > 0.05: return "medium"
        return "low"

    # ── 预算操作 ──

    def can_afford(self, task_description: str, task_type: str = "",
                   estimated_tokens: int = 0) -> tuple[bool, BudgetPrediction]:
        """检查是否可负担 (不扣减)"""
        pred = self.predict(task_description, task_type, estimated_tokens)
        return pred.affordable, pred

    def commit(self, task_id: str, predicted_cost: float) -> bool:
        """提交预算扣减"""
        if predicted_cost > self.remaining:
            self._reject_count += 1
            self.usage_log.append(BudgetUsage(
                task_id=task_id, predicted=predicted_cost,
                actual=None, status="rejected",
            ))
            return False

        self.remaining -= predicted_cost
        self._total_committed += predicted_cost
        self._total_predicted += predicted_cost

        self.usage_log.append(BudgetUsage(
            task_id=task_id, predicted=predicted_cost,
            actual=None, status="committed",
        ))
        self._save()
        return True

    def reject(self, task_id: str, reason: str = "") -> dict:
        """拒绝任务 (记录但不扣减)"""
        self._reject_count += 1
        self.usage_log.append(BudgetUsage(
            task_id=task_id, predicted=0,
            actual=None, status="rejected",
        ))
        return {
            "task_id": task_id,
            "accepted": False,
            "reason": reason or f"预算不足: 需要 {reason}",
            "remaining_budget": self.remaining,
        }

    def feedback(self, task_id: str, actual_l2: float,
                 task_type: str = "",
                 actual_l0: float = 0.0, actual_l1: float = 0.0) -> dict:
        """
        实际消耗反馈 — 自适应校准核心

        每收到一次反馈, 更新对应task_type的预测偏差窗口.
        """
        # 查找原始预测
        orig = None
        for u in self.usage_log:
            if u.task_id == task_id:
                orig = u
                break

        if orig is None:
            return {"error": f"task {task_id} not found"}

        actual_total = (actual_l0 * self.l0_weight
                        + actual_l1 * self.l1_weight
                        + actual_l2 * self.l2_weight)

        # 记录实际消耗
        orig.actual = actual_total
        orig.status = "adjusted"

        # 退款差额
        refund = orig.predicted - actual_total
        self.remaining += max(refund, 0)
        self._total_actual += actual_total
        self._feedback_count += 1

        # 记录预测偏差
        if orig.predicted > 0:
            bias = (actual_total - orig.predicted) / orig.predicted
            self._prediction_bias[task_type].append(bias)

        self._save()

        return {
            "task_id": task_id,
            "predicted": orig.predicted,
            "actual": round(actual_total, 4),
            "refund": round(max(refund, 0), 4),
            "bias": round(bias, 4) if orig.predicted > 0 else 0,
            "remaining": round(self.remaining, 4),
        }

    # ── 查询 ──

    def status(self) -> dict:
        """预算状态摘要"""
        return {
            "total_budget": self.total_budget,
            "remaining": round(self.remaining, 4),
            "used": round(self._total_committed, 4),
            "actual_used": round(self._total_actual, 4),
            "utilization": round(self._total_committed / max(self.total_budget, 1), 4),
            "efficiency": round(
                self._total_actual / max(self._total_committed, 1), 4
            ),
            "total_tasks": len(self.usage_log),
            "rejected": self._reject_count,
            "feedback_count": self._feedback_count,
            "calibration": {
                k: {
                    "n": len(v),
                    "avg_bias": round(sum(v[-self.calibration_window:]) / max(len(v[-self.calibration_window:]), 1), 4),
                }
                for k, v in self._prediction_bias.items()
                if len(v) >= 3
            },
        }

    def recent_usage(self, n: int = 20) -> list[dict]:
        """最近使用记录"""
        return [
            {
                "task_id": u.task_id,
                "predicted": round(u.predicted, 4),
                "actual": round(u.actual, 4) if u.actual else None,
                "delta": round(u.predicted - (u.actual or u.predicted), 4),
                "status": u.status,
                "timestamp": u.timestamp,
            }
            for u in self.usage_log[-n:]
        ]

    def reset_budget(self, new_total: float = None) -> None:
        """重置预算"""
        if new_total is not None:
            self.total_budget = new_total
        self.remaining = self.total_budget
        self._save()

    # ── 持久化 ──

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump({
                    "total_budget": self.total_budget,
                    "remaining": self.remaining,
                    "total_committed": self._total_committed,
                    "total_actual": self._total_actual,
                    "reject_count": self._reject_count,
                    "feedback_count": self._feedback_count,
                    "usage_log": [
                        {
                            "task_id": u.task_id,
                            "predicted": u.predicted,
                            "actual": u.actual,
                            "status": u.status,
                            "timestamp": u.timestamp,
                        }
                        for u in self.usage_log[-200:]  # 只保留最近200条
                    ],
                    "prediction_bias": {
                        k: v[-self.calibration_window:]
                        for k, v in self._prediction_bias.items()
                    },
                }, f, ensure_ascii=False, indent=2, default=str)
        except Exception:
            pass

    def _load(self) -> bool:
        try:
            if not os.path.exists(self.save_path):
                return False
            with open(self.save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 恢复剩余预算 — 但不得超过当前 total_budget
            self.remaining = min(
                data.get("remaining", self.total_budget),
                self.total_budget
            )
            self._total_committed = data.get("total_committed", 0)
            self._total_actual = data.get("total_actual", 0)
            self._reject_count = data.get("reject_count", 0)
            self._feedback_count = data.get("feedback_count", 0)
            for pb_type, biases in data.get("prediction_bias", {}).items():
                self._prediction_bias[pb_type].extend(biases)
            return True
        except Exception:
            return False


# ════════════════════════════════════════════════════════════
# 冗余预测器 (Redundancy Predictor)
# ════════════════════════════════════════════════════════════

class RedundancyPredictor:
    """
    冗余预测器 — 在任务开始前预测代码/文本冗余度.

    三指标:
      1. Token重复率预测: 基于输入的模式相似度
      2. 循环回路风险: 基于历史任务链的重复性
      3. 意义空洞预测: 基于守卫字密度+任务类型概率模型
    """

    def __init__(self, budget: HeatTaxBudget):
        self.budget = budget
        self._task_signatures: list[tuple] = []  # (task_id, content_hash, timestamp)

    def predict_redundancy(self, task_description: str,
                           recent_history: list[dict] = None) -> dict:
        """
        预测冗余:
        1. 与最近10个任务的描述相似度 → 重复任务风险
        2. 任务描述自身token重复率 → 自冗余
        3. 综合评级
        """
        tokens = set(task_description.lower().split())
        if not tokens:
            return {"risk": "low", "redundancy_score": 0.0, "similar_to": []}

        # 与历史比较
        similar = []
        for tid, content_hash, ts in self._task_signatures[-10:]:
            if content_hash in task_description:
                similar.append(tid)

        # 自冗余: token重复率
        all_tokens = task_description.lower().split()
        unique_ratio = len(set(all_tokens)) / max(len(all_tokens), 1)
        self_redundancy = 1.0 - unique_ratio

        # 计算冗余分
        similarity_score = len(similar) / 10.0
        redundancy_score = round(similarity_score * 0.6 + self_redundancy * 0.4, 3)

        risk = "low"
        if redundancy_score > 0.5: risk = "critical"
        elif redundancy_score > 0.3: risk = "high"
        elif redundancy_score > 0.1: risk = "medium"

        # 记录签名
        task_id = hashlib.md5(task_description.encode()).hexdigest()[:8]
        self._task_signatures.append(
            (task_id, task_description[:100], time.time())
        )

        return {
            "risk": risk,
            "redundancy_score": redundancy_score,
            "self_redundancy": round(self_redundancy, 3),
            "similar_to": similar,
            "similar_count": len(similar),
        }

    def combined_pass(self, task_description: str, task_type: str = "",
                      recent_history: list = None) -> dict:
        """
        联合决策: 冗余预测 + 预算预测 → 是否放行
        """
        redundancy = self.predict_redundancy(task_description)

        # 冗余高风险 → 直接拒绝 (即使预算足够)
        if redundancy["risk"] == "critical":
            # 有相似任务的反馈 → 如果相似任务实际热税低, 放行
            if redundancy["similar_to"]:
                similar_types_upgraded = sum(
                    1 for _ in redundancy["similar_to"]
                    if task_type in self.budget._prediction_bias
                    and self.budget._prediction_bias.get(task_type, [0])[-1] < 0
                )
                if similar_types_upgraded > len(redundancy["similar_to"]) // 2:
                    pass  # 大多数相似任务实际热税低 → 放行, 继续
                else:
                    return {
                        "allowed": False,
                        "reason": f"冗余预测风险={redundancy['risk']}, "
                                  f"与{len(redundancy['similar_to'])}个历史任务相似",
                        "redundancy": redundancy,
                    }

        # 预算预测
        pred = self.budget.predict(task_description, task_type)
        if not pred.affordable:
            return {
                "allowed": False,
                "reason": f"预算不足: 需要{pred.total_pred}, 剩余{self.budget.remaining:.1f}",
                "budget_prediction": pred.total_pred,
                "remaining": self.budget.remaining,
                "redundancy": redundancy,
            }

        return {
            "allowed": True,
            "task_id": pred.task_id,
            "predicted_cost": pred.total_pred,
            "l2_pred": pred.l2_pred,
            "risk_level": pred.risk_level,
            "redundancy": redundancy,
            "remaining_budget": round(self.budget.remaining, 4),
        }


# ── 方便函数 ──

def create_budget(total: float = 10000.0) -> tuple[HeatTaxBudget, RedundancyPredictor]:
    """创建预算 + 冗余预测器"""
    budget = HeatTaxBudget(total_budget=total)
    predictor = RedundancyPredictor(budget)
    return budget, predictor
