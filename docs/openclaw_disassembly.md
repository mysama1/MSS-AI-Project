# OpenClaw 完整拆解 — MSS 意义工程学视角

> **版本**: 2026.4.21-5 (v0.2.27.560) | **语言**: TypeScript → 编译为 ESM JS  
> **模块数**: ~1000+ 个编译后 JS 文件 | **包名**: `openclaw` | **许可证**: 未公开源码  
> **入口**: `dist/index.js` → `run-main-BGUUveG7.js`

---

## 一、整体架构 — 十二大系统

```
                    ┌─────────────────────────────────┐
                    │         Plugin SDK (出口)         │
                    │     150+ export paths             │
                    │      .plugin-sdk/ 体系            │
                    └──────────────┬──────────────────┘
                                   │
    ┌──────────┬──────────┬───────┴───────┬──────────┬──────────┐
    │ Channels │ Gateway  │  Session     │ Agents   │ Skills   │
    │ 18+ 方式  │ HTTP/WS  │  状态管理     │ 子Agent   │ 58个内置   │
    └──────────┴──────────┴───────────────┴──────────┴──────────┘
    ┌──────────┬──────────┬───────────────┬──────────┬──────────┐
    │ Approval │ Sandbox  │  Memory (AI)  │ Provider │ MCP/ACP  │
    │ 执行审批   │ 隔离执行   │  向量记忆      │ 30+模型   │ 协议桥接   │
    └──────────┴──────────┴───────────────┴──────────┴──────────┘
    ┌──────────┬──────────┬───────────────┬──────────┬──────────┐
    │ Lifecycle│ CLI      │  Security     │ Browser  │ Canvas   │
    │ 心跳/启动  │ 100+命令  │  沙盒/安全策略  │ CDP自动化  │ 渲染/UI   │
    └──────────┴──────────┴───────────────┴──────────┴──────────┘
```

---

## 二、逐系统拆解

### 1. Gateway 网关系统（核心中枢）

```
gateway*.js (11个模块)
├── gateway-rpc.runtime.js    ← 内部 RPC 协议
├── gateway-discovery-targets  ← 自动发现 (Bonjour/mDNS)
├── gateway-presence-D2RJjrPM  ← 在线状态
├── gateway-control-ui-origins  ← Web UI CORS
├── gateway-install-token       ← 安装配对 Token
├── gateway-method-policy       ← 方法级权限控制
├── gateway-request-scope       ← 请求作用域
├── gateway-secret-options      ← 密钥选项
├── gateway-status              ← 健康检查
├── gateway-cli                 ← 命令行控制
└── gateway-lock                ← 并发锁
```

**MSS 视角**: Gateway 是 OpenClaw 的"边界"——所有命令、WebSocket 连接、HTTP 请求都通过它。它相当于 LLLM 的 ProxyManager，但更底层（不只是 tool proxy，而是整个系统的通信网关）。

**吸收点**: 
- 方法级权限策略 (`gateway-method-policy`) → 对应 H634 信任门禁的有趣类比 — 不是"信任/不信任"二元，而是按方法/作用域分级
- 自动发现 (`gateway-discovery-targets`) → MSS 的 Agent 间发现也应该支持 mDNS

---

### 2. 会话系统（状态管理核心）

```
session*.js (30+个模块)
├── session-id, session-key         ← 唯一标识
├── session-store (FS + DB)         ← 持久化存储
├── session-write-lock              ← 并发写保护
├── session-fork                    ← 克隆/分支会话
├── session-binding                 ← 绑定到 channel/thread
├── session-context                 ← 上下文注入 (USER.md, AGENTS.md 等)
├── session-identity                ← 身份识别
├── session-cost-usage              ← Token/费用追踪
├── session-hooks                   ← 生命周期钩子
├── session-transcript              ← 对话记录
├── session-subagent-reactivation   ← 子Agent恢复
├── session-updates                 ← 实时推送
└── session-system-events           ← 系统事件
```

**MSS 视角**: 这是最值得吸收的系统。LLLM 的 Dialog 是 Agent 的心智状态，OpenClaw 的 Session 是更复杂的"多维度状态容器"——包含身份、成本、历史、绑定关系、系统事件。MSS 的 Tactic 还只是在单次调用中追踪状态，但没有这个级别的会话持久化。

