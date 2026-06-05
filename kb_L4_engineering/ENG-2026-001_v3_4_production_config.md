# ENG-2026-001: mss-ai-v3_4-production 模型配置

## 基本信息

```
名称:      mss-ai-v3_4-production:latest
基座:      qwen2 7.6B
量化:      Q4_K_M
上下文:    4096 tokens
温度:      0.05
top_p:     0.4
top_k:     20
num_predict: 2048
```

## 基准测试

| 指标 | 数值 |
|:---|:---|
| 37 项自测 | 37/37 (100%) |
| SQI | 100.0 |
| Dao 评分 | 100.0 |
| 平均响应 | 2.7s |
| CRTR | N/A (没有意义黑洞) |

## 对比

| 模型 | 得分 | 延迟 |
|:---|:---|:---|
| v3_4-production | 100% | 2.7s |
| v3_7 | 67% | 3.1s |
| v3_4 | 100% | 2.7s |
| v3_3 | 97% | 2.9s |

## System Prompt (核心)

```
You are MSS-AI (production), operating within the Meaning Supremacy System framework.

CORE PRINCIPLES:
- All claims MUST be anchored to observable evidence
- NEVER fabricate data, citations, or statistics
- When uncertain, state uncertainty with confidence level
- Distinguish between PROVEN, CONJECTURE, and SPECULATION
```

## 已知限制

1. 上下文仅 4096 → 不适合长文档
2. 温度 0.05 → 创造性低, 不适合发散任务
3. 所有 MSS 理论声明均需独立验证
4. 不联网, 知识截止到训练数据

## 升级路径

- 如需更长上下文 → `mss-ai-v3_6-32k` (32768)
- 如需更高创造性 → 调整 temperature=0.3
- 如需联网 → 走 QClaw 主模型 (pool-hy3-preview)
