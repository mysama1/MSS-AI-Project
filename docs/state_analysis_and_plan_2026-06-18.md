# MSS-AI 全系统状态分析与优先级规划
> 2026-06-18 00:09 GMT+8 | Sprint 211

## 一、真实状态

| 维度 | 数值 | 评价 |
|------|------|------|
| 核心模块 | 146 .py | 重度膨胀 — 需要功能聚类 |
| 文档 | 45 md | 覆盖广但缺乏统一索引 |
| 测试文件 | 46 | 覆盖参差不齐 |
| CLI 命令 | 36 | 零散，缺分组导航 |
| Ollama 模型 | 10 | nomic-embed-text 刚就绪 |
| 服务 | 3/3 UP | skill_api / blackhole / ollama |
| Phase 1 | Canvas 仪表盘 | ✅ 已上线 |
| Phase 2 | Dify桥+前端拆解 | ✅ 分析完成 |
| Phase 3 | 桌面客户端 | ✅ 拆解完成 |
| nomic-embed-text | 274MB | 🆕 刚下载完成 |

## 二、当前瓶颈诊断

### 🔴 高优先级

1. **向量记忆模块未验证** — nomic-embed-text 刚就绪，12 logic tests通过但 7 integration tests未跑
2. **146核心模块无功能架构图** — 人/新Agent难以快速定位目标模块
3. **测试覆盖率不均衡** — 46文件从哪来到哪去，分布不明
4. **Gateway 重启标记为TODO已悬空多轮** — LCM调优未生效

### 🟡 中优先级

5. **KB搜索索引需刷新** — `nomic-embed-text` 就绪后可通过向量增强
6. **热税扫描器只有离线版** — `heat_tax_self_scan.py` 未集成到仪表盘实时数据
7. **Dify 工具桥(离线demo通过)但无Live集成测试**
8. **46个test文件散落无组织结构图**

### 🟢 低优先级 / 优化

9. **ConvSearch v2.0 语义别名未对接向量搜索**
10. **白皮书 v1.4 → v1.5** (需纳入Sprint 208-211产出)
11. **废弃模型清理** — v3.4.2-production/final/slim 占 ~14GB

## 三、优先级路线图

```
现在 ──┬── [P0] 向量记忆集成验证 (15min)
       │    ├─ test_vector_memory.py 全量跑
       │    ├─ vector_memory → dashboard 数据管线
       │    └─ kb_search.py 向量增强
       │
       ├── [P1] 146模块功能架构图 (15min)  
       │    ├─ 自动扫描→生成 ARCHITECTURE.md
       │    └─ 按功能域分组 (Agent/VDP/ToolChain/Defense/...)
       │
       ├── [P2] 测试覆盖率分布图 (15min)
       │    ├─ 扫描 tests/ → 映射回 core/ 模块
       │    └─ 生成覆盖率矩阵 (哪个模块有多少测试)
       │
       ├── [P3] 全量回归测试 (15min)
       │    └─ 46文件 pytest 全跑
       │
       └── [P4] Gateway 重启 (2min, 阻塞项消除)
            └─ LCM 调优生效

今天 ──┬── [A] dashboard 实时数据升级
       │    └─ +向量记忆状态 +热税实时扫描 +服务体检
       │
       ├── [B] 白皮书 v1.5
       │    └─ 纳入 Phase 1-3 全链路
       │
       └── [C] 38th CLI → 36→38 命令分组

本周 ──┬── [D] Tauri 客户端 MVP 骨架
       │    └─ Rust + React + Python sidecar
       │
       └── [E] Dify 桥 Live 集成
            └─ 实际调 Dify API 验证工具链路
```

## 四、立即可并行的4件事

| # | 任务 | 工具 | 时间 |
|---|------|------|------|
| 1 | 向量记忆全量测试 | pytest | 2min |
| 2 | 146模块架构图生成 | python scan | 2min |
| 3 | 全量回归测试 | pytest | 5min |
| 4 | Gateway 重启 | openclaw gateway | 1min |

## 五、模块膨胀诊断 (146 .py)

```
mssclaw/core/ (146 files)
├── 核心引擎 (~15): l2op_v3, mcdp, mcdp_v2, pipeline, scene_router...
├── 防御系统 (~12): defense_pipeline, vaccine_efficacy, virus_taxonomy...
├── Agent框架 (~10): mss_agent, mss_session, mss_channel, mss_approval_chain...
├── 审计/SE (~8):  se_audit, heat_tax_self_scan, defer_guard...
├── 实验/评测 (~10): experiment_runner, ollama_benchmark, bench_lite...
├── 知识/记忆 (~8):  kb_search, conv_search, vector_memory, vector_search...
├── 工具桥接 (~5):  mss_tool_provider, mcp_client, mss_prompt, mss_tactic...
├── 基础设施 (~15): vault, init_env, dashboard_export, model_catalog...
├── 理论基础 (~10): normative_field, evolutionary_loop, observable...
└── 未分类/杂项 (~50+): 大量早期/试验性模块
```

**关键发现: 50+ 模块属于"功能探索期"产物，不清除但要标记状态。**

## 六、风险预警

| 风险 | 概率 | 影响 |
|------|------|------|
| Gateway 重启后 LCM 调优异常 | 中 | 800MB DB 再次 SIGKILL |
| 向量记忆集成失败 (Ollama embed 端点问题) | 低 | nomic-embed-text 已可用 |
| 全量回归发现隐藏breakage | 中 | 46文件未经全跑 |
| 模块膨胀导致新Agent难以定位 | 高 | 无架构图 |

## 七、建议执行

立即并行发射 4 项 (P0-P4)，30 分钟内完成全链路验证，
然后深度推进 A/B/C/D/E 中用户指定方向。