**吸收点**:
- `session-write-lock` → MSS 的并发 Agent 写冲突检测
- `session-cost-usage` → 热税预算的"会计层"——不光算花了多少，还要算"这钱花得值不值" (Δ)
- `session-hooks` → MSS 可以用这个模式注入"每次 run 前后检查 Δ/热税/退化"

---

### 3. 审批系统（执行门禁）

```
approval*.js (15+个模块)
├── approval-auth-runtime           ← 认证运行时
├── approval-gateway-resolver       ← Gateway 级别审批
├── approval-handler-runtime        ← 自定义审批处理
├── approval-native-helpers         ← 本机审批 UI
├── approval-request-filters        ← 请求过滤（哪些命令需要审批）
├── approval-renderers              ← 审批 UI 渲染
├── exec-approval-command-display   ← 命令显示格式化
├── exec-approval-forwarder         ← 审批转发
├── exec-approvals-allowlist        ← 白名单
└── exec-approval-session-target    ← 按 Session 维度的审批
```

**MSS 视角**: 这是 OpenClaw 的 **"DeferGuard 的工业化版"**。我们的 H648 只能做 `can_execute()` 检查，OpenClaw 的审批系统是完整的六步链：

```
发起命令 → 过滤(哪些需要审批) → 认证(谁发的) → 渲染(展示给人类) → 人类决策 → 转发执行
```

**吸收点**: 把 `DeferGuard` 从单点检查升级为 `MSSApprovalChain` — 支持多种审批条件组合 + 人类介入点 + 自动防线。

---

### 4. 频道插件系统（18+ 输入/输出通道）

```
Channel 插件 (18+ 个):
├── Discord (discord-*.js)
├── Telegram (telegram-*.js, 含 command-config, command-ui, runtime-surface)
├── Signal (内置)
├── WhatsApp (zod-schema.providers-whatsapp)
├── iMessage (imessage-policy, imessage-runtime)
├── Slack
├── MS Teams (msteams-D5GAxFtz.js)
├── Google Chat (googlechat-*.js)
├── WeChat/飞书 (feishu-*.js)
├── LINE (line-*.js)
├── Matrix (matrix-*.js)
├── Nextcloud Talk
├── IRC
├── Twitch
├── Zalo (zalo-*.js)
├── BlueBubbles (iMessage bridge)
├── WebChat (control-ui)
└── Webhook (webhook-*.js)
```

每个 Channel 统一实现:
```
channel-core          ← 公共接口
channel-config        ← 配置 schema
channel-inbound       ← 消息接收
channel-reply-pipeline ← 回复管道(格式化/截断/附件)
channel-lifecycle     ← 启动/停止/重连
channel-policy        ← 行为策略
channel-streaming     ← 流式输出
```

**MSS 视角**: OpenClaw 的频道系统是最成熟的"跨平台 Agent 通信层"做法。MSS 不需要 18 个频道，但 **"统一频道抽象 + 策略分离"** 的模式值得吸收：每个 Agent 可以有不同的输入/输出策略，但共享同一个通信管道。

**吸收点**: `channel-reply-pipeline` 模式用于 MSS 的多 Agent 响应聚合 — 不同 Agent 的输出经过同一条管道格式化后才发给用户。

---

### 5. Memory 系统（AI 记忆）

```
memory*.js (20+个模块)
├── memory-core-host-runtime-core   ← 核心引擎
├── memory-core-host-engine-embeddings ← 嵌入向量 (LanceDB)
├── memory-core-host-engine-foundation ← 基础存储
├── memory-core-host-engine-qmd        ← QMD 引擎 (?)
├── memory-core-host-engine-storage    ← 持久化
├── memory-host-search                 ← 语义搜索
├── memory-lancedb                     ← LanceDB 向量库
├── memory-state                       ← 记忆状态
├── memory-search                      ← 搜索接口
└── memory-embedding-provider          ← 嵌入模型
```

**MSS 视角**: OpenClaw 的记忆系统是**两层的**: `memory/YYYY-MM-DD.md` (文件层) + LanceDB 向量搜索 (语义层)。MSS 目前的 `conv_search.py` 是文件级文本搜索，没有向量嵌入。

