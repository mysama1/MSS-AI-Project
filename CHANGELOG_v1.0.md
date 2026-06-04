# MSS-AI Changelog

## v1.0.0 (2026-05-09)

### Added
- **Three-Method API**: analyze(), generate(), switch_model()
- **Arbiter Engine**: v3.2.1 with four-layer anti-hallucination detection
- **Responder Agent**: Compliant persona v2.1 (0.938 score)
- **Model Manager**: GPU-aware dynamic switching with VRAM auto-detection
- **Skills System**: LLLM-compatible progressive loading (L1/L2/L3)
- **Dialog Fork**: Conversation branching for redteam parallel testing
- **Redteam Manager**: 5-template adversarial testing with resilience scoring
- **Post-process Filter**: Automatic forbidden term replacement
- **Integration Tests**: 4/4 pass rate

### Technical Details
- UTF-8 encoding enforced across all subprocess calls
- Support for qwen2.5:7b/14b, mss-ai-v1, llama3.1:8b, phi4:14b
- RTX 2060 12GB optimized (GPU layers auto-calculated)
- 310+ knowledge base entries (L1:119, L2:123, L3:58)

### Architecture
- Layer-based compliance (L1 hard core / L2 protective belt / L3 heuristics)
- RSCA recursive self-consistency checking
- Progressive skill loading (50-100 token catalog overhead)
- Dialog tree with fork/merge capabilities

---

## Pre-v1.0 History

See git history for detailed development timeline from v3.0 to v1.0.
