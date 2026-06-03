@echo off
chcp 65001 >nul
echo ==========================================
echo MSS-AI Gateway Monitor
echo ==========================================
echo.
echo Starting monitor in foreground mode...
echo Press Ctrl+C to stop
echo.

python C:\MSS-AI-Project\gateway_monitor.py --auto-restart --interval 60 --log-file C:\MSS-AI-Project\gateway_monitor.log