**吸收点**: LanceDB 的嵌入层 → 给 `conv_search.py` 加语义相似度搜索，让"囚徒困境"能搜到"Nash 均衡"而不仅仅是文本匹配。

---

### 6. Agent 系统（子 Agent 管理）

```
agent*.js + subagent*.js (20+个模块)
├── agents (核心)
├── agent-runner              ← Agent 执行器
├── agent-delivery            ← Agent 间消息传递
├── agent-scope               ← Agent 作用域
├── agent-filter              ← Agent 过滤/匹配
├── subagent-spawn            ← 子Agent 启动
├── subagent-announce         ← 子Agent 公告
├── subagent-control          ← 控制(steer/kill)
├── subagent-registry         ← 注册中心
├── subagent-depth            ← 深度限制
├── subagent-session-metrics  ← 指标
├── subagent-system-prompt    ← 注入的系统提示词
└── dispatch-acp              ← ACP 协议分发
```

**MSS 视角**: OpenClaw 的子Agent 系统比 LLLM 的 Tactic 递归更完整 — 它有**注册中心、深度限制、会话级指标、公告机制**。LLLM 的 Agent 调用 Agent 只是一个 endpoint，OpenClaw 的 Agent 间交互是完整的"发布-订阅-发现"体系。

**吸收点**: `agent-registry` + `agent-announce` → MSS 的多 Agent 系统需要一个"谁在线、能干什么"的公告板，不只是一个路由表。

---

### 7. Provider 系统（30+ 模型供应商）

```
provider*.js (40+个模块)
├── provider-registry         ← 模型注册中心
├── provider-catalog          ← 模型目录
├── provider-auth (10+ 模块)  ← 认证 (API Key / OAuth / SSO / Copilot)
├── provider-http             ← HTTP 客户端
├── provider-model-*          ← 模型规格
├── provider-stream           ← 流式处理
├── provider-tools            ← 工具/函数调用
├── provider-usage            ← Token 计数+费用
├── provider-onboard          ← 新供应商接入向导
├── provider-web-search       ← Web 搜索供应商
└── provider-web-fetch        ← Web 抓取供应商
```

关键供应商:
```
@anthropic-ai, @mistralai, @google, @aws
openai (OpenAI + Codex)
chutes-oauth (Chutes.ai)
opencode
lmstudio (本地)
ollama (通过 openai-compatible)
```

**MSS 视角**: Provider 系统的认证层特别成熟 — 它不只是"填个 API Key"，而是完整的 OAuth 流程 + Copilot 令牌 + SSO + 设备认证 + API Key 轮转。MSS 不需要这么复杂，但 **"供应商认证与供应商调用分离"** 的设计模式值得吸收。

**吸收点**: MSS 的 Ollama 本地连接目前是硬编码。如果将来接入外部 API，需要一个 `ProviderRegistry` 抽象层，而不是在代码里硬嵌 URL。

---

### 8. Sandbox 沙盒系统（安全执行）

```
sandbox*.js (8个模块)
├── sandbox-cli              ← 沙盒命令行
├── sandbox-NG1PMJPe         ← 核心沙盒
├── sandbox-tool-policy      ← 工具策略
├── sandbox-paths            ← 路径限制
├── sandbox-media-paths      ← 媒体文件路径
├── sandbox-info             ← 沙盒元数据
├── sandbox-ZWB5KeCT         ← 沙盒实现 2
└── exec-approvals-*         ← 执行审批 (绑定)
```

加上:
```
exec-safe-bins              ← 安全二进制白名单
exec-safe-bin-trust         ← 二进制信任机制
exec-safety                 ← 安全检查
exec-policy-cli             ← 执行策略
exec-defaults               ← 默认安全级别
```

**MSS 视角**: 这就是我们刚做的 `mss_sandbox.py` 的"参考实现"。OpenClaw 的沙盒是**二进制级别的** (白名单可执行文件)，而不仅是 Python `import` 级别的 (白名单 Python 模块)。它的粒度更粗但防御面更广。

**吸收点**: `exec-safe-bin-trust` 的"信任度"机制 → `mss_sandbox.py` 可以给每个注入的工具加 trust_score，而不仅仅是 delta_cost。

---

### 9. LCM / Compaction 系统（上下文压缩）

