# TH-2026-005: 模块缓存污染 — MSS 新诊断类 L2-011

## 发现背景

TRAE SOLO 沙盒故障诊断中，用户识别出根因非物理沙箱，而是 Python `sys.modules` 
缓存了旧版模块。磁盘文件正确，但运行时使用的是过时的内存缓存。所有下游执行结果
因此"认知受损"。

## MSS 分类: L2-011 — 逻辑病毒 / 陈旧模块缓存

### 为什么是"逻辑病毒"?

| 特征 | 生物病毒 | 模块缓存污染 |
|:---|:---|:---|
| 自身不致命 | ✅ 不破坏文件 | ✅ sys.modules 无害 |
| 劫持宿主机制 | ✅ 利用细胞复制 | ✅ 利用 Python import 链 |
| 传播性 | ✅ 感染其他细胞 | ✅ import 依赖链传播 |
| 症状延迟 | ✅ 潜伏期 | ✅ 执行结果错误，非加载时报错 |
| 隐蔽性 | ✅ 免疫系统识别困难 | ✅ 磁盘 diff 检查才能发现 |

### 热税分析

```
T_direct(缓存污染) = 0       # .pyc 旧于 .py 本身无直接消耗
T_potential(缓存污染) = Σ(下游调用 × 错误结果代价)
                     = 极高  # 所有依赖链上的执行都受影响
```

这正是**热税短视症**的典型案例：零直接热税，但潜在热税爆炸性增长。

## 检测方法

### 方法 1: 文件时间戳比对

```
∀ module ∈ sys.modules:
  if .py 的 mtime > .pyc 的 mtime:
    → STALE (模块加载后源文件被修改过)
  if __pycache__/*.pyc 不存在且 .py 存在:
    → SUSPICIOUS (Python 应自动生成 .pyc)
```

### 方法 2: 哈希比对 (更强)

```
.py 的 SHA256 ≠ __pycache__/*.pyc 对应节段的 SHA256
  → CONTAMINATED (缓存与源码不一致)
```

### 方法 3: 运行时版本检查

```
module.__version__ ≠ importlib.metadata.version(module)
  → VERSION_MISMATCH
```

## 修复

1. **即时**: `importlib.reload(module)` — 强制重载
2. **彻底**: 删除 `__pycache__/` 目录 + 重启 Python 进程
3. **预防**: CI/CD 中加 `find . -name __pycache__ -exec rm -rf {} +` 在每次部署前

## 在 MSS 诊断体系中的位置

```
L1 公理:  A4 固有随机性 → 缓存不一致是 A4 的一种表现形式
L2 定理:  L2-011 = 模块陈旧缓存 = 热税短视症的子类
L3 工具:  module_cache_detector.py → 自动化检测
L4 工程:  CI/CD 清缓存步骤 → 预防措施
```

## 已部署工具

```
python module_cache_detector.py --project-dirs E:\QClaw-Data\skills E:\AI_Workspace\MSS-AI
```

输出:
- STALE_MODULES: 所有 sys.modules 中陈旧条目
- PROJECT_CONTAMINATION: 项目目录中的污染模块

## 关联

- H456: 超显化假说 (预算独占→缓存独占 类比)
- CLOSURE-2026-002: Collatz 不等式方向错误的根因之一可能就是缓存污染
- "热税短视症": T_direct=0 但 T_potential 极高
