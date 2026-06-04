# MSS-Agent SDK v0.1

> 阶段一核心交付物：外挂式逻辑审计SDK  
> 让任何Python应用都能接入MSS意义锚定与逻辑合规检查

## 核心特性

- **零侵入**：通过装饰器/上下文管理器接入，不改现有代码逻辑
- **双模运行**：本地符号引擎（确定性）+ 远程MSS-AI（深度分析）
- **诚实基线**：所有输出标注 `[Confidence]` / `[Layer]` / `[Boundary Note]`
- **三层锚定**：客观意义 / 实在意义 / 主观意义

## 快速开始

```python
from mss_agent_sdk import MSSClient, mss_audit, mss_anchor
from mss_agent_sdk.mss_types import AnchorLevel

# 方式1：装饰器（零侵入）
@mss_audit(auto_print=True)
def generate_report():
    return "暗物质是由WIMP粒子组成的"

# 方式2：直接调用
client = MSSClient()
result = client.audit("MSS理论是终极真理")
print(result.to_markdown())

# 方式3：意义锚定
@mss_anchor(level=AnchorLevel.OBJECTIVE)
def make_claim():
    return "信息是宇宙的本体"
```

## 安装

```bash
pip install mss-agent-sdk
```

## CLI工具

```bash
# 审计文本
mss-audit "这是一个需要审计的文本"

# 审计文件
mss-audit -f report.txt

# 意义锚定
mss-audit --anchor objective "信息是宇宙的本体"

# JSON输出
mss-audit --json "终极真理"
```

## 配置

环境变量：
- `MSS_API_ENDPOINT`: MSS-AI服务端点（默认 http://localhost:11434）
- `MSS_MODEL_NAME`: 模型名称（默认 mss-ai-v1）
- `MSS_LOCAL_ONLY`: 仅本地模式（默认 false）
- `MSS_KB_PATH`: 知识库路径（默认 knowledge_base）

## 架构

```
mss_agent_sdk/
├── __init__.py          # 包入口
├── client.py            # 核心客户端（双模运行）
├── decorators.py        # 装饰器（@mss_audit, @mss_anchor）
├── mss_types.py         # 核心类型（AuditResult, AnchorResult等）
├── config.py            # 配置管理
├── cli.py               # 命令行工具
├── setup.py             # 安装脚本
└── test_sdk_standalone.py  # 独立测试套件
```

## 审计输出示例

```markdown
## MSS逻辑审计报告

**状态**: ❌ 未通过
**逻辑刚性 M_L**: 0.3500
**热税 γ**: 0.4500
**置信度**: [Confidence: SPECULATIVE]
**层级**: L4

### 检测到的矛盾
- ⚠️ 检测到禁用词: '终极'

### 优化建议
- 💡 建议替换为相对化表述
```

## 公理锚定

SDK所有审计逻辑锚定于MSS六条硬核公理（A1-A6）：
- A1 信息本体论
- A2 信息切片与显化公理
- A3 终极热税公理
- A4 规范场与引力公理
- A5 映射公理
- A6 生命与意识公理

## 版本历史

- v0.1.0 (2026-05-22): Alpha发布
  - 核心客户端（本地+远程双模）
  - 装饰器支持（@mss_audit, @mss_anchor）
  - CLI工具（mss-audit）
  - 三层意义锚定
  - 13项独立测试全部通过

## 诚实声明

当前SDK处于Alpha阶段，逻辑刚性估算为启发式算法（非形式化证明）。
框架完整性约25-30%，验证层0%。
所有输出自动标注置信度和边界，禁止虚假完备性声明。
