---
title: 'mss-agent: A Python Toolkit for Three-Layer LLM Conversation Quality Monitoring'
tags:
  - Python
  - LLM
  - AI safety
  - multi-agent
  - conversation quality
  - open source
authors:
  - name: ""
    orcid: ""
    affiliation: "Independent Researcher"
date: 18 June 2026
bibliography: paper.bib
---

# Summary

`mss-agent` is an open-source Python package that implements the Meaning-Surplus-Security (MSS) framework—a three-layer architecture for monitoring, constraining, and orchestrating large language model (LLM) conversations. The framework introduces a novel cost model that distinguishes physical computation costs (L0) from logical redundancy (L1) and meaning-integrity degradation (L2, or "heat tax"). It provides the Delta Protocol for detecting repetitive conversation patterns, HeatTax accounting for budget tracking, and multi-agent orchestration with asyncio-based parallel execution and QuorumFast convergence detection.

The package is pip-installable, supports Python 3.10+, and includes a structured knowledge base of 591 indexed entries (H7-H597) documenting the framework's theoretical foundations and empirical findings.

# Statement of Need

As LLMs are increasingly deployed in multi-turn conversational contexts—from customer support to code review to philosophical discourse—a fundamental problem emerges: autoregressive models are architecturally constrained to produce outputs for every input, but the optimal strategy is sometimes to *stop producing output*. Current LLM deployment frameworks lack mechanisms to distinguish between productive conversation turns and repetitive, performative, or waste-generating discourse.

Existing approaches such as token budgeting, rate limiting, and output length capping operate at L0 (physical layer) only. They cannot detect when a conversation has entered a self-similar loop, when an LLM is performing depth rather than producing insight, or when the cost of continuing a conversation exceeds its marginal information gain. Furthermore, self-correction training (asking an LLM to detect and correct its own errors) encounters fundamental limitations predicted by Gödel's second incompleteness theorem.

`mss-agent` addresses this gap by implementing an external monitoring architecture (L1 observation + L2 arbitration) that operates outside the autoregressive system (L0), enabling conversation-level quality decisions that the underlying LLM cannot make about itself.

# Description

`mss-agent` provides four core components:

1. **HeatTax Accountant** (`HeatTaxAccountant`): Tracks per-turn consumption across L0 (token count), L1 (redundancy detection), and L2 (performative digression). When L2 waste exceeds configurable thresholds (default 30%), it triggers warnings and can recommend conversation termination.

2. **Delta Protocol** (`DeltaQuickAudit`): Measures the rate of new information emergence per conversation turn. When structural isomorphism is detected across multiple turns (conversation falling into repetitive patterns), it recommends healing actions: acknowledge blind spots, redefine discussion domain, introduce meta-observation, or terminate.

3. **Agent Orchestrator** (`AgentOrchestrator`): Supports four execution modes—sequential, parallel, quorum, and pipeline—with v0.3.3+ providing true asyncio-based concurrent execution for parallel and quorum modes. Includes QuorumFast convergence detection that identifies consensus groups without requiring unanimous agreement.

4. **Domain-Specific Presets** (`AgentConfig`): Pre-configured parameter sets for daily, technical, philosophical, and adversarial conversation contexts, adjusting HeatTax sensitivity and Delta thresholds appropriately.

The package has been empirically validated through a 15-round adversarial dialogue experiment, which confirmed the framework's predictions about LLM self-correction limitations and weapon-migration patterns in extended conversations.

# Acknowledgements

This work was supported by the open-source community. The authors acknowledge the contributions of participants in the adversarial dialogue experiments that informed the framework's development.

# References
