"""
guardian — 守卫引擎入口 (re-export from guardian_engine).

GuardianEngine: 守卫字/禁止词语义保真度检测引擎
GuardianEngineLite: 轻量版守卫引擎 (跳过慢速检查)

Usage:
    from mssclaw.core.guardian import GuardianEngine
    engine = GuardianEngine()
    result = engine.scan(text)
"""
from .guardian_engine import GuardianResult, GuardianEngine, GuardianEngineLite

__all__ = ["GuardianResult", "GuardianEngine", "GuardianEngineLite"]
