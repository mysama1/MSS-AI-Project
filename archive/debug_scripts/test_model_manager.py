# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from mss_model_manager import MSSModelManager, get_gpu_status, list_available_models

# 测试模型管理器
manager = MSSModelManager()

print("=" * 60)
print("GPU Status:")
gpu = get_gpu_status()
print(f"  Available: {gpu['available']}")
print(f"  Total: {gpu.get('total_gb', 'N/A')}GB")
print(f"  Free: {gpu.get('free_gb', 'N/A')}GB")

print("\n" + "=" * 60)
print("Installed Models:")
models = list_available_models()
for name, params in models.items():
    print(f"  {name}: {params}")

print("\n" + "=" * 60)
print("Recommendations:")
rec = manager.get_recommendations()
print(f"  Status: {rec['status']}")
print(f"  Recommended: {rec['recommended']}")
print(f"  Reason: {rec['reason']}")

print("\n" + "=" * 60)
print("GPU Layer Calculation Tests:")
test_cases = [
    ("qwen2.5:7b", 12),
    ("qwen2.5:7b", 6),
    ("qwen2.5:14b", 12),
    ("qwen2.5:14b", 6),
]

for model, vram in test_cases:
    layers = manager.calculate_gpu_layers(model, vram)
    print(f"  {model} with {vram}GB free → {layers} GPU layers")