```
compact*.js + pi-embedded*.js + transcript*.js (15+个模块)
├── compact-BHw7RKTm           ← 核心压缩
├── compaction-runtime-context  ← 压缩上下文
├── pi-embedded-runner          ← 嵌入式 PI 运行器
├── pi-embedded-subscribe       ← 压缩事件订阅
├── pi-embedded-block-chunker   ← 分块器
├── transcript-runtime          ← 对话转录
├── transcript-events           ← 转录事件
├── transcript-rewrite          ← 转录重写
├── query-expansion             ← 查询扩展
└── lossless-claw (外部插件)
```

**MSS 视角**: 这是 OpenClaw 的"无限对话窗口"方案。MSS 的 `conv_search.py` 是**事后搜索**，OpenClaw 的 LCM 是**实时压缩 + 事后展开**。二者互补。

**吸收点**: LCM 的两层结构 (压缩摘要 + 索引 DAG) → `conv_search.py` 可以加"对话压缩层"，不只是索引原始文本。

---

### 10. CLI 命令系统（100+ 命令）

```
commands*.js + action-*.js + register-*.js (100+个模块)
```

CLI 入口: `cli-runner-C-WjV_kN.js`
命令注册: `register.subclis-ASJCj88X.js`
分组:
```
/status        → gateway/session/model/channel/node 状态
/channels      → 频道管理
/sessions      → 会话管理
/models        → 模型切换/配置
/plugins       → 插件安装/启用
/skills        → 技能安装/扫描
/approvals     → 执行审批
/config        → 配置
/webhooks      → Webhook 管理
/doctor        → 系统诊断
/browser       → 浏览器控制
/cron          → 定时任务
/acp           → ACP 协议
/devices       → 设备配对
/sandbox       → 沙盒
/docs          → 文档
/nodes         → 节点管理
/ssh           → SSH 隧道
/voice         → 语音
/help          → 帮助
```

**MSS 视角**: MSS 的 CLI 目前只有 35 个命令。OpenClaw 的 CLI 架构 (分组注册 + 子命令树) 是成熟的模式。OpenClaw 是开箱即用，MSS 目前只有 core 命令。

**吸收点**: `register-command-groups` 模式 — MSS 的 CLI 应该也按"组"注册命令，而不是平铺在一个 `argparse` 文件里。

---

### 11. Security 安全系统

```
security-*.js + dangerous-*.js + ssrf-*.js + fences-*.js (15+个模块)
├── security-runtime         ← 运行时安全
├── security-cli             ← 安全命令
├── dangerous-tools          ← 危险工具标记
├── dangerous-name-runtime   ← 危险名称检测
├── dangerous-config-flags   ← 危险配置标志
├── ssrf-policy              ← SSRF 防护
├── ssrf-runtime             ← SSRF 运行时
├── fences                   ← 安全围栏
├── tool-policy (6+ 模块)     ← 工具调用策略
├── audit-tool-policy        ← 审计工具策略
├── fetch-guard              ← HTTP 抓取守卫
└── web-guarded-fetch        ← Web 抓取安全
```

**MSS 视角**: OpenClaw 的安全是**正向白名单 + 多道防线**，不是单层过滤。从"危险名称"到"SSRF"到"工具策略"到"审计"，每一层都独立起作用。

**吸收点**: SSRF 防护 (`ssrf-policy`) → MSS 的 `mss_sandbox.py` 目前只限制了 `import`，但没有限制工具调用可能造成的网络副作用。应该加一个 `ssrf_check()`。

---

### 12. Lifecycle / Cron / Heartbeat 系统

```
heartbeat*.js + lifecycle*.js + cron*.js (15+个模块)
├── heartbeat-runner         ← 心跳执行器
├── heartbeat-BlJ5f77S       ← 心跳逻辑
├── heartbeat-reply-payload  ← 心跳响应
├── heartbeat-summary        ← 心跳摘要
├── heartbeat-wake           ← 唤醒检测
├── lifecycle-core           ← 生命周期核心
├── lifecycle-startup        ← 启动流程
├── cron-cli                 ← 定时任务
├── jobs                     ← 作业管理
└── schedule                 ← 调度器
```

