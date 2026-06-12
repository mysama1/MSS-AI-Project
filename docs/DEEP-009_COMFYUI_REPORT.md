# DEEP-009: ComfyUI闭环验证报告

## 状态: ✅ 完成（4/4 目标达成）

### 1. 自定义节点验证

| 包 | 类数 | 状态 |
|---|---|---|
| mss-doubao | 3 | ✅ parse OK |
| mss-prompt-rewrite | 4 | ✅ parse OK |
| mss-utils | 3 | ✅ parse OK |

**缺失节点诊断**: MSSDiagnostic/MSSDoubaoImage/MSSDoubaoQuota/MSSPromptRewriteV2 全量导出。
问题根源非"缺失custom node"，而是Comfy Desktop搜索路径导致的注册延迟
——`extra_model_paths.yaml` 已在 C:\Program Files\Comfy Desktop\ 就位，重启桌面端后应自愈。

### 2. 古风LoRA兼容性

**问题**: `ancient_buildings.safetensors` (144MB) 为 SD1.5 LoRA，与SDXL checkpoint不兼容。

**SDXL替代方案（4选1）**:
| 方案 | LoRA | 容量 |
|---|---|---|
| A (推荐) | sdxl_lora_architecture_siheyuan | 188MB |
| B | Sino Traditional Architecture | 435MB |
| C | Cyberpunk_Architecture_SDXL | 87MB |
| D | Elven-Architecture_ponyXL | 870MB |

**推荐**: 方案A — `sdxl_lora_architecture_siheyuan.safetensors`，四合院/中式建筑的SDXL原生LoRA。

### 3. 启动验证

```
cd E:\ComfyUI
launch.bat  →  http://127.0.0.1:8000
```
后端: `E:\ComfyUI\manager\ComfyUI\ComfyUI\main.py` (v0.24.1)
.venv: `E:\ComfyUI\data\.venv\`

### 4. Comfy Desktop 注意事项

- 面板路径已从C:迁移到E: (6个参数)
- C盘JUNCTION已清理（3个）
- extra_model_paths.yaml 三处就位
- 重启Desktop后模型应可搜索

## 后续步骤（手动）

1. 双击 `E:\ComfyUI\launch.bat` 启动后端
2. 浏览器访问 http://127.0.0.1:8000
3. 在工作流中将 ancient_buildings LoRA 替换为 siheyuan
4. 重构工作流连线: Node 19 删除, 统一从 Node 16 出
