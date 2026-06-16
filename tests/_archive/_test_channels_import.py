# -*- coding: utf-8 -*-
"""channels/ 导入验证"""
import sys
sys.path.insert(0, r"E:\AI_Workspace\MSS-AI\project")

from mssclaw.channels import Channel, NullChannel, get_channel, list_channels, register_channel
print("1. 顶层 import OK")

# 默认通道
ch = get_channel("null")
print(f"2. null: available={ch.available}, result={repr(ch.execute('test'))}")
assert isinstance(ch, NullChannel)

# fallback
ch = get_channel("nonexistent")
print(f"3. fallback: type={type(ch).__name__}")
assert isinstance(ch, NullChannel)

# openclaw
ch = get_channel("openclaw")
print(f"4. openclaw: available={ch.available}, type={type(ch).__name__}")
result = ch.execute("hello")
print(f"   execute result: {repr(result[:80]) if result else '(empty)'}")
print(f"   health: {ch.health()}")

# list
print(f"5. channels: {list_channels()}")

print("\n=== ALL CHECKS PASSED ===")
