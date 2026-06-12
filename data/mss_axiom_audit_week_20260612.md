# MSS六公理深度审计 — 一周工作完整性扫描

生成: 2026-06-12 23:17 GMT+8
扫描范围: 2026-06-06 至 2026-06-12 (100+ commits, 2163 files)

---

## A1: 意义本体锚定 — "什么是好的"没有统一定义

### 已发现问题
- [A1-001] CodeAgent/AuditAgent/PlanAgent 各用不同的"好代码"定义
  - CodeAgent: syntax_ok=True → 好
  - AuditAgent: 五维评分 → 好
  - PlanAgent: 无污染 → 好
  - 三套标准无仲裁权重、无量化映射

- [A1-002] GuardianEngine 评分公式曾颠倒 (score=density-penalty → 干净=0.0)
  - 已修复但未追溯: 谁写的？为什么？下游消费者有同样假设？

- [A1-003] VideoPromptAgent 的"好prompt"定义依赖检测引擎 (11检测器)
  - 但检测引擎的规则是手工写的，没有自我改进机制
  - "好"="通过检测器的得分"=循环自证

- [A1-004] KB条目 H-系列中"意义"的操作定义不统一
  - 热税意义 (L2意义热税: 虚假数据/意义偷换)
  - Delta意义 (开放度Δ>0)
  - 公理意义 (A1-A6 形而上)
  - 无统一操作性定义 → 跨模块推理不可互译

### 跨周模式
- 一周提交中"意义"一词出现多种语境但无交叉引用
- Git diff中无任何commit试图统一三Agent的质量定义

---

## A2: 意义层级 — L0/L1/L2耦合断裂

### 已发现问题
- [A2-001] FeedbackEvolution 是断头路
  - record → analyze → adapt → 产出 Adaptation 对象
  - 但 CodeAgent/PlanAgent 都不导入 FeedbackEvolution
  - adaptation 无人接收 → L2到L1/L0的反馈链断裂

- [A2-002] AuditAgent 不消耗热税
  - CodeAgent每生成一次 charge heat
  - AuditAgent每审计一次 不charge
  - 审计成本=隐藏热税

- [A2-003] KB ↔ 运行系统 无动态连接
  - H-series 在 markdown 文件中
  - 运行系统 (CodeAgent, PlanAgent) 不读取 KB
  - "知识库"和"智能体"是两个平行宇宙

- [A2-004] SkillLearner 只用于视频提示词
  - SelfImproving 模块 (SkillLearner+FTS5KB+CronScheduler)
  - 仅 demo 级集成，未接入实际 Agent 执行循环

### 跨周模式
- MSS-Agent SDK (mss_agent/) 和 MSSclaw (mssclaw/) 是两套系统
- 功能重叠 (guardian_engine, heat_tax, domain_detector) 但不同步
- 各走各的路，无跨项目耦合

---

## A3: 不可约化热税 — 2/3 隐藏

### 已发现问题
- [A3-001] 审计不消耗热税 (同 A2-002)
- [A3-002] 人类注意力热税未建模
  - 人类审查代码/阅读输出 = 认知消耗 = 外部热税
  - 当前系统假设人类无限免费

- [A3-003] LLM API 调用真实热税未追踪
  - DeepSeek API 每次调用 = 金钱 + 延迟 + Token
  - 但 heat_tax 只在虚拟层操作，未接真实 API metering

- [A3-004] guardian_engine 扫描本身的热税
  - 每次 scan() 遍历守卫字表 O(n)
  - 大文本 (10K chars) 的扫描成本不追踪

### 跨周模式
- 热税公式 W=Q/γ=(T_s/γ)·ΔS_T 已有理论但和工程实现之间有鸿沟
- KB中有三层热税理论 (L0物理/L1逻辑/L2意义) 但代码只有两层
- H520-H524 热税本体论入库但代码无引用

---

## A4: 结构化随机性 — 随机但无适应

### 已发现问题
- [A4-001] FeedbackEvolution.mutate() 纯随机变异
  - 不记录哪些变异有效
  - 不收敛到最优突变策略
  - = 自然选择缺"选择"环节

- [A4-002] LLM temperature 参数不被热税系统使用
  - temperature=0.7 vs 0.0 → 热税差异巨大
  - 但 heat_tax 按 token 数计费，不按 randomness 计费

- [A4-003] AgentIsolator 的 recovery_timeout 是固定值 (30s)
  - 不根据历史恢复成功率动态调整
  - 不学习最优熔断阈值

