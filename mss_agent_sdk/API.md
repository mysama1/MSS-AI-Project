# MSS-Agent SDK v0.1 API文档

## 概述

MSS-Agent SDK 是 MSS-AI 框架的官方 Python SDK，提供文本逻辑审计和意义锚定能力。

**双模运行架构：**
- **本地模式**：符号引擎 + 知识库查询（确定性，零延迟）
- **远程模式**：MSS-AI 深度分析（高智能，有延迟）

## 安装

```bash
pip install mss-agent-sdk
```

## 快速开始

```python
from mss_agent_sdk import MSSClient

client = MSSClient()

# 审计文本
result = client.audit("量子纠缠是非定域的...")
print(f"M_L={result.logic_rigidity:.2f}, γ={result.heat_tax:.2f}")

# 意义锚定
anchor = client.anchor("双缝实验结果", level=AnchorLevel.ACTUAL)
print(anchor.text)  # [可验证] 双缝实验结果 [待实证]
```

## 核心类

### MSSClient

主客户端类，提供审计和锚定功能。

#### 构造函数

```python
MSSClient(config: Optional[SDKConfig] = None)
```

- `config`: SDK配置对象，默认从环境变量加载

#### 方法

##### audit(text, context=None)

对文本进行逻辑审计。

**参数：**
- `text` (str): 待审计文本
- `context` (Optional[str]): 可选上下文

**返回：** `AuditResult`

**示例：**
```python
result = client.audit("因为A所以B")
print(result.passed)           # True/False
print(result.logic_rigidity)   # 0.0-1.0
print(result.heat_tax)         # ≥0
print(result.to_markdown())    # Markdown报告
```

##### anchor(text, level=AnchorLevel.ACTUAL)

对文本进行意义锚定。

**参数：**
- `text` (str): 待锚定文本
- `level` (AnchorLevel): 锚定层级

**返回：** `AnchorResult`

**示例：**
```python
result = client.anchor("量子力学", level=AnchorLevel.OBJECTIVE)
print(result.text)  # [A1-A6公理框架内] 量子力学
```

## 装饰器

### @mss_audit()

自动审计函数返回值。

```python
from mss_agent_sdk import mss_audit

@mss_audit()
def generate_report(topic):
    return f"关于{topic}的报告..."

report = generate_report("AI安全")
# 返回值自动附加审计结果
```

**参数：**
- `context` (Optional[str]): 审计上下文
- `auto_print` (bool): 是否自动打印审计报告
- `raise_on_fail` (bool): 审计未通过时是否抛出异常

### @mss_anchor()

自动锚定函数返回值。

```python
from mss_agent_sdk import mss_anchor

@mss_anchor(level=AnchorLevel.OBJECTIVE)
def state_axiom():
    return "信息是宇宙的本体"

axiom = state_axiom()
# 返回值自动附加锚定标记
```

**参数：**
- `level` (AnchorLevel): 锚定层级
- `auto_append` (bool): 是否自动附加锚定标记到文本

## 类型定义

### AnchorLevel

意义锚定层级枚举。

```python
class AnchorLevel(Enum):
    OBJECTIVE = auto()   # 客观潜在意义 L-1
    ACTUAL = auto()      # 实在显化意义 L0
    SUBJECTIVE = auto()  # 主观体验意义 L1
```

### Confidence

置信度等级枚举。

```python
class Confidence(Enum):
    CERTAIN = "[Confidence: CERTAIN]"      # 公理/定义层
    HIGH = "[Confidence: HIGH]"            # 定理/引理层
    MODERATE = "[Confidence: MODERATE]"    # 试探法层
    SPECULATIVE = "[Confidence: SPECULATIVE]"  # 推测/边界外
```

### AuditResult

审计结果数据类。

**字段：**
- `passed` (bool): 是否通过审计
- `logic_rigidity` (float): 逻辑刚性 M_L ∈ [0,1]
- `heat_tax` (float): 热税 γ ≥ 0
- `confidence` (Confidence): 置信度等级
- `layer` (str): 层级 L1/L2/L3/L4
- `boundary_notes` (List[BoundaryNote]): 边界标注
- `contradictions` (List[str]): 检测到的矛盾
- `suggestions` (List[str]): 优化建议

**方法：**
- `to_markdown() -> str`: 生成Markdown格式报告

### AnchorResult

锚定结果数据类。

**字段：**
- `level` (AnchorLevel): 锚定层级
- `anchored` (bool): 是否成功锚定
- `text` (str): 锚定后的文本
- `heat_tax_before` (float): 锚定前热税
- `heat_tax_after` (float): 锚定后热税
- `savings` (float): 热税节省比例

## 配置

### SDKConfig

配置类，支持从环境变量加载。

**环境变量：**
- `MSS_API_ENDPOINT`: API端点（默认 http://localhost:11434）
- `MSS_MODEL_NAME`: 模型名称（默认 qwen2.5:7b）
- `MSS_KB_PATH`: 知识库路径
- `MSS_LOGIC_RIGIDITY_THRESHOLD`: 逻辑刚性阈值（默认 0.5）
- `MSS_HEAT_TAX_THRESHOLD`: 热税阈值（默认 0.3）

**示例：**
```python
from mss_agent_sdk.config import SDKConfig

config = SDKConfig(
    api_endpoint="http://localhost:11434",
    model_name="qwen2.5:7b",
    knowledge_base_path="./knowledge_base",
    logic_rigidity_threshold=0.5,
    heat_tax_threshold=0.3,
)
config.validate()
```

## CLI工具

安装后提供 `mss-audit` 命令行工具。

```bash
# 审计文件
mss-audit input.txt

# 审计并生成报告
mss-audit input.txt --output report.md

# 指定锚定层级
mss-audit input.txt --anchor objective
```

## 示例

详见 `demo.py` 完整示例代码。

## 版本信息

- **版本**: v0.1
- **发布日期**: 2026-05-21
- **MSS框架版本**: v15.1
- **许可证**: MIT
