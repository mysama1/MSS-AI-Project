# DEV-001: JS/TS AST 真吞错检测 — 前置设计

**状态**: 前置准备 | **预计**: 5-7个有限块, 每块≤2h | **2026-06-05**

---

## 1. 范围锁定

**"真吞错"定义**: 运行时静默错误 (非语法错误, 非风格问题, 非类型警告)

| 真吞错 (检测) | 假吞错 (不检测) |
|:---|:---|
| `await` 缺失导致 Promise 未捕获 | ESLint no-floating-promises (已有) |
| 条件分支中类型收窄失效 | ESLint 类型检查 |
| `null` 传播到属性访问 | TSC strictNullChecks (已有) |
| 事件监听器未清理导致泄漏 | 内存profiling (运行时) |
| `try { } catch {}` 空catch吞错 | ESLint no-empty |
| React useEffect 缺少cleanup return | eslint-plugin-react-hooks (已有) |

**差异化**: 不重复 ESLint/TSC。聚焦 VDP 框架独有的检测维度。

## 2. VDP 规则 → JS/TS 映射

| VDP规则 | JS/TS 等效 | 检测模式 | 优先级 |
|:---|:---|:---|:---|
| V1_PATH | import/require 路径存在性 | AST遍历 → fs检查 | P0 |
| V2_ERROR | 空catch块 / .catch()无处理 / Promise链断裂 | AST模式匹配 | P0 |
| V4_ATOMIC | fs.writeFile无备份 / JSON.stringify直接覆写 | AST+语义分析 | P1 |
| V5_TIMEOUT | fetch/axios无超时 / 死循环无断路器 | AST模式 | P1 |
| V6_FACT | as断言 vs 运行时校验 / any逃逸 | AST+类型标注 | P1 |
| V7_CTX | 无 (话语模板特定, JS不适用) | — | — |

**新增JS专有规则**:

| ID | 规则 | 检测模式 |
|:---|:---|:---|
| V8_LEAK | useEffect/subscribe/addEventListener 无对应cleanup | AST配对检查 |
| V9_ASYNC | async函数内部throw vs reject / forEach+async | AST模式 |
| V10_NULL | `?.` 后继续属性访问 / `!` 非空断言滥用 | AST+语义 |

## 3. 架构决策

```
方案A: Node.js subprocess (babel/ts-morph)
  优点: 完整AST, 类型信息, 成熟生态
  缺点: 依赖Node.js, 跨进程开销, 输出解析脆弱

方案B: tree-sitter (Python binding)
  优点: 纯Python集成, 无外部进程, 快
  缺点: 无类型信息, 仅语法层AST

方案C: 混合 (tree-sitter语法 + TypeScript CLI类型)
  优点: 语法检测Python侧, 类型信息按需调tsc --noEmit
  缺点: 两套解析器

裁定: B (tree-sitter) → 够用且最简单。V6/V10可在后续升级到C。
```

**依赖**:
```bash
pip install tree-sitter tree-sitter-javascript tree-sitter-typescript
# tree-sitter 0.22+ 支持 Python 3.8+
```

## 4. 有限拆分 (5块, 防热寂)

### 块 1: Parser Shell (30min)
- [ ] 安装 tree-sitter + JS/TS grammar
- [ ] 创建 `js_scan.py` 骨架: AST解析 → 节点遍历 → 规则调度
- [ ] 自测: 解析 sample.js → 输出AST节点类型列表
- **检查点**: `py js_scan.py sample.js` 输出 `program → expression_statement → call_expression → ...`

### 块 2: V2_ERROR (60min)
- [ ] 空 catch 块检测: `catch (e) {}` 无语句
- [ ] .catch() 单参数无处理: `.catch(err => {})`
- [ ] Promise 链断裂: `p.then().then()` 无catch
- [ ] 3个测试用例 × 通过
- **检查点**: 扫描包含5种错误的 test_v2.js → 5 violations

### 块 3: V1_PATH + V5_TIMEOUT (45min)
- [ ] ESM import路径: `import foo from './missing.js'` → fs.exists
- [ ] CJS require路径: `require('../../nonexistent')`
- [ ] fetch/axios无超时参数: `fetch(url)` 无 signal/timeout
- [ ] 4个测试用例 × 通过
- **检查点**: test_v1v5.js → 4 violations

### 块 4: V8_LEAK + V9_ASYNC (60min)
- [ ] useEffect无cleanup: `useEffect(()=>{sub()})` 无return
- [ ] addEventListener无removeEventListener配对
- [ ] forEach+async: `arr.forEach(async (x)=>await f(x))` (静默吞错)
- [ ] 4个测试用例 × 通过
- **检查点**: test_v8v9.js → 4 violations

### 块 5: 集成 + 报告 (45min)
- [ ] `js_scan.py` 集成到 `vdp_pipeline.py`: 自动识别 .js/.ts/.jsx/.tsx
- [ ] JSON输出格式对齐 vdp_scan.py 规范
- [ ] 全量自测: 11规则 × test suite
- [ ] 集成到 skill_api.py: `POST /vdp/scan` 增加 `filetype: javascript`
- **检查点**: `vdp_pipeline.py` 扫描含JS/TS文件目录 → 统一报告

## 5. 抗中断策略

```
每块结束 → git commit + 写入 task_bar checkpoint
块内状态 → .run/js_scan_state.json (当前阶段/已通过测试)
恢复入口 → 读 checkpoint → 跳至未完成块
```

## 6. 成功标准

```
✅ 11条规则全部投产 (V1,V2,V4,V5,V6,V8,V9,V10 + 3个增强)
✅ 集成到 vdp_pipeline.py (自动识别.js/.ts/.jsx/.tsx)
✅ 集成到 skill_api.py (/vdp/scan 支持 javascript 类型)
✅ 测试套件 ≥11个文件, 每个文件包含2+故意错误
✅ 零假阳性 (扫描现有代码不报错)
```

## 7. 不做的

- ❌ TypeScript类型推导/类型检查 (TSC已有)
- ❌ JSX虚拟DOM diff分析 (React DevTools已有)
- ❌ 运行时插桩/覆盖率 (Jest/Istanbul已有)
- ❌ CSS/HTML解析 (Phase 2考虑)
