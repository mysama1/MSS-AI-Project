# MSS-AI ROADMAP: v1.1 → v2.0

**Version:** 1.1 (Draft)  
**Date:** 2026-05-15  
**Status:** BC Phase v2.0 In Progress  

---

## Current State (v1.0.0)

- **Tests:** 26 suites / 344 tests, 100% pass, ~5.9s
- **Knowledge Base:** 142 entries (L1=30, L2=54, L3=57, L4=1)
- **GitHub:** mysama1/MSS-AI-Project @ commit `45bef79`
- **Core Modules:** 13 delivered (Symbolic Engine v3, NL Bridge v2, Hybrid Reasoning, Ω-Rules, Resilience Scan, CLI, Web API, Simulation, Visualization, WebSocket, Docs, Packaging, GitHub Release)

---

## Phase Breakdown

### Phase A: Knowledge Base Expansion (Week 5-6)
**Goal:** 142 → 500+ entries

| Sprint | Target | Content |
|--------|--------|---------|
| A1 | +100 entries | L1公理深化（AMFI, LLIA, 映射公理v5.4） |
| A2 | +100 entries | L2保护带扩展（BCT耦合, 热税公式, 韦伯-熵增重构） |
| A3 | +100 entries | L3试探法补充（组织韧性, 修真隐喻, 运行态） |
| A4 | +58 entries | L4审计归档（v9.1 AI幻觉, K3文明审计） |

**Deliverable:** `knowledge_base/` 12 files → 20+ files

---

### Phase B: Performance Optimization (Week 7-8)
**Goal:** Numba JIT + CUDA exploration

| Task | Description | Priority |
|------|-------------|----------|
| B1 | Numba JIT加速模拟框架 | P0 |
| B2 | CUDA内核探索（渗流相变并行化） | P1 |
| B3 | 缓存策略优化（lru_cache, 持久化缓存） | P1 |
| B4 | 异步IO优化（aiohttp替换同步调用） | P2 |

**Deliverable:** `performance_benchmark.py`, 性能基线报告

---

### Phase C: Docker & Deployment (Week 9-10)
**Goal:** 完整容器化部署

| Task | Description | Priority |
|------|-------------|----------|
| C1 | Dockerfile + docker-compose.yml | P0 |
| C2 | Ollama服务容器化 | P0 |
| C3 | 多阶段构建优化镜像大小 | P1 |
| C4 | Kubernetes部署清单（可选） | P2 |

**Deliverable:** `docker/`, 一键部署脚本

---

### Phase D: v2.0 Release (Week 11-12)
**Goal:** 版本冻结与发布

| Task | Description | Priority |
|------|-------------|----------|
| D1 | 版本冻结（功能锁定） | P0 |
| D2 | 完整CHANGELOG v1.0→v2.0 | P0 |
| D3 | 用户文档（安装指南、API文档、教程） | P0 |
| D4 | GitHub Release + 标签 | P0 |
| D5 | 性能基准报告 | P1 |
| D6 | 安全审计报告 | P1 |

**Deliverable:** GitHub Release v2.0.0

---

## Priority Matrix

| Priority | Task | ETA | Blockers |
|----------|------|-----|----------|
| P0 | KB扩展至500+ | Week 6 | 内容来源 |
| P0 | Numba JIT加速 | Week 8 | Numba安装 |
| P0 | Docker容器化 | Week 10 | Docker环境 |
| P0 | v2.0发布 | Week 12 | 前三项完成 |
| P1 | GPU CUDA探索 | Week 8 | CUDA toolkit |
| P1 | K8s部署 | Week 10 | 需求确认 |
| P2 | Web UI前端 | Week 12 | 前端资源 |
| P2 | 多语言支持 | Week 12 | 翻译资源 |

---

## Long-term Backlog (Post-v2.0)

- [ ] 组织韧性扫描器符号推理后端（P0，长期阻塞）
- [ ] v3引擎完全合并入MSSTactic主文件（P1）
- [ ] Gateway Monitor脚本部署（P1）
- [ ] 自指涉n=7极限熔断机制（P2）
- [ ] K3科学兼容性实验验证（P2，2-5年）
- [ ] 13B+模型支持（P2，硬件限制）

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-12 | B+C优先，A暂缓 | 7B模型限制需先突破 |
| 2026-05-15 | KB扩展优先于性能 | 知识密度是系统智能的基础 |
| 2026-05-15 | 500条目为v2.0门槛 | 保证核心领域覆盖度 |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| KB内容质量不足 | Medium | High | 严格L1/L2/L3分级审查 |
| Numba兼容性问题 | Medium | Medium | 纯Python fallback |
| Docker镜像过大 | Low | Low | 多阶段构建优化 |
| 7B模型能力瓶颈 | High | High | 后处理补偿+13B升级路径 |

