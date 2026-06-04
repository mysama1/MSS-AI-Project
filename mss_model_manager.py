# -*- coding: utf-8 -*-
"""
MSS Model Manager - 模型管理器
动态切换 Ollama 模型，自动适配硬件
"""

import os
import re
import json
import subprocess
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    size: str
    parameter_count: str
    quantization: str
    vram_required_gb: float

class MSSModelManager:
    """MSS 模型管理器"""
    
    # 预定义的模型配置
    MODEL_CATALOG = {
        "qwen2.5:7b": ModelInfo(
            name="qwen2.5:7b",
            size="4.7GB",
            parameter_count="7B",
            quantization="Q4_K_M",
            vram_required_gb=4.5
        ),
        "qwen2.5:14b": ModelInfo(
            name="qwen2.5:14b",
            size="9.0GB",
            parameter_count="14B",
            quantization="Q4_K_M",
            vram_required_gb=8.5
        ),
        "mss-ai-v1": ModelInfo(
            name="mss-ai-v1",
            size="4.7GB",
            parameter_count="7B",
            quantization="Q4_K_M",
            vram_required_gb=4.5
        ),
        "llama3.1:8b": ModelInfo(
            name="llama3.1:8b",
            size="4.7GB",
            parameter_count="8B",
            quantization="Q4_K_M",
            vram_required_gb=5.0
        ),
        "phi4:14b": ModelInfo(
            name="phi4:14b",
            size="9.1GB",
            parameter_count="14B",
            quantization="Q4_K_M",
            vram_required_gb=8.5
        )
    }
    
    def __init__(self):
        self.current_model = None
        self.gpu_layers = 999  # 默认全部 GPU 卸载
        self._check_ollama()
    
    def _check_ollama(self):
        """检查 Ollama 是否安装"""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("Ollama not found. Please install Ollama first.")
        except FileNotFoundError:
            raise RuntimeError("Ollama not found. Please install Ollama first.")
    
    def list_models(self) -> Dict[str, ModelInfo]:
        """列出已安装的模型"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            
            models = {}
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[0]
                    if name in self.MODEL_CATALOG:
                        models[name] = self.MODEL_CATALOG[name]
                    else:
                        # 未知模型，估算 VRAM
                        models[name] = self._estimate_model_info(name)
            
            return models
        except Exception as e:
            print(f"Error listing models: {e}")
            return {}
    
    def _estimate_model_info(self, name: str) -> ModelInfo:
        """估算未知模型的信息"""
        # 尝试从名称提取参数数量
        param_match = re.search(r':(\d+)b', name.lower())
        if param_match:
            params = int(param_match.group(1))
            vram = params * 0.6  # 粗略估算
            return ModelInfo(
                name=name,
                size="Unknown",
                parameter_count=f"{params}B",
                quantization="Unknown",
                vram_required_gb=vram
            )
        
        return ModelInfo(
            name=name,
            size="Unknown",
            parameter_count="Unknown",
            quantization="Unknown",
            vram_required_gb=6.0  # 默认值
        )
    
    def check_gpu_memory(self) -> Dict:
        """检查 GPU 显存"""
        try:
            # 尝试使用 nvidia-smi
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total,memory.free", 
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            
            if result.returncode == 0:
                total, free = result.stdout.strip().split(',')
                total_mb = float(total.strip())
                free_mb = float(free.strip())
                
                return {
                    "available": True,
                    "total_mb": total_mb,
                    "free_mb": free_mb,
                    "total_gb": round(total_mb / 1024, 1),
                    "free_gb": round(free_mb / 1024, 1)
                }
        except FileNotFoundError:
            pass
        
        # 回退：检查环境变量
        if os.environ.get("OLLAMA_GPU_LAYERS"):
            return {
                "available": True,
                "total_mb": 12288,  # 假设 12GB
                "free_mb": 8192,
                "total_gb": 12,
                "free_gb": 8,
                "note": "Using environment variable fallback"
            }
        
        return {
            "available": False,
            "total_mb": 0,
            "free_mb": 0,
            "total_gb": 0,
            "free_gb": 0
        }
    
    def calculate_gpu_layers(self, model_name: str, 
                            free_vram_gb: float) -> int:
        """
        计算最优 GPU 层数
        
        Args:
            model_name: 模型名称
            free_vram_gb: 空闲显存 (GB)
            
        Returns:
            int: 推荐的 GPU 层数
        """
        model_info = self.MODEL_CATALOG.get(model_name)
        if not model_info:
            model_info = self._estimate_model_info(model_name)
        
        required = model_info.vram_required_gb
        
        # 显存充足：全部 GPU
        if free_vram_gb >= required * 1.2:
            return 999
        
        # 显存刚好：全部 GPU
        if free_vram_gb >= required:
            return 999
        
        # 显存不足：按比例分配
        if free_vram_gb >= required * 0.7:
            return 50  # 50% GPU
        
        if free_vram_gb >= required * 0.5:
            return 30  # 30% GPU
        
        if free_vram_gb >= required * 0.3:
            return 15  # 15% GPU
        
        # 显存严重不足：CPU 运行
        return 0
    
    def switch_model(self, model_name: str, 
                     gpu_layers: Optional[int] = None) -> bool:
        """
        切换模型
        
        Args:
            model_name: 目标模型名称
            gpu_layers: 手动指定 GPU 层数 (None=自动计算)
            
        Returns:
            bool: 是否成功
        """
        print(f"[Model Manager] Switching to {model_name}...")
        
        # 1. 检查模型是否已安装
        installed = self.list_models()
        if model_name not in installed:
            print(f"[Model Manager] Model {model_name} not found. Pulling...")
            if not self._pull_model(model_name):
                return False
        
        # 2. 检查显存
        gpu_info = self.check_gpu_memory()
        if gpu_info["available"]:
            free_gb = gpu_info["free_gb"]
            print(f"[Model Manager] GPU: {gpu_info['total_gb']}GB total, "
                  f"{free_gb}GB free")
            
            # 计算 GPU 层数
            if gpu_layers is None:
                gpu_layers = self.calculate_gpu_layers(model_name, free_gb)
            
            # 设置环境变量
            os.environ["OLLAMA_GPU_LAYERS"] = str(gpu_layers)
            print(f"[Model Manager] Set OLLAMA_GPU_LAYERS={gpu_layers}")
            
            # 显存警告
            model_info = self.MODEL_CATALOG.get(model_name)
            if model_info and free_gb < model_info.vram_required_gb:
                print(f"[WARNING] Free VRAM ({free_gb}GB) < required "
                      f"({model_info.vram_required_gb}GB). "
                      f"Performance may be degraded.")
        else:
            print("[Model Manager] No GPU detected. Using CPU.")
            os.environ["OLLAMA_GPU_LAYERS"] = "0"
        
        # 3. 预热模型
        if self._warmup_model(model_name):
            self.current_model = model_name
            self.gpu_layers = gpu_layers
            print(f"[Model Manager] Successfully switched to {model_name}")
            return True
        else:
            print(f"[Model Manager] Failed to warmup {model_name}")
            return False
    
    def _pull_model(self, model_name: str) -> bool:
        """拉取模型"""
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300  # 5分钟超时
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"[Model Manager] Pull timeout for {model_name}")
            return False
        except Exception as e:
            print(f"[Model Manager] Pull error: {e}")
            return False
    
    def _warmup_model(self, model_name: str) -> bool:
        """预热模型"""
        try:
            result = subprocess.run(
                ["ollama", "run", model_name, "Hi"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[Model Manager] Warmup error: {e}")
            return False
    
    def get_current_model(self) -> Optional[str]:
        """获取当前模型"""
        return self.current_model
    
    def get_recommendations(self) -> Dict[str, str]:
        """获取模型推荐"""
        gpu_info = self.check_gpu_memory()
        
        if not gpu_info["available"]:
            return {
                "status": "CPU only",
                "recommended": "qwen2.5:7b",
                "reason": "No GPU detected. Use 7B model for acceptable speed."
            }
        
        free_gb = gpu_info["free_gb"]
        
        if free_gb >= 10:
            return {
                "status": "High VRAM",
                "recommended": "qwen2.5:14b or phi4:14b",
                "reason": f"{free_gb}GB free VRAM supports 13-14B models."
            }
        elif free_gb >= 6:
            return {
                "status": "Medium VRAM",
                "recommended": "qwen2.5:7b or llama3.1:8b",
                "reason": f"{free_gb}GB free VRAM optimal for 7-8B models."
            }
        else:
            return {
                "status": "Low VRAM",
                "recommended": "qwen2.5:7b (CPU fallback)",
                "reason": f"Only {free_gb}GB free. 7B with partial GPU or CPU."
            }


# 便捷函数
def switch_model(model_name: str, gpu_layers: Optional[int] = None) -> bool:
    """便捷函数：切换模型"""
    manager = MSSModelManager()
    return manager.switch_model(model_name, gpu_layers)


def get_gpu_status() -> Dict:
    """便捷函数：获取 GPU 状态"""
    manager = MSSModelManager()
    return manager.check_gpu_memory()


def list_available_models() -> Dict[str, str]:
    """便捷函数：列出可用模型"""
    manager = MSSModelManager()
    models = manager.list_models()
    return {name: info.parameter_count for name, info in models.items()}


if __name__ == "__main__":
    # 测试
    manager = MSSModelManager()
    
    print("=" * 60)
    print("GPU Status:")
    gpu = manager.check_gpu_memory()
    print(f"  Available: {gpu['available']}")
    print(f"  Total: {gpu['total_gb']}GB")
    print(f"  Free: {gpu['free_gb']}GB")
    
    print("\n" + "=" * 60)
    print("Installed Models:")
    models = manager.list_models()
    for name, info in models.items():
        print(f"  {name}: {info.parameter_count} ({info.size})")
    
    print("\n" + "=" * 60)
    print("Recommendations:")
    rec = manager.get_recommendations()
    print(f"  Status: {rec['status']}")
    print(f"  Recommended: {rec['recommended']}")
    print(f"  Reason: {rec['reason']}")
