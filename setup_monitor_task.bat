@echo off
chcp 65001 >nul
title OpenClaw Gateway Monitor Task Setup
echo ==========================================
echo OpenClaw Gateway Monitor - 计划任务安装
echo ==========================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 请以管理员身份运行此脚本！
    pause
    exit /b 1
)

set "TaskName=OpenClawGatewayMonitor"
set "ScriptPath=C:\MSS-AI-Project\gateway_monitor_task.ps1"
set "LogPath=C:\MSS-AI-Project\gateway_monitor.log"

REM 检查脚本文件是否存在
if not exist "%ScriptPath%" (
    echo [错误] 监控脚本不存在: %ScriptPath%
    pause
    exit /b 1
)

echo [1/3] 删除现有任务（如果存在）...
schtasks /delete /tn "%TaskName%" /f >nul 2>&1

echo [2/3] 创建新的计划任务...
set "PSCmd=powershell.exe -ExecutionPolicy Bypass -File '%ScriptPath%'"
schtasks /create /tn "%TaskName%" /tr "%PSCmd%" /sc minute /mo 5 /rl highest /ru SYSTEM /np /f

if %errorlevel% neq 0 (
    echo [错误] 创建计划任务失败！
    pause
    exit /b 1
)

echo [3/3] 验证任务创建...
schtasks /query /tn "%TaskName%" /fo list | findstr "任务名称"

echo.
echo ==========================================
echo 计划任务创建成功！
echo ==========================================
echo 任务名称: %TaskName%
echo 执行频率: 每5分钟
echo 监控脚本: %ScriptPath%
echo 日志文件: %LogPath%
echo.
echo 手动运行测试: schtasks /run /tn "%TaskName%"
echo 查看日志: type "%LogPath%"
echo.
pause
