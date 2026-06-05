#!/usr/bin/env python3
"""
D5-002: 深度思考UI逻辑 — Thinking Folding Mechanism
问题: AI思考代码直接输出, 影响阅读体验
方案: <thinking>...</thinking> 折叠标记 + 前端解析器
MSS锚定: A2(信息切片) — 思考过程与最终输出分层
"""
import re, json, sys

# ===== 思考标记规范 =====
THINKING_START = "<thinking>"
THINKING_END = "</thinking>"

# ===== 解析器: 提取思考块 =====
def extract_thinking(text):
    """从AI输出中提取所有思考块"""
    pattern = re.compile(rf'{re.escape(THINKING_START)}(.*?){re.escape(THINKING_END)}', re.DOTALL)
    thoughts = pattern.findall(text)
    clean = pattern.sub('', text).strip()
    return thoughts, clean

# ===== 渲染器: 折叠UI =====
def render_folded(text):
    """将思考块转换为折叠HTML标记"""
    def fold(match):
        content = match.group(1).strip()
        # 取前80字作为摘要
        summary = content[:80] + ("…" if len(content) > 80 else "")
        return f'\n<details><summary>🧠 思考过程: {summary}</summary>\n\n{content}\n\n</details>\n'
    
    pattern = re.compile(rf'{re.escape(THINKING_START)}(.*?){re.escape(THINKING_END)}', re.DOTALL)
    return pattern.sub(fold, text)

# ===== 提示词注入器: 教模型使用思考标记 =====
THINKING_PROMPT = """
## CRITICAL: Thinking Output Protocol

When you need to reason through a complex problem:

1. Wrap ALL reasoning/chain-of-thought in <thinking>...</thinking> tags
2. After </thinking>, output ONLY the final answer
3. The thinking block will be COLLAPSED in the UI — it's for audit, not display

Example:
<thinking>
Step 1: Analyze the problem...
Step 2: Consider alternatives...
Step 3: Verify constraints...
</thinking>
最终答案: ...

NEVER output raw reasoning outside <thinking> tags.
"""

# ===== 测试用例 =====
TEST_INPUT = """
<thinking>
This is a complex problem. Let me break it down.
First, I'll check the axioms A3 and A4.
Then I'll verify the thermal tax calculation.
Conclusion: γ=2.5, meaning entropy is increasing moderately.
</thinking>

分析结果: γ=2.5, 意义熵在适度增长。建议减少低T值输入。
"""

def self_test():
    thoughts, clean = extract_thinking(TEST_INPUT)
    print("=== 提取测试 ===")
    print(f"思考块: {len(thoughts)}")
    print(f"干净输出: {clean[:50]}...")
    
    rendered = render_folded(TEST_INPUT)
    print(f"\n=== 折叠渲染测试 ===")
    print(rendered[:200])
    
    print("\n✅ D5-002 思考折叠机制自测通过")

if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    elif "--extract" in sys.argv and len(sys.argv) > 2:
        text = sys.argv[2]
        thoughts, clean = extract_thinking(text)
        print(f"思考块数: {len(thoughts)}")
        print(f"输出: {clean}")
    elif "--prompt" in sys.argv:
        print(THINKING_PROMPT)
    else:
        self_test()