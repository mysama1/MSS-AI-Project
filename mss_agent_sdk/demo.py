"""
MSS-Agent SDK v0.1 - Demo示例
展示如何使用SDK进行文本审计和意义锚定
"""

import sys
sys.path.insert(0, r'C:\MSS-AI-Project')

from mss_agent_sdk import MSSClient, mss_audit, mss_anchor
from mss_agent_sdk.types import AnchorLevel, AuditResult

# ========== 示例1: 基础客户端使用 ==========
print("=" * 60)
print("示例1: 基础客户端使用")
print("=" * 60)

client = MSSClient()

# 审计一段文本
text = "因为量子纠缠是非定域的，所以我们可以瞬间传递信息。"
result = client.audit(text)

print(f"原文: {text}")
print(f"逻辑刚性 M_L: {result.logic_rigidity:.2f}")
print(f"层级: {result.layer}")
print(f"置信度: {result.confidence.value}")
print(f"热税 γ: {result.heat_tax:.2f}")
print(f"通过状态: {'✅' if result.passed else '❌'}")
if result.suggestions:
    print(f"建议: {result.suggestions[0]}")
print()

# ========== 示例2: 三层意义锚定 ==========
print("=" * 60)
print("示例2: 三层意义锚定")
print("=" * 60)

# 客观锚定
obj_anchor = client.anchor(
    text="量子力学描述了微观粒子的行为",
    level=AnchorLevel.OBJECTIVE
)
print(f"客观锚定: {obj_anchor.text}")
print(f"层级: {obj_anchor.level}")
print()

# 实在锚定
real_anchor = client.anchor(
    text="双缝实验观测结果",
    level=AnchorLevel.ACTUAL
)
print(f"实在锚定: {real_anchor.text}")
print()

# 主观锚定
subj_anchor = client.anchor(
    text="我认为量子力学是完备的",
    level=AnchorLevel.SUBJECTIVE
)
print(f"主观锚定: {subj_anchor.text}")
print()

# ========== 示例3: 装饰器自动审计 ==========
print("=" * 60)
print("示例3: 装饰器自动审计")
print("=" * 60)

@mss_audit()
def generate_report(topic: str) -> str:
    """生成关于某个主题的报告"""
    return f"{topic}是一个非常重要的研究领域，我们需要终极解决方案。"

# 调用被装饰的函数
report = generate_report("AI安全")
print(f"生成报告: {report}")
print()

# ========== 示例4: 装饰器自动锚定 ==========
print("=" * 60)
print("示例4: 装饰器自动锚定")
print("=" * 60)

@mss_anchor(level=AnchorLevel.OBJECTIVE)
def state_axiom() -> str:
    """陈述MSS公理"""
    return "信息是宇宙的本体，物理现实是信息的显化投影。"

axiom = state_axiom()
print(f"公理陈述: {axiom}")
print()

# ========== 示例5: 批量审计 ==========
print("=" * 60)
print("示例5: 批量审计")
print("=" * 60)

texts = [
    "因为A所以B，这是一个有效的推理。",
    "这个方案是完美的，没有任何缺陷。",
    "∀x∈S, P(x)⇒Q(x)，根据公理A1可证。",
]

for i, text in enumerate(texts, 1):
    result = client.audit(text)
    status = "✓" if result.passed else "✗"
    print(f"{status} 文本{i}: M_L={result.logic_rigidity:.2f}, 热税={result.heat_tax:.2f}")

print()

# ========== 示例6: 生成Markdown报告 ==========
print("=" * 60)
print("示例6: 生成Markdown报告")
print("=" * 60)

report_md = result.to_markdown()
print(report_md[:500] + "...")
print()

# ========== 示例7: 逻辑刚性估算 ==========
print("=" * 60)
print("示例7: 逻辑刚性估算")
print("=" * 60)

sample_texts = [
    ("∀x∈S, P(x)⇒Q(x), ∴R", "形式化证明"),
    ("因为A所以B，如果C那么D", "因果推理"),
    ("这个方案绝对完美", "绝对化表述"),
]

for text, desc in sample_texts:
    rigidity = client._estimate_logic_rigidity(text)
    print(f"{desc}: M_L={rigidity:.2f}")

print()

# ========== 示例8: 热税估算 ==========
print("=" * 60)
print("示例8: 热税估算")
print("=" * 60)

heat_samples = [
    "根据实验数据，我们推测可能存在某种关联。",
    "这是终极真理，不容置疑！",
    "在特定条件下，系统表现出非线性特征。",
]

for text in heat_samples:
    heat = client._estimate_heat_tax(text)
    level = "低" if heat < 0.3 else "中" if heat < 0.6 else "高"
    print(f"热税={heat:.2f} ({level}): {text[:30]}...")

print()

print("=" * 60)
print("Demo完成！MSS-Agent SDK v0.1")
print("=" * 60)
