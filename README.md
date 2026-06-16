# mssclaw v0.3.0

**世界上第一个内置「意义场自检」的开源 Agent 框架**

```
mssclaw (框架平台)
├── mss-ai models     ← 本地模型 (mss-ai-v3.4.3-balanced等)
├── Agent 引擎         ← L2护城河 + 流式 + 工具 + RAG
├── Vault 保险箱       ← 密码管理全栈
├── Library 库系统     ← 工具库/技能库/知识库/免疫库/模型库
└── CLI 统一入口       ← mssclaw vault|chat|serve|absorb|library
```

## 🛡️ L2 独有护城河 (行业 0/40)
- 🔥 **A3 热税预算** — 自动拒绝无意义任务
- Δ **意义开放度检测** — 实时监控闭合/循环
- 🛡️ **规范场 + 幻觉盾** — 31规则+4类检测
- 🧠 **认知框架** — 能力自知+身份锚定+演化就绪
- 📊 **Δ 健康监控** — 不只"活着", 要"有意义"

## 🤖 Agent 核心能力
- **LLM 后端**: Ollama + OpenAI 兼容
- **流式输出**: 6模式 + 语义感知 + 深度折叠 + 速度对齐
- **工具调用**: 6内置工具 + L2 安检
- **RAG 管道**: BM25+密度, 零外部依赖
- **多Agent流水线**: Writer→Reviewer→Refiner
- **容错**: 重试+降级+熔断
- **记忆**: 三层存储 + 自动凝聚
- **评测**: 道评分 valid-pseudo×2.0

## 🔐 密码管理器全栈
- **加密**: AES-256-GCM, Zero-Trust
- **工具**: 生成器+TOTP+强度评估+8类模板
- **CLI**: `mss-vault` 15+命令
- **Web面板**: `mss-vault serve` → http://127.0.0.1:5099
- **HTTP API**: RESTful, 127.0.0.1 only
- **导入**: Chrome/Edge 一键迁移
- **备份**: 自动+旋转+恢复
- **体检**: 弱密码/重复/过期检测

## 📦 部署
- **Docker**: `docker-compose up`
- **双微服务**: Vault:5099 + Agent:5100
- **统一入口**: `mssclaw vault|chat|serve|demo|kb|health`
- **PyPI**: `pip install mss-agent==0.3.0`

## 🚀 快速开始
```bash
pip install mss-agent
mss-vault quickstart               # 一键初始化
mss-vault serve                    # Web面板
mssclaw chat --model qwen2.5:7b   # 终端AI
```

## 📊 行业评分
```
MSS-Agent:  27(能力) + 34(护城河) = 61/80  ← 总分第一
LangChain:  38(能力) +  0(护城河) = 38/80
Dify:       35(能力) +  0(护城河) = 35/80
```

## 🏗️ 架构
```
L2: HeatTax ↔ Delta ↔ NormField ↔ HalluShield ↔ CogFrame (+3桥)
Agent: LLM + 流式(6模式) + 工具(6+L2) + RAG + Pipeline + 评测
Vault: 加密 + CLI + Web + API + 导入 + 备份 + 健康
工程: Docker + 容错 + 持久化 + 统一入口 + 进程监控
```

## 📈 开发统计
- 50 Sprints | 115 Tests | 50 Commits
- 4.5小时连续构建 | 14:00 → 18:37
- GitHub: mysama1/MSS-AI-Project
- License: MIT
