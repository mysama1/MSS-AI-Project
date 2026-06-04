# OpenClaw Gateway Monitor - Windows计划任务安装脚本
# 以管理员权限运行此脚本安装监控任务

$TaskName = "OpenClawGatewayMonitor"
$MonitorScript = "C:\MSS-AI-Project\gateway_monitor.py"
$LogFile = "C:\MSS-AI-Project\gateway_monitor.log"

# 检查管理员权限
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "请以管理员权限运行此脚本"
    exit 1
}

# 检查监控脚本是否存在
if (-not (Test-Path $MonitorScript)) {
    Write-Error "监控脚本不存在: $MonitorScript"
    exit 1
}

# 删除旧任务（如果存在）
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "删除现有任务: $TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 创建任务动作
$Action = New-ScheduledTaskAction -Execute "python" -Argument "$MonitorScript --once" -WorkingDirectory "C:\MSS-AI-Project"

# 创建任务触发器（每5分钟）
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 365)

# 创建任务设置
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

# 创建任务对象
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings

# 注册任务
Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force

Write-Host "任务已安装: $TaskName"
Write-Host "检查间隔: 每5分钟"
Write-Host "日志文件: $LogFile"
Write-Host ""
Write-Host "查看任务状态: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "手动运行任务: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "删除任务: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
