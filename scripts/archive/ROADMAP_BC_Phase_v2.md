# MSS-AI 路线图: B+C Phase v2.0

> 状态: BC Phase v1.0 已完成，进入 v2.0 增强阶段
> 更新时间: 2026-05-15

---

## 完成状态回顾

### BC Phase v1.0 交付 (2026-05-06 至 2026-05-15)

| # | 模块 | 文件 | 测试 | 状态 |
|---|------|------|------|------|
| 1 | 符号推理引擎v3 | `symbolic_engine_v3.py` | 31/31 | ✅ |
| 2 | 自然语言桥接V2 | `nl_bridge_v2.py` | 13/13 | ✅ |
| 3 | 混合推理系统 | `hybrid_reasoning.py` | 8/8 | ✅ |
| 4 | Ω级裁定规则 | `symbolic_rules_omega.py` | 33/33 | ✅ |
| 5 | 组织韧性扫描 | `organizational_resilience.py` | 14/14 | ✅ |
| 6 | 交互式CLI | `interactive_cli.py` | 10/10 | ✅ |
| 7 | Web API原型 | `web_api.py` | 7/7 | ✅ |
| 8 | 数值模拟框架 | `simulation_framework.py` | 15/15 | ✅ |
| 9 | 可视化引擎 | `visualization_engine.py` | 14/14 | ✅ |
| 10 | 完整文档 | README/ARCHITECTURE/API_GUIDE/CHANGELOG | - | ✅ |
| 11 | 打包配置 | `setup.py` + `requirements.txt` | - | ✅ |
| 12 | GitHub发布 | v1.0.0 | - | ✅ |

**测试基准**: 24套件/308测试，100%通过，~4.8s

---

## BC Phase v2.0 目标

基于已完成基础，进入**增强与优化**阶段：

### 方向1: 性能优化 (Numba JIT)
**目标**: 模拟框架计算速度提升10-100x
**理由**: 当前纯NumPy实现，渗流模拟50×50网格~50ms，可优化至<5ms

### 方向2: 容器化部署 (Docker)
**目标**: 一键部署，跨平台运行
**理由**: 当前仅Windows本地运行，需支持Linux服务器部署

### 方向3: WebSocket实时通信
**目标**: 实时状态推送，交互式可视化
**理由**: 当前HTTP轮询，WebSocket更适合监控场景

### 方向4: 知识库扩展
**目标**: 从312条扩展至500+条
**理由**: 更多领域覆盖，提升推理能力

---

## Phase v2.0 详细规划

### Week 1-2: 性能优化

**Day 1-3: Numba JIT集成**
- [ ] 安装numba (`pip install numba`)
- [ ] 渗流模拟器JIT编译
- [ ] ETA动力学JIT编译
- [ ] 基准测试对比

**Day 4-7: 并行计算**
- [ ] 多核并行参数扫描
- [ ] 批次模拟并行化
- [ ] GPU加速探索（CUDA via Numba）

**预期收益**:
- 渗流模拟: 50ms → 5ms (10x)
- 参数扫描: 串行 → 并行 (N核加速)

### Week 3-4: Docker容器化

**Day 8-10: Dockerfile**
- [ ] 多阶段构建（减小镜像体积）
- [ ] Python 3.11 slim基础镜像
- [ ] 依赖缓存优化

**Day 11-14: Docker Compose**
- [ ] 服务编排（API + CLI + Monitor）
- [ ] 数据卷挂载（知识库/日志）
- [ ] 环境变量配置

**Day 15: 验证**
- [ ] Windows Docker Desktop测试
- [ ] Linux服务器测试
- [ ] 性能对比（容器vs原生）

### Week 5-6: WebSocket增强

**Day 16-18: WebSocket服务端**
- [ ] FastAPI WebSocket端点
- [ ] 实时状态推送
- [ ] 订阅/取消订阅机制

**Day 19-21: 前端原型**
- [ ] 简单HTML/JS客户端
- [ ] 实时图表更新
- [ ] 系统监控面板

**Day 22: 集成测试**
- [ ] 并发连接测试
- [ ] 长时间运行稳定性

### Week 7-8: 知识库扩展

**Day 23-25: 自动条目生成**
- [ ] 从MSS理论文档提取
- [ ] 结构化转换（JSONL）
- [ ] 质量验证

**Day 26-28: 领域扩展**
- [ ] 物理学条目（量子力学/热力学）
- [ ] 生物学条目（进化论/生态学）
- [ ] 社会学条目（组织理论/网络科学）

**Day 29-30: 验证**
- [ ] 知识图谱一致性检查
- [ ] 推理路径验证
- [ ] 性能影响评估

---

## 技术决策

### Numba vs Cython
- **选择Numba**: 无需修改Python代码，装饰器即可JIT
- **放弃Cython**: 需要额外编译步骤，增加复杂度

### Docker基础镜像
- **选择python:3.11-slim**: 平衡体积与功能
- **放弃alpine**: musl libc兼容性问题

### WebSocket库
- **选择FastAPI原生**: 与现有API统一，减少依赖
- **放弃Socket.IO**: 额外依赖，功能过剩

---

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Numba兼容性问题 | 中 | 中 | 回退至纯NumPy，条件导入 |
| Docker体积过大 | 低 | 低 | 多阶段构建，slim镜像 |
| WebSocket并发限制 | 低 | 中 | 异步处理，连接池 |
| 知识库质量下降 | 中 | 高 | 自动验证+人工审核 |

---

## 成功标准

### 4周后 (Week 1-2完成)
- [ ] Numba JIT集成完成
- [ ] 渗流模拟速度提升10x+
- [ ] 参数扫描支持并行

### 8周后 (Week 3-8完成)
- [ ] Docker镜像可运行
- [ ] WebSocket实时通信可用
- [ ] 知识库扩展至500+条
- [ ] v2.0发布

---

## 下一步行动

**立即执行**:
1. 安装Numba (`pip install numba`)
2. 创建Dockerfile
3. 开始渗流模拟器JIT优化

**等待决策**:
- v2.0优先级排序（性能/容器/WebSocket/知识库）
- 是否跳过某些方向
- 时间线调整

---

*文档版本: v2.0*
*状态: 草稿，待用户确认*
