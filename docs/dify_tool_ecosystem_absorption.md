# Dify 工具生态拆解 — MSS 可吸收资源地图

> 分析: Dify `api/core/tools/` 完整模块树 → MSS 吸收策略
> 核心命题: "他们的工具生态也是我们的资源"

## 一、Dify 工具层架构

```
api/core/tools/
├── tool_engine.py          ← 核心引擎 (AgentPromptEntity → ToolInvokeMsg)
├── tool_manager.py         ← 工具注册中心 (hardcoded + plugin + workflow)
├── tool_file_manager.py    ← 文件生命周期 (上传/引用/清理)
├── tool_label_manager.py   ← 分类/标签系统
├── entities/               ← 数据模型 (ToolProviderEntity等)
├── __base/                 ← 抽象基类 (ToolProvider / Tool)
├── builtin_tool/           ← 内置工具 (audio/code/time/webscraper)
│   └── providers/           ← 工具提供者注册
├── custom_tool/            ← 用户自定义工具 (OpenAPI schema)
├── mcp_tool/               ← MCP 协议桥接 (Stdio/SSE)
├── plugin_tool/            ← 插件市场工具
├── workflow_as_tool/       ← Workflow → 可调用Tool
└── utils/                  ← 工具类
```

## 二、Dify 工具分类目录

| 类别 | 数量(估计) | 典型代表 | MSS可吸收性 |
|------|----------|---------|-----------|
| **搜索类** | ~10 | Google/Bing/Wikipedia/SerpAPI | ✅ 已有 web_search |
| **代码类** | ~5 | Python/JS/Code Interpreter | ✅ 已有 exec |
| **文件类** | ~4 | PDF/Excel/Word Parser | ✅ 已有 skill |
| **知识库** | ~3 | RAG/Vector/Knowledge | ✅ 已有 vector_memory |
| **多媒体** | ~3 | Generate Image/DALL·E/StableDiffusion | ❌ GPU依赖 |
| **数据分析** | ~2 | Chart Generator/Data Analysis | ❌ 轻量可实现 |
| **通信** | ~3 | Email/SMS/Slack | ✅ 有 skill |
| **爬虫** | ~2 | Web Scraper/Jina Reader | ✅ 已有 web_fetch |
| **时间/工具** | ~3 | Current Time/Calculator/Weather | ✅ 轻量 |

## 三、MSS 吸收策略: 三层不重写

### Layer 1: 不需要写 — Dify 工具直接调用

Dify 的每个 Tool 暴露为 HTTP API → MSS 通过 HTTP 调用, 零代码复用:

```python
# MSS 不需要实现 Google 搜索, 直接调 Dify 的 Google Tool
result = requests.post(
    "http://localhost:5001/v1/tools/google_search/invoke",
    json={"query": "heat tax definition"},
    headers={"Authorization": f"Bearer {DIFY_API_KEY}"}
)
```

**可吸收工具清单** (Dify 已实现, MSS 直接调):
- Google Search / Bing / Wikipedia / SerpAPI (搜索)
- Code Interpreter / Python Executor (执行)
- Web Scraper / Jina Reader (爬取)
- Email / Slack / SMS / Discord (通信)
- PDF/Excel/Word Parser (文档)
- Stable Diffusion / DALL·E (图像)

### Layer 2: 需要适配 — Dify Tool → MSS Tool 包装器

```python
# mssclaw/core/mss_tool_provider.py
class DifyToolProvider:
    """MSS ↔ Dify Tool Bridge"""
    
    def __init__(self, dify_api_url="http://localhost:5001"):
        self.api_url = dify_api_url
        self.heat_tax = ToolHeatTaxTracker()
    
    def invoke(self, tool_name: str, params: dict) -> dict:
        """Invoke Dify tool, tracked by MSS heat tax."""
        start = time.time()
        result = self._call_dify(tool_name, params)
        elapsed = time.time() - start
        
        # MSS heat tax overlay
        self.heat_tax.record(tool_name, elapsed, result)
        return result
```

### Layer 3: 需要替换 — MSS 原生实现

以下领域 Dify 的工具不够好, MSS 应原生替代:
- **热税感知的工具调用调度** (按热税预算分配调用)
- **Δ可观测的工具链** (每个工具调用的意义贡献)
- **信任预算路由** (不同Agent对工具的访问权限)

## 四、MSS 独有的工具维度 (Dify 完全没有)

| MSS 维度 | Dify 对应 | 差距 |
|---------|----------|------|
| **热税工具审计** | ❌ | 🔴 Dify 不关心每次调用的热税 |
| **Δ 工具评分** | ❌ | 🔴 Dify 不评估工具调用的意义贡献 |
| **信任预算门禁** | ❌ | 🔴 Dify 所有Agent对所有工具平等 |
| **A6 维度工具组合** | ❌ | 🔴 Dify 不检测工具组合的矛盾 |
| **蜕壳式工具淘汰** | ❌ | 🔴 Dify 只添加不淘汰 |

## 五、立刻可做的三件事

### [P0] mss_tool_bridge.py — Dify 工具直调桥
```python
# 一行代码: 所有 Dify 工具变为 MSS 可调用资源
provider = DifyToolProvider("http://dify:5001")
result = provider.search("Google", {"query": "heat tax"})
# → result 附带热税/Δ评分
```

### [P1] 工具目录自动扫描
```python
# 扫 Dify 暴露的 tools.json → 生成 MSS 的工具注册表
mssclaw tool scan --source dify
```

### [P2] 热税感知调度器
```python
# 按热税预算调度工具调用
scheduler = HeatTaxToolScheduler(budget=0.3)
scheduler.run([
    ToolCall("GoogleSearch", query="x", priority=0.8),
    ToolCall("CodeExec", code="...", priority=0.2),
])
# → 优先执行热税低的调用组合
```

## 六、吸收优先级矩阵

```
                    Dify实现质量
                    高          低
                ┌─────────┬─────────┐
MSS  高  (需要) │ 搜索工具 │ 多媒体   │ ← 直接调Dify
差异          │  通信工具 │ 数据分析 │
化           ├─────────┼─────────┤
价值 低  (不需要)│ 代码执行 │ 时间/计算│ ← 可选调用
                └─────────┘─────────┘
```

**结论**: Dify 的工具生态就是 MSS 的免费资源库 — 我们不重写, 包装一层热税/Δ/信任预算的门面。
