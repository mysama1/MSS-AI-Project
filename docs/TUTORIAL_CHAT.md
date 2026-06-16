# Tutorial: Agent Chat — 终端 AI 聊天

本地终端版 ChatGPT，支持流式输出、工具调用、对话持久化。

## 第一步：启动聊天

```bash
mssclaw chat
# 默认使用 qwen2.5:7b

mssclaw chat --model phi3:mini
# 使用其他模型
```

```
┌─────────────────────────────────────┐
│ mssclaw v0.3.9                      │
│ Model: qwen2.5:7b | Vault: ready    │
│ /help for commands                   │
└─────────────────────────────────────┘
```

## 第二步：对话

```bash
You: 解释一下什么是热税
Agent: 热税(MSS-Axiom 3)分为三层...  [流式输出]
```

## 第三步：Slash 命令

```bash
/model qwen2.5:7b     # 切换模型
/vault                # 连接保险箱
/tools                # 开关工具调用
/shell dual           # 启动双模型模式
/absorb Review code   # 吸收外部技能
/clear                # 清空历史
/save                 # 保存对话
/load                 # 加载上次对话
/quit                 # 退出
```

## 第四步：工具调用

```bash
You: 现在几点？
Agent: [调用 datetime] 2026-06-16 21:00  ✅

You: 计算 2^10
Agent: [调用 calculator] 1024  ✅

You: kb_search 热税公式
Agent: [调用 kb_search] H123: 热税三层公式... ✅
```

## 第五步：流式输出特性

MSS 独有语义流式——根据内容自动切换风格：

- **代码**：高亮语法 + 自动格式化
- **数学**：LaTeX 渲染
- **长文**：自动折叠 (DeepFold)
- **对话**：自然呼吸节奏

## 对话持久化

```bash
# 对话保存在 ~/.mssclaw/chat_history/
# 自动记录: 模型、延迟、L2层级
# /save /load 手动管理
```

---

**提示**: 启动时按 Enter 跳过闲聊，直接 `/model` 切换终端。