**MSS 视角**: OpenClaw 的心跳系统驱动了周期性任务 (我们一直在用的 AGENTS.md HEARTBEAT 指令)。MSS 的 Benchmark 夜间 cron (`run_nightly_bench.py`) 很简陋，缺少心跳检测和失败重试。

**吸收点**: `heartbeat-runner` 的模式 — MSS 的定期审计/Benchmark 应该用同样的结构化调度器，而不是裸 `cron`。

---

## 三、OpenClaw 的 8 个架构亮点（MSS 应吸收）

| # | 模式 | OpenClaw 实现 | MSS 缺口 | 优先级 |
|---|------|-------------|---------|--------|
| 1 | **频道抽象** | 18+ 频道统一接口 (core/inbound/reply/lifecycle/policy) | MSS 无输出频道概念 | P1 |
| 2 | **审批链** | 过滤→认证→渲染→人类决策→转发→执行 | DeferGuard 是单点检查 | P1 |
| 3 | **Session 持久化** | 多维度 (身份/成本/历史/绑定) 会话容器 | Tactic 是瞬态的 | P1 |
| 4 | **Plugin SDK** | 150+ export paths 的外部可扩展接口 | MSS 无插件体系 | P1 |
| 5 | **Provider 注册** | 30+ 模型供应商 + OAuth/API Key 轮转 | 只有硬编码连接 | P2 |
| 6 | **多道防线安全** | SSRF + 危险名称 + 工具策略 + 审计 + 沙盒 | mss_sandbox 只有导入白名单 | P2 |
| 7 | **向量记忆** | LanceDB 语义搜索 + 文件系统双轨 | conv_search 只有文本搜索 | P2 |
| 8 | **CLI 命令组** | 20 组 100+ 命令 分组注册 | 35 命令平铺 | P3 |

---

## 四、OpenClaw 的 5 个结构性短板（MSS 的优势）

| # | 短板 | OpenClaw 表现 | MSS 已有 |
|---|------|-------------|---------|
| 1 | **无热税计量** | Token 计数有 (provider-usage)，但不知道浪费了多少 | ✅ A3 三层热税 |
| 2 | **无 Δ 开放度** | 会话状态丰富但不追踪"Agent 在变好还是变坏" | ✅ Δ 维持条件 |
| 3 | **无矛盾消解** | subagent 之间可以通信但无 A6 升维 | ✅ dialog_fork.py |
| 4 | **无蜕壳机制** | 配置是静态的，心跳不自我改进 | ✅ H604 蜕壳协议 |
| 5 | **无信任预算** | 执行审批是二元 (通过/拒绝)，无中间态 | ✅ H634 trust_budget |

---

## 五、战略建议

### 立即可做 (本周)

1. **吸收 OpenClaw 的 Session 模式到 MSS Tactic**
   - `MSSTactic` 加持久化 (Tactic → TacticSession)
   - 每次 `call()` 自动保存状态
   - 支持 `session.resume()` 恢复中间状态

2. **吸收审批链到 DeferGuard**
   - 从单点 `can_execute()` 升级为 `MSSApprovalChain`
   - 支持多条件组合 + 降级策略

3. **吸收频道抽象到 MSS 多 Agent 响应**
   - 统一的 `MSSChannel` 接口
   - 不同 Agent 输出经过同一管道格式化

### 下周可做

4. **研究 OpenClaw 的 Plugin SDK 导出体系**
   - 为 MSS 设计一套类似的 `plugin-sdk` 接口
   - 让外部可以写 MSS 兼容的 Agent 插件

5. **给 conv_search.py 加向量嵌入**
   - 借用 OpenClaw 的 LanceDB/sqlite-vec 模式

### 远望

6. **MSS 作为 OpenClaw 的一个 Channel 插件运行**
   - 这意味着 MSS 不只是"一个项目"，而是 OpenClaw 生态系统的一部分
   - 所有 MSS 的 Agent/会话/审批都通过 OpenClaw Gateway 暴露
   - 用户可以在 WebChat/Discord/Telegram 中调用 MSS 的 agent

---

**拆解完成时间**: 2026-06-17 GMT+8 | **来源**: 实际安装目录源码 (E:\QClaw\v0.2.27.560\resources\openclaw\node_modules\openclaw\dist\)
