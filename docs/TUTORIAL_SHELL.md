# Tutorial: MSS Shell — 双模型壳核模式

MSS 独有特性。壳感知世界，核守护意义。

## 架构

```
     User Input
          │
     ┌────┴────┐
     │  Router │  ← Auto-detect: 闲聊? 专业? 安全?
     └────┬────┘
          │
    ┌─────┴──────┐
    │            │
┌───┴───┐   ┌───┴───┐
│ Shell │   │ Shell  │
│ ONLY  │   │ + Core │
│       │   │        │
│ qwen  │   │ qwen   │  ← Shell: fast LLM (perception)
│ 5ms   │   │ 5ms    │
└───────┘   │   +    │
            │ mss-ai │  ← Core: local model (logic)
            │ 24-47s │
            └────────┘
```

## 四种模式

```bash
/shell off     # 默认，单一模型
/shell auto    # 自动路由 ← 推荐
/shell dual    # 强制双模型
/shell check   # 壳回答 + 核审查
```

## 自动路由规则

| 输入 | 路由 | 原因 |
|---|---|---|
| "你好" | `shell_only` | 低风险闲聊 |
| "写五言绝句" | `full_dual` | 创作任务 |
| "解释热税公式" | `core_check` | MSS 专业知识 |
| "审计这段代码" | `full_dual` | 安全敏感 |

## 后端自动选择

```
有 API 密钥时:
  壳 → DeepSeek API (快, <2s)
  核 → 本地 mss-ai-v3.4.3 (专)

无 API 密钥时:
  壳 → Ollama qwen2.5:7b
  核 → Ollama mss-ai-v3.4.3
```

## 实战

```bash
mssclaw chat
/shell auto

You: 写一首关于AI的诗
# → full_dual: qwen生成 + mss-ai审查

You: 看看我的代码有没有安全问题
# → full_dual: qwen分析 + mss-ai核查

You: 你好
# → shell_only: 快速响应
```

## 核审查内容

```
FULL_DUAL 输出:
  [壳回答]
  ═══════
  [MSS-AI 核审查]
  ✅ 公理一致性: A1-PASS A3-PASS A6-PASS
  ✅ 热税预算: 0.03 (安全)
  ✅ Δ开放度: 0.87 (健康)
  ✅ 无意义偷换/虚假数据/伪约束
```

---

**提示**: 双模型模式下延迟 24-47s。建议默认 `auto`，只在需要安全审查时切换到 `dual`。
