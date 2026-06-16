@echo off
chcp 65001 >nul
cd /d C:\MSS-AI-Project
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=utf-8

:: 检查是否已有监控进程在运行
tasklist /FI "WINDOWTITLE eq GatewayMonitor*" 2>nul | find "python.exe" >nul
if %errorlevel% == 0 (
    echo [WARNING] 监控进程已在运行
    pause
    exit 1
)

echo ==========================================
echo OpenClaw Gateway Monitor 守护进程
echo ==========================================
echo 自动重启: 启用
echo 检查间隔: 60秒
echo 日志文件: gateway_monitor.log
echo ==========================================
echo 按 Ctrl+C 停止监控
echo.

python gateway_monitor.py --auto-restart --interval 60 --log-file gateway_monitor.log

pause
