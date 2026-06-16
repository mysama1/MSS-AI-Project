"""
Config Hot Reload - Watch config file changes and auto-reload
"""
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional, Dict

class ConfigWatcher:
    """配置文件监视器"""

    def __init__(self, config_path: str, reload_callback: Optional[Callable] = None):
        self.config_path = Path(config_path)
        self.reload_callback = reload_callback
        self._last_modified: Optional[float] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self, interval: float = 2.0):
        """开始监视"""
        if self._running:
            return

        if self.config_path.exists():
            self._last_modified = os.path.getmtime(self.config_path)

        self._running = True
        self._thread = threading.Thread(
            target=self._watch_loop,
            args=(interval,),
            daemon=True
        )
        self._thread.start()
        print(f"[ConfigWatcher] Watching {self.config_path}")

    def stop(self):
        """停止监视"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[ConfigWatcher] Stopped")

    def _watch_loop(self, interval: float):
        """监视循环"""
        while self._running:
            try:
                if self.config_path.exists():
                    current_mtime = os.path.getmtime(self.config_path)

                    with self._lock:
                        if (self._last_modified is not None and
                            current_mtime > self._last_modified):
                            print(f"[ConfigWatcher] Config changed, reloading...")
                            self._last_modified = current_mtime

                            if self.reload_callback:
                                try:
                                    self.reload_callback()
                                    print("[ConfigWatcher] Reload successful")
                                except Exception as e:
                                    print(f"[ConfigWatcher] Reload failed: {e}")
                        elif self._last_modified is None:
                            self._last_modified = current_mtime

            except Exception as e:
                print(f"[ConfigWatcher] Error: {e}")

            time.sleep(interval)

    def force_reload(self):
        """强制重新加载"""
        if self.reload_callback:
            self.reload_callback()

class HotReloadManager:
    """热重载管理器"""

    def __init__(self):
        self.watchers: Dict[str, ConfigWatcher] = {}

    def add_watcher(self, name: str, config_path: str,
                    reload_callback: Callable) -> ConfigWatcher:
        """添加监视器"""
        watcher = ConfigWatcher(config_path, reload_callback)
        self.watchers[name] = watcher
        return watcher

    def start_all(self):
        """启动所有监视器"""
        for name, watcher in self.watchers.items():
            watcher.start()

    def stop_all(self):
        """停止所有监视器"""
        for watcher in self.watchers.values():
            watcher.stop()

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            name: {
                "running": watcher._running,
                "path": str(watcher.config_path)
            }
            for name, watcher in self.watchers.items()
        }

def create_watcher(config_path: str,
                   reload_callback: Optional[Callable] = None) -> ConfigWatcher:
    """工厂函数"""
    return ConfigWatcher(config_path, reload_callback)
