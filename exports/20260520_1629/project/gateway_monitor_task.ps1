# OpenClaw Gateway Monitor - Windows计划任务脚本
# 每5分钟检查一次网关状态，异常时自动重启

$LogFile = "C:\MSS-AI-Project\gateway_monitor.log"
$MonitorScript = "C:\MSS-AI-Project\gateway_monitor.py"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Write-Log {
    param([string]$Message)
    $LogEntry = "[$Timestamp] $Message"
    Add-Content -Path $LogFile -Value $LogEntry
    Write-Output $LogEntry
}

# 检查监控脚本是否存在
if (-not (Test-Path $MonitorScript)) {
    Write-Log "ERROR: 监控脚本不存在: $MonitorScript"
    exit 1
}

# 运行监控检查
Write-Log "正在检查网关状态..."

try {
    $Result = & python $MonitorScript --once 2>&1
    $ExitCode = $LASTEXITCODE
    
    if ($ExitCode -eq 0) {
        Write-Log "网关状态: 正常"
    } else {
        Write-Log "网关状态: 异常，尝试自动重启..."
        
        # 尝试自动重启
        $RestartResult = & python $MonitorScript --auto-restart --once 2>&1
        $RestartExitCode = $LASTEXITCODE
        
        if ($RestartExitCode -eq 0) {
            Write-Log "自动重启成功"
        } else {
            Write-Log "自动重启失败: $RestartResult"
        }
    }
} catch {
    Write-Log "ERROR: 执行监控脚本时出错: $_"
}
