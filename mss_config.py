"""
MSS-AI Configuration Management
Centralized config with environment separation and validation
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path

from mss_exceptions import SystemException, ValidationException, ErrorCode

class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "dev"
    TESTING = "test"
    PRODUCTION = "prod"

@dataclass
class ModelConfig:
    """Model configuration"""
    arbiter_model: str = "qwen2.5:7b"
    responder_model: str = "mss-ai-v1"
    fallback_model: str = "qwen2.5:7b"
    max_tokens: int = 2048
    temperature: float = 0.05
    timeout_seconds: int = 30
    max_retries: int = 3

    # GPU settings
    check_gpu: bool = True
    gpu_memory_threshold_mb: int = 4096
    offload_to_cpu: bool = False

@dataclass
class PostProcessConfig:
    """Post-processing configuration"""
    enabled: bool = True
    track_positions: bool = False
    max_text_length: int = 100000

    # Rule defaults
    default_rules_enabled: bool = True
    terminology_priority: int = 10
    assertion_priority: int = 10
    structure_priority: int = 5
    compliance_priority: int = 0
    format_priority: int = 20

@dataclass
class SymbolicEngineConfig:
    """Symbolic engine configuration"""
    max_graph_nodes: int = 10000
    max_path_depth: int = 10
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    # Inference settings
    default_confidence: float = 0.8
    min_confidence_threshold: float = 0.5
    contradiction_detection: bool = True

@dataclass
class KnowledgeBaseConfig:
    """Knowledge base configuration"""
    kb_path: str = "kb"
    auto_load: bool = True
    file_pattern: str = "*.jsonl"
    encoding: str = "utf-8"

    # Validation
    validate_on_load: bool = True
    strict_mode: bool = False
    max_entry_size: int = 10000

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    file_enabled: bool = True
    file_path: str = "logs/mss-ai.log"
    max_file_size_mb: int = 10
    max_backup_files: int = 5

    # Console
    console_enabled: bool = True
    console_encoding: str = "utf-8"

@dataclass
class SecurityConfig:
    """Security and compliance configuration"""
    content_filter_enabled: bool = True
    max_input_length: int = 50000
    forbidden_patterns: List[str] = field(default_factory=list)

    # Output constraints
    require_boundary_notes: bool = True
    require_confidence_markers: bool = True
    max_output_length: int = 100000

@dataclass
class MSSConfig:
    """Master configuration container"""
    environment: Environment = Environment.DEVELOPMENT
    version: str = "1.0.0"

    # Sub-configs
    model: ModelConfig = field(default_factory=ModelConfig)
    post_process: PostProcessConfig = field(default_factory=PostProcessConfig)
    symbolic: SymbolicEngineConfig = field(default_factory=SymbolicEngineConfig)
    knowledge_base: KnowledgeBaseConfig = field(default_factory=KnowledgeBaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # Runtime overrides
    _overrides: Dict[str, Any] = field(default_factory=dict, repr=False)

    def get(self, key: str, default=None):
        """Get config value by dot notation (e.g., 'model.arbiter_model')"""
        keys = key.split(".")
        value = self
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        """Set config value by dot notation"""
        keys = key.split(".")
        target = self
        for k in keys[:-1]:
            target = getattr(target, k)
        setattr(target, keys[-1], value)
        self._overrides[key] = value

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "environment": self.environment.value,
            "version": self.version,
            "model": asdict(self.model),
            "post_process": asdict(self.post_process),
            "symbolic": asdict(self.symbolic),
            "knowledge_base": asdict(self.knowledge_base),
            "logging": asdict(self.logging),
            "security": asdict(self.security),
            "overrides": self._overrides
        }

    def save(self, path: str):
        """Save configuration to JSON file"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "MSSConfig":
        """Load configuration from JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict) -> "MSSConfig":
        """Create config from dictionary"""
        config = cls()

        if "environment" in data:
            config.environment = Environment(data["environment"])
        if "version" in data:
            config.version = data["version"]

        # Load sub-configs
        for key, subcls in [
            ("model", ModelConfig),
            ("post_process", PostProcessConfig),
            ("symbolic", SymbolicEngineConfig),
            ("knowledge_base", KnowledgeBaseConfig),
            ("logging", LoggingConfig),
            ("security", SecurityConfig),
        ]:
            if key in data:
                subconfig = subcls(**data[key])
                setattr(config, key, subconfig)

        return config

    def validate(self) -> List[str]:
        """Validate configuration, return list of issues"""
        issues = []

        # Model validation
        if self.model.temperature < 0 or self.model.temperature > 2:
            issues.append("model.temperature must be between 0 and 2")
        if self.model.max_tokens < 1:
            issues.append("model.max_tokens must be positive")

        # Post-process validation
        if self.post_process.max_text_length < 100:
            issues.append("post_process.max_text_length too small")

        # Symbolic validation
        if self.symbolic.max_graph_nodes < 100:
            issues.append("symbolic.max_graph_nodes too small")

        # Security validation
        if self.security.max_input_length < 100:
            issues.append("security.max_input_length too small")

        return issues

# Global config instance
_config: Optional[MSSConfig] = None

def get_config() -> MSSConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config

def set_config(config: MSSConfig):
    """Set global configuration instance"""
    global _config
    _config = config

def load_config(
    env: Optional[Environment] = None,
    config_path: Optional[str] = None
) -> MSSConfig:
    """Load configuration with environment-specific overrides"""

    # Start with defaults
    config = MSSConfig()

    # Detect environment
    if env is None:
        env_str = os.environ.get("MSS_ENV", "dev").lower()
        try:
            env = Environment(env_str)
        except ValueError:
            env = Environment.DEVELOPMENT

    config.environment = env

    # Load from file if specified
    if config_path and os.path.exists(config_path):
        try:
            file_config = MSSConfig.load(config_path)
            # Merge with defaults
            config = file_config
        except Exception as e:
            raise SystemException(
                f"Failed to load config from {config_path}: {str(e)}",
                code=ErrorCode.SYSTEM_CONFIG_MISSING
            )

    # Apply environment-specific overrides
    env_overrides = _get_env_overrides(env)
    for key, value in env_overrides.items():
        config.set(key, value)

    # Validate
    issues = config.validate()
    if issues:
        raise ValidationException(
            f"Configuration validation failed: {'; '.join(issues)}",
            code=ErrorCode.VALIDATION_INPUT_EMPTY,
            details={"issues": issues}
        )

    return config

def _get_env_overrides(env: Environment) -> Dict[str, Any]:
    """Get environment-specific configuration overrides"""

    overrides = {
        Environment.DEVELOPMENT: {
            "logging.level": "DEBUG",
            "logging.console_enabled": True,
            "model.check_gpu": False,
            "post_process.track_positions": True,
        },
        Environment.TESTING: {
            "logging.level": "WARNING",
            "logging.file_enabled": False,
            "model.check_gpu": False,
            "post_process.enabled": True,
            "symbolic.cache_enabled": False,
        },
        Environment.PRODUCTION: {
            "logging.level": "INFO",
            "logging.file_enabled": True,
            "model.check_gpu": True,
            "security.content_filter_enabled": True,
            "post_process.enabled": True,
        }
    }

    return overrides.get(env, {})

# Demo
if __name__ == "__main__":
    print("=" * 60)
    print("MSS Configuration Management Demo")
    print("=" * 60)

    # 1. Default config
    print("\n1. Default Configuration:")
    config = MSSConfig()
    print(f"   Environment: {config.environment.value}")
    print(f"   Arbiter model: {config.model.arbiter_model}")
    print(f"   Temperature: {config.model.temperature}")

    # 2. Environment-specific config
    print("\n2. Development Config:")
    dev_config = load_config(Environment.DEVELOPMENT)
    print(f"   Log level: {dev_config.logging.level}")
    print(f"   GPU check: {dev_config.model.check_gpu}")

    print("\n3. Production Config:")
    prod_config = load_config(Environment.PRODUCTION)
    print(f"   Log level: {prod_config.logging.level}")
    print(f"   GPU check: {prod_config.model.check_gpu}")

    # 3. Dot notation access
    print("\n4. Dot Notation Access:")
    print(f"   model.arbiter_model = {config.get('model.arbiter_model')}")
    print(f"   post_process.enabled = {config.get('post_process.enabled')}")

    # 4. Validation
    print("\n5. Validation:")
    issues = config.validate()
    print(f"   Issues: {issues if issues else 'None'}")

    # 5. Save/Load
    print("\n6. Save & Load:")
    config.save("config_demo.json")
    loaded = MSSConfig.load("config_demo.json")
    print(f"   Saved and loaded: {loaded.version}")

    # Cleanup
    if os.path.exists("config_demo.json"):
        os.remove("config_demo.json")

    print("\n" + "=" * 60)
    print("Demo complete")
