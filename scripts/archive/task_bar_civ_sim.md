# MSS 任务栏 — 2026-06-09

## 🟢 ComfyUI / Prompt Rewrite 管线

| 编号 | 任务 | 状态 | 备注 |
|------|------|------|------|
| PR-001 | ComfyUI 全家桶搬 E:\ | ✅ 完成 | 5个Junction, C盘释放12GB |
| PR-002 | SDXL Fast 管线 (Ollama+中英翻译) | ✅ 完成 | enable_ollama=true, target=sdxl |
| PR-003 | MSS Scene Decomposer (Pro双通道) | ✅ 完成 | 氛围+前景+中景+背景 4路CLIP |
| PR-004 | 光源分离系统提示词升级 | ✅ 完成 | 背景层独立光源type+color+position |
| PR-005 | ControlNet深度模型下载 | ✅ 完成 | 2.33GB, 844 tensors, valid |
| PR-006 | DepthAnythingV2 预处理器安装 | ✅ 完成 | kijai/ComfyUI-DepthAnythingV2 |
| PR-007 | ControlNet 两轮精炼工作流 | 🔄 用户施工中 | 第一轮底图→深度提取→第二轮锚定 |
| PR-008 | SFT 微调 Qwen2.5-7B | ⬜ 待执行 | sft_train.py就绪, pip install unsloth |
| PR-009 | Pro管线 v1.1 区域mask | ⬜ 规划中 | SAM/clipseg前景中景背景自动分割 |
| PR-010 | Pro管线 v1.2 IP-Adapter对象锚定 | ⬜ 规划中 | 广告牌/车辆用参考图锚定 |

## 🟡 MSS-AI 核心架构

| 编号 | 任务 | 状态 | 备注 |
|------|------|------|------|
| ARC-001 | heat_tax_fuse.py 三层级联熔断器 | ✅ 完成 | 5/5 自测 |
| ARC-002 | R-001 gradient_theft_detector.py | ✅ 完成 | 6/6 自测, 已集成agent.run() |
| ARC-003 | C-Weight gate cweight_gate.py | ✅ 完成 | 5/5 自测, 四层门控 |
| ARC-004 | Agent全量集成审计 | ✅ 完成 | 31/31 passed |
| ARC-005 | R-001 + C-Weight 进 agent.run() | ✅ 完成 | 自动拒绝夸赞驱动表演 |

## 🔵 巨鸟文明 / CIV-SIM

| 编号 | 任务 | 状态 | 备注 |
|------|------|------|------|
| CIV-001 | CIV编号统一 | ✅ 完成 | 40+条目→CIV-SIM/HIS/ARC/EVO/DIA/STR/PRT |
| CIV-002 | CIV-SIM001~010 文明模拟器总纲 | ⬜ 待用户补全方向 | 架构总纲/三阶段/气候探针/韧性陷阱/叙事黑洞/双轨/红铅笔/压测/Φ-GAUGE/Φ-WORKFLOW |
| CIV-003 | 韧性陷阱版全史深度展开 | ⬜ 待用户补全资料 | CIV-HIS001~010 |
| CIV-004 | 巨鸟帝国压测数据集 | ⬜ 待用户补全 | 农业/气候/难民/信任 具体数据 |
| CIV-005 | Φ协议公式化 | ⬜ 待用户补全 | γ_phase = γ₀×D⁻ⁿ 的参数确定 |
| CIV-006 | SIM-001 数字模拟器启动 | ⬜ 待CIV-002补全后执行 | 微观验证→宏观推演→闭环耦合 |

## 📋 对话提炼归档

| 编号 | 内容 | 状态 |
|------|------|------|
| DIA-001 | 2026-06-09 对话提炼: C-Weight/热税脱敏/二阶控制论/老子原型/定义暴力 | ✅ 已归档 |

---

## 下一步优先级

1. **用户**: CIV-SIM001~010 补全方向和资料 → CIV-003~006 启动
2. **用户**: ComfyUI ControlNet两轮工作流搭建 → PR-007 完成
3. **系统**: PR-008 SFT微调 → pip install unsloth → sft_train.py
4. **系统**: PR-009 v1.1 区域mask → SAM模型安装
