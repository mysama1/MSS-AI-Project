# MSS-AI 迁移指南

## 导出信息

- **导出时间**：2026-05-20T16:29:42.719938
- **源平台**：QClaw
- **目标平台**：u-claw
- **文件总数**：483
- **总大小**：3.81 MB

## 目录结构

```
MSS-AI-Export_20260520_1629/
├── project/          # 项目代码（C:\MSS-AI-Project）
│   ├── symbolic_engine_v4/
│   ├── knowledge_base/
│   └── ...
├── memory/           # 记忆文件
│   ├── MEMORY.md     # 长期记忆
│   ├── AGENTS.md     # Agent配置
│   ├── USER.md       # 用户画像
│   └── daily/        # 每日记忆
├── tasks/            # 任务系统
│   ├── task_system_data.json
│   └── ROADMAP*.md
└── config/           # 配置文件（脱敏）
    └── openclaw.json
```

## u-claw 导入步骤

### 1. 解压
```bash
unzip MSS-AI-Export_20260520_1629.zip
cd MSS-AI-Export_20260520_1629
```

### 2. 部署项目代码
```bash
# 复制到u-claw工作区
cp -r project/* /path/to/uclaw/workspace/
```

### 3. 恢复记忆
```bash
# 复制记忆文件
cp memory/MEMORY.md /path/to/uclaw/workspace/
cp memory/AGENTS.md /path/to/uclaw/workspace/
cp memory/USER.md /path/to/uclaw/workspace/
cp memory/SOUL.md /path/to/uclaw/workspace/

# 恢复每日记忆
cp memory/daily/* /path/to/uclaw/workspace/memory/
```

### 4. 恢复任务系统
```bash
# 复制任务数据
cp tasks/task_system_data.json /path/to/uclaw/workspace/
```

### 5. 安装依赖
```bash
cd /path/to/uclaw/workspace
pip install -r requirements.txt
```

### 6. 验证
```bash
python task_system.py
python test_core.py
```

## 注意事项

1. **API密钥**：config目录中的密钥已脱敏，需重新配置
2. **路径差异**：Windows路径（C:\）需改为Linux路径（/home/）
3. **u-claw兼容性**：部分QClaw特有功能可能需要适配
4. **IMA知识库**：需手动重新上传至u-claw的知识库系统

## 联系

如有问题，请联系项目管理员。