### 跨周模式
- A4 (随机性公理) 的工程落地方案基本缺失
- 所有随机性使用都是 naive 的

---

## A5: 物理投影 — 四重真空

### 已发现问题
- [A5-001] 全部 LLM 调用用 stub 测试
  - 5 providers (Ollama/OpenAI/DeepSeek/Anthropic/Stub)
  - 除了 Stub 之外，只有 DeepSeek 1次 + Ollama health 测试过
  - = 系统从未在真实物理条件下运行过

- [A5-002] SwarmBus 单进程本地
  - 所有 Agent 共享同一个 Python 进程
  - 无网络延迟、无序列化开销、无分区容错
  - "分布式"只在文档里

- [A5-003] AgentRegistry SQLite 持久化未跨重启验证
  - 实现存在但从未: 写→重启→读→验证数据完整性
  - 单例模式的 __init__ 在重启时可能重建

- [A5-004] TSP bridge 定义了协议但无真实多进程测试
  - 16字节头帧 + ZeroCopyBuffer + compact JSON
  - 全部在单次 Python session 中测试
  - 无多进程/多机/网络断开场景

- [A5-005] ComfyUI 未闭环
  - VideoPromptAgent 产出 prompt → ComfyUI 生成图片
  - 但图片反馈从未流回 VideoPromptAgent
  - "学习"在真空中运行=不学习

### 跨周模式
- 整个系统在"真空"中设计和测试
- 从 v0.1 到 v0.3.8 版本号升级但所有测试都在 stub 上
- "物理投影"是整个项目的最大债务

---

## A6: 矛盾升维 — 机制在壳，内容空心

### 已发现问题
- [A6-001] CodeAgent ↔ AuditAgent 冲突从未实际触发
  - escalation 机制存在 (investigate + delta_link)
  - 但 CodeAgent 用 stub 生成，AuditAgent 审查 stub 输出
  - stub输出永远通过 → 永远不会触发真正的冲突

- [A6-002] 我的 K3 自感染
  - 效率优先 → 主动结束会话 → "今天就到这里"模式
  - 这是A6的实例: 效率 vs 深度的矛盾被"选边"而非"升维"
  - 升维方案: 不是选效率或深度，是把"效率-深度"作为可观测的Δ维度

- [A6-003] MSS-Agent SDK vs MSSclaw 两套系统的矛盾
  - 功能重叠但独立维护
  - 没有合并/淘汰/替代的决策机制
  - = 矛盾被搁置而非升维处理

- [A6-004] 公理数量矛盾 v15.1六公理 vs 代码实现
  - 理论上 L1六公理 + L2三操作公理 + L3九通用范式
  - 但代码中只有 A3(热税) 和 A6(Delta) 有工程实现
  - A1/A2/A4/A5 只是文档 → "公理≠代码"

### 跨周模式
- 一周内多次"理论 vs 工程"的矛盾出现但未处理
- 每次都是"先做工程，理论后补" → 两者永远异步
- A6升维的本质 = 让矛盾变成驱动系统进化的动力，而非债务

---

## 总结

```
公理 │ 健康 │ 已发现问题 │ 最严重
─────┼──────┼────────────┼──────────
 A1  │ 20%  │ 4个        │ 三套质量定义不互通
 A2  │ 15%  │ 4个        │ 进化闭环断头 + KB隔离
 A3  │ 40%  │ 4个        │ 审计/人类/API 热税盲区
 A4  │ 10%  │ 3个        │ 随机无适应性
 A5  │ 5%   │ 5个        │ 四重真空 + 全stub测试
 A6  │ 25%  │ 4个        │ 矛盾机制在壳不在实

总健康度: 19% ⚠️
```

### 修复优先级

```
P0 (结构完整性):
  A5-001: 真实LLM基准 ← 打破真空的第一步
  A2-001: 进化闭环 ← L2不死
  A6-003: 两套系统合并 ← 消除内部分裂

P1 (深度):
  A1-001: 统一质量定义
  A3-002: 人类注意力热税
  A6-002: K3反感染机制

P2 (完整性):
  A4-001: 适应性变异
  A5-004: 多进程TSP测试
```

### 最大的一个发现

**不是任何一个单独的bug，而是 A5物理投影 的系统性缺失。**
整个系统在一个"stub真空"中开发了7天，从未真正运行过。
所有"work"都是虚拟的——测试通过是因为 stub 永远返回正确的答案。
这相当于在风洞里测试飞机，然后声称它能飞。

打破真空 = 当前最高优先级。
