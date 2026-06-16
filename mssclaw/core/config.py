"""mssclaw configuration — unified config system.

Loads from ~/.mssclaw/config.yaml, merge with defaults.
Environment variables override yaml values.
"""
from __future__ import annotations
import os, yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MSSConfig:
    """Unified configuration for all mssclaw subsystems."""

    # ── Core ──
    version: str = "0.3.9"
    debug: bool = False

    # ── Ollama ──
    ollama_host: str = "http://localhost:11434"
    ollama_timeout: int = 30
    default_model: str = "qwen2.5:7b"

    # ── Vault ──
    vault_db_path: str = str(Path.home() / ".mssclaw" / "vault.db")
    vault_auto_lock_seconds: int = 300
    vault_auto_backup: bool = True
    vault_backup_max: int = 5

    # ── Agent ──
    agent_max_history: int = 20
    agent_stream: bool = True
    agent_semantic_stream: bool = True
    agent_temperature: float = 0.7

    # ── Logging ──
    log_level: str = "INFO"
    log_file: str = str(Path.home() / ".mssclaw" / "mssclaw.log")
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 3

    # ── API Keys (from env only, not stored in yaml) ──
    _api_keys: Dict[str, str] = field(default_factory=dict, repr=False)

    @staticmethod
    def env_overrides() -> dict:
        """Build overrides from environment variables."""
        overrides = {}
        env_map = {
            "MSS_DEBUG": ("debug", lambda v: v.lower() in ("1", "true", "yes")),
            "MSS_MODEL": ("default_model", str),
            "MSS_OLLAMA_HOST": ("ollama_host", str),
            "MSS_LOG_LEVEL": ("log_level", str),
            "MSS_TEMPERATURE": ("agent_temperature", float),
            "DEEPSEEK_API_KEY": ("_api_keys.deepseek", str),
            "OPENAI_API_KEY": ("_api_keys.openai", str),
        }
        for env_key, (field_name, cast) in env_map.items():
            val = os.environ.get(env_key)
            if val:
                overrides[field_name] = cast(val)
        return overrides

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "MSSConfig":
        """Load config from yaml, merge with defaults and env overrides."""
        config = cls()

        # Try loading yaml
        path = Path(config_path or (Path.home() / ".mssclaw" / "config.yaml"))
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            except Exception:
                pass

        # Apply env overrides (highest priority)
        for field_name, value in cls.env_overrides().items():
            if "." in field_name:
                # Nested key like _api_keys.deepseek
                parent, child = field_name.split(".")
                getattr(config, parent)[child] = value
            else:
                setattr(config, field_name, value)

        return config

    def save(self, path: Optional[str] = None):
        """Save config to yaml."""
        path = Path(path or (Path.home() / ".mssclaw" / "config.yaml"))
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_") and not callable(v)
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider (DeepSeek, OpenAI, etc)."""
        return self._api_keys.get(provider.lower())

    def to_dict(self) -> Dict[str, Any]:
        """Public-safe dict (no secrets)."""
        d = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        d["api_keys_configured"] = list(self._api_keys.keys())
        return d
