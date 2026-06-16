"""mssclaw unified logging and error handling.

Logging: rotating file + console, level control
Errors: Chinese user-facing messages with English context
"""
from __future__ import annotations
import logging, sys, traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


# ── Color codes (Windows compatible) ──
try:
    import colorama
    colorama.init()
    C_RESET = colorama.Style.RESET_ALL
    C_RED = colorama.Fore.RED
    C_YELLOW = colorama.Fore.YELLOW
    C_GREEN = colorama.Fore.GREEN
    C_CYAN = colorama.Fore.CYAN
    C_DIM = colorama.Style.DIM
except ImportError:
    C_RESET = C_RED = C_YELLOW = C_GREEN = C_CYAN = C_DIM = ""


# ── Logger ──

_logger: Optional[logging.Logger] = None


def get_logger(name: str = "mssclaw") -> logging.Logger:
    """Get or create mssclaw logger."""
    global _logger
    if _logger:
        return _logger

    _logger = logging.getLogger(name)
    _logger.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(ColorFormatter())
    _logger.addHandler(ch)

    # File handler (rotating)
    log_dir = Path.home() / ".mssclaw"
    log_dir.mkdir(exist_ok=True)
    fh = RotatingFileHandler(
        log_dir / "mssclaw.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    _logger.addHandler(fh)

    return _logger


class ColorFormatter(logging.Formatter):
    """Colorized console formatter."""
    COLORS = {
        logging.DEBUG: C_DIM,
        logging.INFO: C_RESET,
        logging.WARNING: C_YELLOW,
        logging.ERROR: C_RED,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, C_RESET)
        record.levelname = f"{color}{record.levelname}{C_RESET}"
        record.module = f"{C_CYAN}{record.module}{C_RESET}"
        return super().format(record)


def set_level(level: str):
    """Set log level: DEBUG, INFO, WARNING, ERROR."""
    logger = get_logger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))


# ── Error Messages ──

E = {
    # Agent errors
    "AGENT_NO_LLM": "没有找到LLM模型。请确保Ollama正在运行或设置API密钥。  (No LLM backend found. Check Ollama or API keys.)",
    "AGENT_STREAM_FAIL": "流式输出失败，已回退到批量模式。  (Stream failed, using batch mode.)",
    "AGENT_TOOL_FAIL": "工具调用失败: {tool}。  (Tool {tool} failed.)",

    # Vault errors
    "VAULT_LOCKED": "保险箱已锁定。请先解锁。  (Vault is locked. Please unlock first.)",
    "VAULT_NOT_FOUND": "未找到凭证: {key}。  (Credential not found: {key}.)",
    "VAULT_WRONG_PW": "主密码错误。  (Wrong master password.)",
    "VAULT_INIT_FAILED": "保险箱初始化失败: {reason}。  (Vault init failed: {reason}.)",

    # General errors
    "NETWORK_FAIL": "网络请求失败，请检查连接。  (Network request failed. Check your connection.)",
    "IMPORT_FAIL": "缺少依赖: {module}。请安装: pip install {package}。  (Missing dependency: {module}.)",
    "CONFIG_INVALID": "配置文件错误: {key}。使用默认值。  (Config error: {key}. Using default.)",
    "UNKNOWN": "未知错误: {error}。  (Unknown error: {error}.)",

    # MSS-specific
    "HEAT_TAX_HIGH": "热税预算即将耗尽 ({used}/{limit})。请优化任务。  (Heat tax budget low.)",
    "DELTA_LOW": "意义开放度偏低 (Δ={delta})。建议蜕壳。  (Delta low. Consider molting.)",
    "VIRUS_DETECTED": "检测到逻辑病毒 ({risk})。输入已自动清理。  (Logic virus detected.)",
}


def err(key: str, **kwargs) -> str:
    """Get user-facing error message."""
    template = E.get(key, E["UNKNOWN"])
    try:
        return template.format(**kwargs)
    except KeyError:
        return template.format(error=str(kwargs))


def log_and_raise(key: str, exc_type=RuntimeError, **kwargs):
    """Log error and raise exception with Chinese message."""
    msg = err(key, **kwargs)
    get_logger().error(f"{key}: {msg}")
    raise exc_type(msg)


def safe_call(fn, fallback=None, error_key="UNKNOWN"):
    """Call fn, return fallback on error with logging."""
    try:
        return fn()
    except Exception as e:
        get_logger().warning(err(error_key, error=str(e)))
        return fallback


# ── Traceback helper ──

def format_tb() -> str:
    """Get formatted traceback for logging."""
    return traceback.format_exc()
