# MSS-AI Gateway Monitor - Windows Task Scheduler Installation
# Run as Administrator

$taskName = "MSS-AI-GatewayMonitor"
$scriptPath = "C:\MSS-AI-Project\gateway_monitor.py"
$pythonPath = "python"

# Check if running as admin
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "Please run this script as Administrator"
    exit 1
}

# Remove existing task if exists
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing task: $taskName"
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create action
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "$scriptPath --auto-restart --interval 60 --log-file C:\MSS-AI-Project\logs\gateway_monitor.log"

# Create trigger (at startup + every 5 minutes)
$trigger1 = New-ScheduledTaskTrigger -AtStartup
$trigger2 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 9999)

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

# Register task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger1,$trigger2 -Settings $settings -Description "MSS-AI OpenClaw Gateway Monitor - Auto restart on failure" -RunLevel Highest

Write-Host "Task installed successfully: $taskName"
Write-Host "Monitor logs: C:\MSS-AI-Project\logs\gateway_monitor.log"
