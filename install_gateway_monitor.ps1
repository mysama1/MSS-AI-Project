# OpenClaw Gateway Monitor Installation Script
# Creates a scheduled task to check gateway status every minute

$taskName = "OpenClaw-Gateway-Monitor"
$scriptPath = "C:\MSS-AI-Project\gateway_monitor.py"
$pythonPath = "python"

# Check if script exists
if (-not (Test-Path $scriptPath)) {
    Write-Error "Gateway monitor script not found: $scriptPath"
    exit 1
}

# Create task action
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "$scriptPath --once --log-file C:\MSS-AI-Project\gateway_monitor.log"

# Create task trigger (every minute)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)

# Create task settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force

Write-Host "Gateway Monitor installed successfully!"
Write-Host "Task: $taskName"
Write-Host "Check interval: 1 minute"
Write-Host "Log file: C:\MSS-AI-Project\gateway_monitor.log"
