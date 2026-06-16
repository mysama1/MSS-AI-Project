# mssclaw WebUI v2.0

基于吸收的顶级开源前端设计模式，从零重建。

## 吸收来源
| 来源 | Stars | 吸收模式 |
|---|---|---|
| LobeChat | ~50K | 对话面板 + 插件架构 + 主题系统 |
| NextChat | ~80K | 零后端架构 + Mask系统 + 流式渲染 |
| Dashboard Starter | ~5K | KBar命令面板 + shadcn/ui + React Query |

## 技术栈
- **Next.js 16** App Router (吸收: Dashboard Starter)
- **shadcn/ui** New York style (吸收: Dashboard Starter + LobeChat)
- **Tailwind CSS v4** (吸收: 全部)
- **Zustand** 状态管理 (吸收: LobeChat)
- **React Query** 数据获取 (吸收: Dashboard Starter)
- **react-markdown** + syntax highlighting (吸收: NextChat)

## 页面架构
```
/chat       — AI对话 (吸收: LobeChat 对话面板 + NextChat Markdown渲染)
/vault      — 密码保险箱 (吸收: Dashboard Starter 表格+搜索)
/models     — 模型目录 (吸收: LobeChat 卡片布局)
/library    — 库浏览器 (吸收: Dashboard Starter 侧边栏)
/settings   — 系统配置 (吸收: Dashboard Starter 表单)
```

## 设计系统
- **调色板**: zinc neutral (吸收: shadcn/ui New York)
- **字体**: Inter + JetBrains Mono (吸收: NextChat 代码渲染)
- **圆角**: 0.5rem (shadcn default)
- **间距**: 4px grid (吸收: Dashboard Starter)

## 启动
```bash
cd mssclaw/webui
npm install
npm run dev
# → http://localhost:3000
```

## 吸收记录
通过 `mssclaw absorb` 命令将 3 个顶级前端项目的设计模式吸收到 mssclaw 生态中。
吸收时间: 2026-06-16 Sprint 103
