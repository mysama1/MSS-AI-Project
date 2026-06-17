"""
mssclaw — Meaning Supremacy System CLI & Library.

Core package architecture:
  core/   — 133 modules: defer_guard, pipeline, scene_router, vault, etc.
  scanner/ — VDP multi-language vulnerability detection (10 languages)
  cli.py   — Unified launcher (34 commands)

  channels/ is an optional plugin layer, loaded explicitly by the caller.
"""
__version__ = "0.3.11"
