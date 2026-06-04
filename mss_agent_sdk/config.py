"""
MSS-Agent SDK 配置管理
"""
from dataclasses import dataclass, field
from typing import Optional
import os

@dataclass
class SDKConfig:
    """SDK配置"""
    # 服务端点
    api_endpoint: str = "http://localhost:11434"  # Ollama默认
    model_name: str = "mss-ai-v1"
    
    # 本地符号引擎路径
    knowledge_base_path: str = "knowledge_base"
    
    # 审计阈值
    logic_rigidity_threshold: float = 0.6  # M_L < 0.6 警告
    heat_tax_threshold: float = 0.3       # γ > 0.3 警告
    max_boundary_notes: int = 3           # 最大边界标注数
    
    # 运行模式
    local_only: bool = False              # 仅本地符号引擎，不调用远程
    fallback_to_local: bool = True        # 远程失败时回退本地
    
    # 输出控制
    auto_append_confidence: bool = True   # 自动附加置信度标记
    auto_append_layer: bool = True        # 自动附加层级标记
    auto_append_boundary: bool = True     # 自动附加边界标注
    
    # 缓存
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    
    @classmethod
    def from_env(cls) -> "SDKConfig":
        """从环境变量加载配置"""
        return cls(
            api_endpoint=os.getenv("MSS_API_ENDPOINT", "http://localhost:11434"),
            model_name=os.getenv("MSS_MODEL_NAME", "mss-ai-v1"),
            knowledge_base_path=os.getenv("MSS_KB_PATH", "knowledge_base"),
            local_only=os.getenv("MSS_LOCAL_ONLY", "false").lower() == "true",
        )
    
    def validate(self) -> bool:
        """验证配置合法性"""
        assert 0 <= self.logic_rigidity_threshold <= 1, "M_L阈值必须在[0,1]"
        assert self.heat_tax_threshold >= 0, "热税阈值必须≥0"
        return True
