# OpenClaw Gateway Monitor

OpenClaw 网关状态自动检测与重启工具

## 功能特性

- **进程检测**：检查 QClaw.exe 进程是否存活
- **HTTP检测**：检查网关 HTTP 端口（默认3000）是否响应
- **自动重启**：连续3次检测失败后自动重启网关（需启用 --auto-restart）
- **日志记录**：完整的监控日志，便于故障排查
- **灵活配置**：支持自定义检查间隔、端口、日志路径

## 文件说明

| 文件 | 说明 |
|------|------|
| `gateway_monitor.py` | 核心监控脚本（Python） |
| `gateway_monitor_task.ps1` | Windows计划任务执行脚本 |
| `setup_monitor_task.bat` | 计划任务安装脚本（需管理员权限） |
| `gateway_monitor.log` | 监控日志文件（运行时生成） |

## 使用方法

### 方法1：手动运行（单次检测）

```bash
# 单次检测网关状态
python gateway_monitor.py --once

# 单次检测并自动重启（如果异常）
python gateway_monitor.py --auto-restart --once
```

### 方法2：守护模式（持续监控）

```bash
# 前台守护模式（每60秒检查一次）
python gateway_monitor.py --auto-restart

# 自定义检查间隔（每30秒）
python gateway_monitor.py --auto-restart --interval 30

# 自定义端口和日志
python gateway_monitor.py --auto-restart --port 8080 --log-file monitor.log
```

### 方法3：Windows计划任务（推荐）

1. **以管理员身份运行** `setup_monitor_task.bat`
2. 脚本会自动创建每5分钟执行一次的计划任务
3. 任务在后台运行，无需保持窗口打开

```bash
# 手动运行任务测试
schtasks /run /tn "OpenClawGatewayMonitor"

# 查看任务状态
schtasks /query /tn "OpenClawGatewayMonitor" /fo list

# 删除任务
schtasks /delete /tn "OpenClawGatewayMonitor" /f
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--auto-restart` | 启用自动重启功能 | 禁用 |
| `--interval` | 检查间隔（秒） | 60 |
| `--port` | 网关HTTP端口 | 3000 |
| `--log-file` | 日志文件路径 | gateway_monitor.log |
| `--once` | 只执行一次检测 | 守护模式 |

## 状态说明

监控器会检测以下状态：

- **健康**：进程存活 + HTTP响应正常
- **异常**：进程存活但HTTP无响应（可能网关卡死）
- **故障**：进程未找到 + HTTP无响应（网关已停止）

## 自动重启逻辑

1. 每次检测失败，连续失败计数器 +1
2. 当连续失败达到 **3次** 且启用了 `--auto-restart`：
   - 执行 `openclaw gateway stop` 停止网关
   - 等待3秒
   - 执行 `openclaw gateway start` 启动网关
   - 等待5秒
   - 验证重启是否成功
3. 重启成功后，计数器重置为0

## 日志示例

```
2026-05-12 04:48:00 [INFO] 网关正常: 健康 (进程存活 + HTTP响应)
2026-05-12 04:49:00 [WARNING] 网关异常 (1/3): 异常 (进程存活但HTTP无响应)
2026-05-12 04:50:00 [WARNING] 网关异常 (2/3): 异常 (进程存活但HTTP无响应)
2026-05-12 04:51:00 [WARNING] 网关异常 (3/3): 故障 (进程未找到 + HTTP无响应)
2026-05-12 04:51:05 [WARNING] 连续失败 3 次，触发自动重启
2026-05-12 04:51:10 [INFO] 网关重启成功: 健康 (进程存活 + HTTP响应)
```

## 故障排查

### 监控脚本无法找到 OpenClaw CLI

确保以下路径之一存在：
- `C:\Program Files\QClaw\resources\openclaw\config\bin\openclaw.CMD`
- `C:\Program Files\QClaw\QClaw.exe`
- PATH 环境变量中包含 openclaw

### 自动重启失败

1. 检查是否有权限执行 `openclaw gateway stop/start`
2. 检查日志中的错误信息
3. 尝试手动运行重启命令排查问题

### 计划任务不执行

1. 确认任务已创建：`schtasks /query /tn "OpenClawGatewayMonitor"`
2. 检查任务历史记录（任务计划程序 → 任务历史）
3. 确认 PowerShell 执行策略允许运行脚本

## 版本历史

- v1.0.0 (2026-05-12): 初始版本，支持进程检测、HTTP检测、自动重启
