# MSS-AI Project

> **Meaning-Space Structure AI Prototype**
> From philosophical framework to running reasoning system

## Status
- **Phase**: Infrastructure (Week 1)
- **Ollama**: Installing qwen2.5:7b
- **GitHub**: Pending OAuth authorization
- **IMA KB**: System config pending manual upload

## What This Is

A prototype implementation of the MSS framework as a working AI system. Unlike traditional LLMs:
- Meaning is the ontology (not language)
- Discrete graph reasoning (not continuous embeddings)
- Topological invariants define stability (not probability distributions)
- Zero alignment tax (not RLHF)

## Project Structure

```
MSS-AI-Project/
├── prompts/        # MSS prompt templates
├── memory/         # Structured memory templates
├── models/         # Ollama Modelfiles
├── scripts/        # Inference and evaluation scripts
├── docs/           # Project documentation
├── tests/          # Test cases and benchmarks
└── README.md
```

## Quick Start

```bash
# 1. Pull base model (in progress)
ollama pull qwen2.5:7b

# 2. Create MSS-AI model
ollama create mss-ai-v1 -f models/Modelfile

# 3. Run inference
ollama run mss-ai-v1
```

## Roadmap

| Week | Phase | Goal |
|------|-------|------|
| 1-2 | Infrastructure | Ollama setup, prompt tuning, reasoning validation |
| 3-6 | MVP | First working reasoning chain, knowledge base integration |
| 7-10 | Commercialization | First paying customer, API packaging |
| 11-12 | Operations | Automation, monitoring, scaling |

## Key Constraints

- Running on: i5-10400F, 32GB RAM, RTX 2060 6GB
- Target model size: 7B parameters (Q4 quantized)
- Inference speed target: 20+ tokens/sec
- No cloud dependency for core reasoning
