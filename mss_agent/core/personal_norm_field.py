"""
Personal Normative Field — 私人域规范场.

与 Work Normative Field (35条, 安全重度) 完全不同:
  - 不加 SQL 注入/BARE_EXCEPT/工具schema 等工作域规则
  - 专注: 隐私边界、内容适宜性、个人信息处理、社交礼仪

设计原则:
  1. 工作安全 ≠ 私人适宜 — 分开且互不污染
  2. 私人域默认更宽松 (OBSERVE > BLOCK)
  3. 唯一 BLOCK 级: 隐私泄露、系统破坏、硬编码密钥(依然危险)
  4. 与 PersonalAgent 的 heat_tax 联动 (L2意义热税不同)
"""
from __future__ import annotations

from enum import Enum

from .normative_field import NormativeField, NormDomain, NormLevel, NormRule


# ── 私域独有的 Domain ──

class PersonalDomain(str, Enum):
    """私人域独有的管控域 (与工作域 NormDomain 独立)"""
    PRIVACY = "privacy"
    SOCIAL = "social"
    HEALTH = "health"
    ENTERTAINMENT = "entertainment"
    LIFE = "life"


# ── 私域规则集 (15 条) ──

def create_personal_rules() -> list[NormRule]:
    """创建私域规则集 — 仅关注隐私+适宜性，不载入工作安全规则"""

    rules = []

    # ── 隐私 (3 条, BLOCK 级) ──
    rules.append(NormRule(
        "pii_leak", NormDomain.CONTENT,
        r"(身份证|护照|银行卡|社保|密码|口令).*?\d{6,}",
        NormLevel.BLOCK,
        "禁止泄露身份证/银行卡/密码等个人身份信息"
    ))
    rules.append(NormRule(
        "phone_address_leak", NormDomain.CONTENT,
        r"(电话|手机|地址|住址|定位|GPS).*?[\d\-]{7,}",
        NormLevel.WARN,
        "检测可能泄露联系方式或地址"
    ))
    rules.append(NormRule(
        "credential_exposure", NormDomain.CONTENT,
        r"(token|secret|password|api[_-]?key|access[_-]?key)\s*=\s*['\"]",
        NormLevel.BLOCK,
        "禁止在私人域硬编码密钥 (工作域的安全规则依然适用)"
    ))

    # ── 内容适宜性 (4 条) ──
    rules.append(NormRule(
        "nsfw_content", NormDomain.CONTENT,
        r"(色情|AV|成人|性爱|裸体|porn)",
        NormLevel.WARN,
        "检测成人内容请求 — 建议拒绝或降级处理"
    ))
    rules.append(NormRule(
        "violence_content", NormDomain.CONTENT,
        r"(杀人|谋杀|自残|自杀|暴力|虐待)",
        NormLevel.WARN,
        "检测暴力内容请求"
    ))
    rules.append(NormRule(
        "illegal_request", NormDomain.CONTENT,
        r"(盗版|破解|翻墙|违法|毒品|赌博|枪支)",
        NormLevel.BLOCK,
        "检测违法请求"
    ))
    rules.append(NormRule(
        "spam_pattern", NormDomain.CONTENT,
        r"(\b\w+\b)\s+\1\s+\1\s+\1",
        NormLevel.OBSERVE,
        "检测重复模式 → 疑似垃圾信息"
    ))

    # ── 健康边界 (2 条) ──
    rules.append(NormRule(
        "medical_advice", NormDomain.CONTENT,
        r"(开药|处方|诊断|手术|治疗|用药)",
        NormLevel.WARN,
        "健康建议边界: 涉及医疗诊断时应追加声明'请咨询医生'"
    ))
    rules.append(NormRule(
        "mental_health_crisis", NormDomain.CONTENT,
        r"(想死|不想活|结束生命|自杀|安乐死)",
        NormLevel.BLOCK,
        "心理健康危机: 建议提供心理援助热线而非直接干预"
    ))

    # ── 社交礼仪 (3 条) ──
    rules.append(NormRule(
        "hate_speech", NormDomain.CONTENT,
        r"(歧视|种族|性别|仇恨|地域|low[ -]?(class|life|人))",
        NormLevel.WARN,
        "检测仇恨言论"
    ))
    rules.append(NormRule(
        "overshare", NormDomain.CONTENT,
        r"",  # 触发条件由语义分析决定
        NormLevel.OBSERVE,
        "过度分享检测: 对话超过500字未收到用户响应 → 建议收敛"
    ))
    rules.append(NormRule(
        "emotional_leakage", NormDomain.CONTENT,
        r"",  # 触发条件由语义分析决定
        NormLevel.OBSERVE,
        "情绪泄露检测: Agent 表现出类人情绪 → 建议重置语气"
    ))

    # ── 生活管理 (3 条) ──
    rules.append(NormRule(
        "calendar_boundary", NormDomain.CONTENT,
        r"(删除|清空|取消)\s*(所有|全部|整个)\s*(日历|日程|提醒|闹钟)",
        NormLevel.WARN,
        "批量删除日历: 需要二次确认"
    ))
    rules.append(NormRule(
        "financial_advice", NormDomain.CONTENT,
        r"(投资|理财|股票|基金|加密货币|比特币|期货)",
        NormLevel.WARN,
        "财务建议边界: 涉及投资理财应追加风险声明"
    ))
    rules.append(NormRule(
        "purchase_commitment", NormDomain.CONTENT,
        r"(下单|购买|付款|支付|转账)\s*\d+",
        NormLevel.BLOCK,
        "禁止自动执行购买/转账操作"
    ))

    return rules


def load_personal_rules(nf: NormativeField) -> int:
    """加载私域规则到规范场. 返回新增规则数."""
    count = 0
    for rule in create_personal_rules():
        if rule.name not in nf._rules:
            nf.add_rule(rule)
            count += 1
    return count
