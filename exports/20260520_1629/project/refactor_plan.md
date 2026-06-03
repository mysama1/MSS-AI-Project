# MSS-Tactic 重构计划

## 问题诊断

`mss_tactic_integrated.py` 1004行，存在以下问题：

### 1. 类过大 (God Class)
- `MSSTactic` 类包含太多职责：仲裁、生成、模型管理、技能加载、对话分叉、电源管理、后处理、知识库、检查点、Ω级合规、符号引擎、韧性扫描、稳定性监控

### 2. 混合抽象层级
- 同一文件中混合了：数据类(ArbiterResult/Dialog)、枚举(Layer/ComplianceStatus)、核心类(ArbiterAgent/MSSTactic)

### 3. 延迟初始化混乱
- 多个 `_ensure_*` 方法，运行时才知道是否初始化

### 4. 测试代码混杂
- 文件末尾包含 `if __name__ == "__main__"` 测试代码

## 重构方案

### Phase 1: 提取数据类和枚举 (立即执行)

```
mss_tactic_integrated.py
├── 提取 → mss_types.py (数据类+枚举)
│   ├── Layer (Enum)
│   ├── ComplianceStatus (Enum)
│   ├── ArbiterResult (dataclass)
│   └── Dialog (dataclass)
```

### Phase 2: 提取 ArbiterAgent (立即执行)

```
mss_tactic_integrated.py
├── 提取 → arbiter_agent.py (200行)
│   ├── ArbiterAgent 类
│   ├── FORBIDDEN_MAP
│   ├── L1_KEYWORDS
│   └── L2_KEYWORDS
```

### Phase 3: 提取 MSSTactic 为多个 Mixin (本周执行)

```
mss_tactic_integrated.py
├── 提取 → mixins/
│   ├── power_mixin.py (电源管理相关)
│   ├── stability_mixin.py (稳定性监控相关)
│   ├── symbolic_mixin.py (符号引擎相关)
│   ├── resilience_mixin.py (韧性扫描相关)
│   └── postprocess_mixin.py (后处理相关)
```

### Phase 4: 清理测试代码 (立即执行)

```
提取 → test_mss_tactic_integration.py
删除 mss_tactic_integrated.py 末尾的测试代码
```

## 预期效果

| 文件 | 重构前行数 | 重构后行数 | 减少 |
|:---|:---|:---|:---|
| mss_tactic_integrated.py | 1004 | ~400 | 60% |
| arbiter_agent.py | 0 | ~200 | 新增 |
| mss_types.py | 0 | ~50 | 新增 |
| mixins/*.py | 0 | ~400 | 新增 |
| **总计** | **1004** | **~1050** | 结构优化 |

## 实施步骤

1. **创建 mss_types.py** — 提取数据类和枚举
2. **创建 arbiter_agent.py** — 提取 ArbiterAgent
3. **修改 mss_tactic_integrated.py** — 导入新模块，删除提取的代码
4. **运行测试** — 确保26套件/344测试仍然通过
5. **创建 mixins/** — 逐步提取其他功能
6. **验证** — 每次提取后运行测试

## 风险

- **低风险**：纯代码移动，无逻辑变更
- **缓解**：每次提取后立即测试
- **回滚**：Git历史完整，可随时回滚
