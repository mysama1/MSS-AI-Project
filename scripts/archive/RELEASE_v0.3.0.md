# mss-agent v0.3.0 Release

> 混血全栈: Δ快检 + 领域检测 + fewshot注入 + callback + 热税会计 + AgentConfig

## 🆕 新增

### 混血调教系统 v2.0
- **Δ快检引擎** `delta_quick_audit.py` — 5秒5问偏差感知,每轮LLM回应后自动审计
- **领域检测器** `domain_detector.py` — 前3轮自动判定 daily/tech/philosophy/combat
- **Few-Shot注入器** `fewshot_builder.py` — 6组校准对比数据 → 完整/精简/反例版prompt
- **Callback集成** `delta_callback.py` — LangChain handler + OpenAI SDK wrapper
- **端到端流水线** `hybrid_pipeline_demo.py` — 4场景全部通过

### Agent v1.0 基础
- **AgentConfig** `agent_config.py` — 4预设 + YAML/JSON配置 + 全参数化阈值
- **热税会计** `heat_tax_accountant.py` — L0/L1/L2三层实时追踪 + 预算告警 + auto_estimate

### 调教文件 (tuning/)
- `mss_llm_hybrid_v1.md` — 三层架构(T1/T2/T3)
- `mss_llm_hybrid_v2.md` — 自校准架构(Δ快检+T2.5自愈+领域配置)
- `calibration_dataset_10.md` — 10组对比示例

### 安装
```bash
pip install mss-agent==0.3.0
```

### 快速开始
```python
from mss_agent import DeltaQuickAudit
from mss_agent import AgentConfig

# 1. Δ快检
auditor = DeltaQuickAudit()
result = auditor.audit(response_text="...", user_query="...")
print(result.light, result.calibration)

# 2. 预设配置
config = AgentConfig.preset("daily")
print(config.heat_tax.max_tokens_per_turn)  # 300
```
