# 桌面客户端拆解 — MSS 本地客户端完整版规划

> Phase 3: 独立桌面App (Electron/Tauri) — 离线可用，自托管全功能
> 当前: Phase 1 Canvas 预览版 → Phase 3 目标

## 一、技术选型: Tauri vs Electron

| 维度 | Electron | Tauri |
|------|----------|-------|
| 语言栈 | JS/TS + Chromium | Rust + 系统 WebView |
| 包大小 | ~150MB (Chromium) | ~5-15MB (系统WebView) |
| 内存占用 | ~200MB 起步 | ~50MB 起步 |
| 性能 | 中等 (V8) | 高 (Rust原生后端) |
| 生态成熟度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 跨平台 | Win/Mac/Linux ✅ | Win/Mac/Linux ✅ |
| 原生API | 需插件 | Rust直接调 |
| MSS兼容性 | Python需打包为子进程 | Python同样作为sidecar |

**建议: Tauri 优先** — MSS 是计算密集型 (Ollama/Python), Tauri 的 Rust 后端更适合做系统级进程管理

## 二、MSS 桌面客户端架构

```
┌─────────────────────────────────────────────────┐
│                  Tauri Shell                      │
│  ┌─────────────────────────────────────────────┐ │
│  │            WebView UI (React/Next.js)        │ │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │ │
│  │  │ Dashboard│ │ Playground│ │ KB Explorer │ │ │
│  │  │ 热税/Δ/道 │ │ Agent交互 │ │ H-ID浏览器  │ │ │
│  │  └──────────┘ └──────────┘ └─────────────┘ │ │
│  └─────────────────────────────────────────────┘ │
│           ↕ IPC (invoke/handle)                   │
│  ┌─────────────────────────────────────────────┐ │
│  │          Rust Backend (tauri::command)        │ │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │ │
│  │  │Process Mg│ │ File I/O │ │ System Tray │ │ │
│  │  │Ollama守  │ │ Config   │ │ 后台运行    │ │ │
│  │  └──────────┘ └──────────┘ └─────────────┘ │ │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │ │
│  │  │AutoUpdate│ │ Crash Rpt│ │ Native Notif│ │ │
│  │  │ 自动更新 │ │ 崩溃报告 │ │ 系统通知    │ │ │
│  │  └──────────┘ └──────────┘ └─────────────┘ │ │
│  └─────────────────────────────────────────────┘ │
│           ↕ sidecar process                      │
│  ┌─────────────────────────────────────────────┐ │
│  │        Python Sidecar (mssclaw)              │ │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │ │
│  │  │ skill_api│ │ Ollama   │ │ MSS Core   │ │ │
│  │  │ :53000   │ │ :11434   │ │ KB/VDP/SE  │ │ │
│  │  └──────────┘ └──────────┘ └─────────────┘ │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## 三、竞品桌面客户端拆解

### 3.1 ChatGPT Desktop (Electron)
```
Electron + React
├── 特点: Chromium内嵌, 系统托盘, 全局快捷键
├── 学习点: 托盘最小化, 快捷键唤起, 文件关联
└── 问题: 450MB内存, 慢启动
```

### 3.2 Ollama Desktop (Go + Wails/WebView)
```
Go backend + WebView2
├── 特点: 极轻 (<30MB), 后台守护, 系统托盘
├── 学习点: 进程管理UI, 模型下载进度, 日志查看
└── 问题: UI简陋 (无仪表盘概念)
```

### 3.3 LM Studio (Electron)
```
Electron + React
├── 特点: 模型市场, 一键下载, GPU配置
├── 学习点: 本地模型管理UI, 本地聊天, 下载进度条
└── 问题: 功能单一 (只管模型)
```

### 3.4 Open Interpreter (Electron/Terminal)
```
Electron/Terminal 双模式
├── 特点: 终端式IDE体验, OI模式
├── 学习点: Terminal-in-Desktop 模式
└── 问题: 仅聊天/代码, 无工程化概念
```

## 四、MSS 桌面的差异化定位

**所有现有桌面客户端都只是"AI聊天+模型管理"** — 没有一款做"意义工程学仪表盘"。

| 功能 | ChatGPT | Ollama | LM Studio | Open Interp. | **MSS Desktop** |
|------|---------|--------|-----------|-------------|----------------|
| AI聊天 | ✅ | ❌ | ✅ | ✅ | ✅ |
| 模型管理 | ❌ | ✅ | ✅ | ❌ | ✅ |
| 热税仪表盘 | ❌ | ❌ | ❌ | ❌ | ✅ **独有** |
| Δ开放度追踪 | ❌ | ❌ | ❌ | ❌ | ✅ **独有** |
| 道评分卡 | ❌ | ❌ | ❌ | ❌ | ✅ **独有** |
| A6事件日志 | ❌ | ❌ | ❌ | ❌ | ✅ **独有** |
| 信任预算仪表 | ❌ | ❌ | ❌ | ❌ | ✅ **独有** |
| 知识库浏览器 | ❌ | ❌ | ❌ | ❌ | ✅ **独有** |
| 系统托盘 | ✅ | ✅ | ✅ | ❌ | ✅ |
| 离线全功能 | ❌ | ✅ | ✅ | ❌ | ✅ **全部本地** |
| 多Agent对话 | ❌ | ❌ | ❌ | ❌ | ✅ **独有** |

## 五、实施路线

### Phase 3a: Tauri MVP (2-3周)
```
- Tauri v2 + React + Vite
- Sidecar: 启动/监控 Ollama + skill_api
- Dashboard: 从 Phase 1 Canvas 版迁移
- System tray: 最小化后台 + 快捷键唤醒
- 包大小: <40MB (.msi)
```

### Phase 3b: 功能完善 (3-4周)
```
- Agent Playground: 多Agent对话+热税实时跟踪
- KB Explorer: 离线知识库浏览
- Model Manager: 下载/切换/配置本地模型
- Offline mode: 完全无网络可用
```

### Phase 3c: 发布 (1-2周)
```
- Windows .msi + macOS .dmg + Linux .AppImage
- Auto-update (Tauri updater)
- 官网下载页 + GitHub Releases
```

## 六、关键决策

1. **Tauri > Electron**: MSS 不需要 Chromium, Rust 后端更适合做进程管理
2. **Sidecar 模式**: Python 不打包进客户端, 而是作为 sidecar 进程 — 用户已安装 Python+Ollama
3. **Web UI 技术栈**: React + Tailwind + Chart.js (与 Phase 1 Canvas 版共享代码)
4. **IPC 协议**: `tauri::command` → JSON IPC → Python sidecar (通过 HTTP localhost)

## 七、Phase 1 → Phase 3 代码复用

```
Phase 1 Canvas 仪表盘        →  Phase 3 Tauri 仪表盘
  dashboard/                    src/dashboard/
  ├── index.html            →   ├── HeatTaxGauge.tsx
  ├── SVG gauges            →   ├── DeltaChart.tsx
  └── Canvas sparkline      →   └── DaoScore.tsx
                                  
data.json 格式保持不变 → 同一套数据结构
```
