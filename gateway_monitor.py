#!/usr/bin/env python3
"""
OpenClaw Gateway Monitor - 网关状态自动检测与重启工具

功能：
1. 检测 OpenClaw 网关进程是否存活
2. 检测网关 HTTP 端口是否响应
3. 自动重启网关（如果配置了自动重启）
4. 记录监控日志

使用方法：
    python gateway_monitor.py [--auto-restart] [--interval SECONDS] [--log-file PATH]

作者：MSS-AI System
版本：1.0.0
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

class GatewayMonitor:
    """OpenClaw 网关监控器"""

    # 默认配置
    DEFAULT_HTTP_PORT = 28789
    DEFAULT_CHECK_INTERVAL = 60  # 秒
    DEFAULT_LOG_FILE = "gateway_monitor.log"

    # OpenClaw 进程名称
    PROCESS_NAMES = ["QClaw.exe", "node.exe", "openclaw.exe"]

    def __init__(self, auto_restart: bool = False, interval: int = DEFAULT_CHECK_INTERVAL,
                 log_file: Optional[str] = None, http_port: int = DEFAULT_HTTP_PORT):
        self.auto_restart = auto_restart
        self.interval = interval
        self.http_port = http_port
        self.log_file = log_file or self.DEFAULT_LOG_FILE
        self.consecutive_failures = 0
        self.max_failures_before_restart = 3

        # 设置日志
        self._setup_logging()

        # 查找 OpenClaw CLI 路径
        self.openclaw_cli = self._find_openclaw_cli()

    def _setup_logging(self):
        """配置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('GatewayMonitor')

    def _find_openclaw_cli(self) -> Optional[str]:
        """查找 OpenClaw CLI 可执行文件"""
        # 常见路径
        possible_paths = [
            r"C:\Program Files\QClaw\resources\openclaw\config\bin\openclaw.CMD",
            r"C:\Program Files\QClaw\QClaw.exe",
            r"C:\Program Files\QClaw\resources\openclaw\config\npm-tools\node_modules\.bin\openclaw.CMD",
        ]

        # 检查 PATH 中的 openclaw
        import shutil
        path_openclaw = shutil.which('openclaw')
        if path_openclaw:
            possible_paths.insert(0, path_openclaw)

        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"找到 OpenClaw CLI: {path}")
                return path

        self.logger.warning("未找到 OpenClaw CLI，自动重启功能将不可用")
        return None

    def check_process_alive(self) -> bool:
        """检查 OpenClaw 进程是否存活"""
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq QClaw.exe'],
                capture_output=True, text=True, encoding='utf-8', errors='ignore',
                timeout=5
            )
            # 如果找到进程，输出会包含进程信息
            return 'QClaw.exe' in result.stdout and 'INFO: No tasks' not in result.stdout
        except Exception as e:
            self.logger.error(f"检查进程状态时出错: {e}")
            return False

    def check_http_port(self) -> bool:
        """检查网关 HTTP 端口是否响应"""
        try:
            # 尝试连接网关端口，接受任何HTTP响应（包括404）
            # 只要端口可连接，说明网关HTTP服务正在运行
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', self.http_port))
            sock.close()
            return result == 0  # 0 表示连接成功
        except Exception:
            return False

    def check_gateway_status(self) -> Tuple[bool, str]:
        """
        综合检查网关状态

        Returns:
            (is_healthy, status_message)
        """
        process_alive = self.check_process_alive()
        http_responsive = self.check_http_port()

        if process_alive and http_responsive:
            return True, "健康 (进程存活 + HTTP响应)"
        elif process_alive and not http_responsive:
            return False, "异常 (进程存活但HTTP无响应)"
        elif not process_alive and http_responsive:
            return False, "异常 (进程未找到但HTTP响应)"
        else:
            return False, "故障 (进程未找到 + HTTP无响应)"

    def restart_gateway(self) -> bool:
        """重启 OpenClaw 网关"""
        if not self.openclaw_cli:
            self.logger.error("无法重启：未找到 OpenClaw CLI")
            return False

        try:
            self.logger.info("正在尝试重启网关...")

            # 先尝试停止
            stop_result = subprocess.run(
                [self.openclaw_cli, 'gateway', 'stop'],
                capture_output=True, text=True, encoding='utf-8', errors='ignore',
                timeout=30, shell=True
            )
            self.logger.info(f"停止命令返回码: {stop_result.returncode}")

            # 等待几秒确保进程退出
            time.sleep(3)

            # 启动网关
            start_result = subprocess.run(
                [self.openclaw_cli, 'gateway', 'start'],
                capture_output=True, text=True, encoding='utf-8', errors='ignore',
                timeout=30, shell=True
            )
            self.logger.info(f"启动命令返回码: {start_result.returncode}")

            # 等待网关启动
            time.sleep(5)

            # 验证重启是否成功
            is_healthy, message = self.check_gateway_status()
            if is_healthy:
                self.logger.info(f"网关重启成功: {message}")
                return True
            else:
                self.logger.error(f"网关重启后仍不健康: {message}")
                return False

        except Exception as e:
            self.logger.error(f"重启网关时出错: {e}")
            return False

    def run_check(self) -> bool:
        """执行单次检查"""
        is_healthy, message = self.check_gateway_status()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if is_healthy:
            if self.consecutive_failures > 0:
                self.logger.info(f"[{timestamp}] 网关恢复: {message}")
            else:
                self.logger.info(f"[{timestamp}] 网关正常: {message}")
            self.consecutive_failures = 0
            return True
        else:
            self.consecutive_failures += 1
            self.logger.warning(
                f"[{timestamp}] 网关异常 ({self.consecutive_failures}/{self.max_failures_before_restart}): {message}"
            )

            # 如果连续失败达到阈值且允许自动重启
            if self.auto_restart and self.consecutive_failures >= self.max_failures_before_restart:
                self.logger.warning(f"连续失败 {self.max_failures_before_restart} 次，触发自动重启")
                restart_success = self.restart_gateway()
                if restart_success:
                    self.consecutive_failures = 0
                    return True

            return False

    def run_daemon(self):
        """作为守护进程持续运行"""
        self.logger.info("=" * 60)
        self.logger.info("OpenClaw Gateway Monitor 启动")
        self.logger.info(f"自动重启: {'启用' if self.auto_restart else '禁用'}")
        self.logger.info(f"检查间隔: {self.interval} 秒")
        self.logger.info(f"HTTP端口: {self.http_port}")
        self.logger.info(f"日志文件: {self.log_file}")
        self.logger.info("=" * 60)

        try:
            while True:
                self.run_check()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.logger.info("监控器已停止")
        except Exception as e:
            self.logger.error(f"监控器异常退出: {e}")

    def run_once(self) -> bool:
        """执行单次检查并返回结果"""
        return self.run_check()

def main():
    parser = argparse.ArgumentParser(
        description='OpenClaw Gateway Monitor - 网关状态检测与自动重启工具'
    )
    parser.add_argument(
        '--auto-restart', action='store_true',
        help='启用自动重启功能（连续3次检测失败后自动重启网关）'
    )
    parser.add_argument(
        '--interval', type=int, default=60,
        help='检查间隔（秒），默认60秒'
    )
    parser.add_argument(
        '--log-file', type=str, default='gateway_monitor.log',
        help='日志文件路径'
    )
    parser.add_argument(
        '--port', type=int, default=28789,
        help='网关HTTP端口，默认28789'
    )
    parser.add_argument(
        '--once', action='store_true',
        help='只执行一次检查，不进入守护模式'
    )

    args = parser.parse_args()

    monitor = GatewayMonitor(
        auto_restart=args.auto_restart,
        interval=args.interval,
        log_file=args.log_file,
        http_port=args.port
    )

    if args.once:
        healthy = monitor.run_once()
        sys.exit(0 if healthy else 1)
    else:
        monitor.run_daemon()

if __name__ == '__main__':
    main()
