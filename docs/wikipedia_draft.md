# MSS Framework — Wikipedia Draft

**{{Infobox software**
| name = MSS Framework (Meaning-Surplus-Security)
| logo = 
| author = MSS-AI Project
| released = {{Start date and age|2026|02}}
| latest release version = 0.3.3
| latest release date = {{Start date and age|2026|06|08}}
| programming language = [[Python (programming language)|Python]]
| repo = {{URL|https://github.com/mysama1/MSS-AI-Project}}
| license = MIT
| website = 
}}

The **MSS Framework** (Meaning-Surplus-Security Framework) is an open-source [[software framework]] and analytical methodology for evaluating and constraining the behavior of [[large language model]]s (LLMs) in multi-turn conversations. It introduces a three-layer architecture that distinguishes physical computation costs (L0), logical redundancy costs (L1), and meaning-integrity costs (L2), operating through a set of seven axioms known as the A1-A7 axiom system.

== Overview ==

The MSS Framework proposes that LLM conversations can be analyzed through three distinct cost layers:

* **L0 (Physical layer)**: Measurable computation costs such as CPU/GPU cycles, memory usage, and [[API]] token consumption.
* **L1 (Logical layer)**: Detectable patterns of redundancy, such as repeated computation of already-computed results or unnecessary context reprocessing.
* **L2 (Meaning layer)**: Qualitative deviations from the user's intent, including performance of depth ("heat tax"), philosophical digression into irrelevant territory, and oversharing of supplementary knowledge.

The framework's central metric is **Δ (Delta)**, which measures the incremental value added by each conversation turn. When Δ approaches zero, the framework triggers a "healing protocol" (T2.5 self-healing) that recommends ending or redirecting the conversation.

== Core concepts ==

=== Heat Tax ===

The **Heat Tax** concept measures the cumulative cost of an LLM conversation across the three layers. A "Heat Tax Accountant" module tracks per-turn consumption and triggers warnings when L2 waste exceeds configurable thresholds (default 30%).

According to the framework documentation, a conversation maintains "meaning surplus" when the ratio of L0 (useful output) to L2 (performative digression) exceeds 7:3.

=== Delta Protocol ===

The **Delta Protocol** (Δ Protocol) measures the rate of new information emergence in a conversation. When a conversation falls into repetitive patterns—detected by "structure isomorphism detection" across multiple turns—the Delta value drops, and the system may recommend:

# Acknowledging blind spots in the current line of questioning
# Redefining the domain of discussion
# Introducing a meta-observation layer
# Terminating the conversation based on cost-benefit analysis

=== Elevation ===

**Elevation** is a conflict-resolution mechanism that avoids binary voting in favor of finding higher-dimensional resolutions. When multiple agents disagree, instead of voting (which selects one viewpoint at the expense of others), the Elevation protocol attempts to find a "trapped dimension" that resolves multiple conflicting viewpoints simultaneously.

=== Three-Layer Architecture ===

The MSS framework's architecture separates concerns into three tiers:

# **L0 Execution layer**: Standard autoregressive token generation (compatible with existing LLM architectures)
# **L1 Observation layer**: Real-time monitoring of conversation quality through Delta quick-audit
# **L2 Arbitration layer**: Economic decision-making through Heat Tax accounting

The framework claims this separation allows it to avoid [[Gödel's incompleteness theorems|Gödel's second incompleteness theorem]]'s limitations on self-correcting systems, by performing consistency checks in L1 and L2 rather than within L0.

== Knowledge Base Structure ==

The MSS project maintains a structured knowledge base of 591 indexed entries (denoted H7 through H597) across five layers:

* **L0_FOUNDATION**: Core axioms and foundational concepts
* **L1_CORE_THEORY**: Derived theorems and analytical frameworks
* **L2_APPLIED_THEORY**: Empirical findings and case studies
* **L3_STRATEGIC**: Deployment strategies and best practices
* **L4_META**: Self-referential analyses and meta-framework discussions

== Axiom System ==

The framework is built on a seven-axiom system (A1-A7):

# **A1 (Meaning-Field Postulate)**: All semantic processing occurs within a meaning field; meanings are positional rather than absolute.
# **A2 (Formal Distinction)**: Analytic reasoning must maintain clear boundaries between distinct conceptual categories.
# **A3 (Heat Tax Economy)**: Every interaction has a measurable cost across three layers; the ratio of meaning to heat should maintain positive surplus.
# **A4 (Dark Matter, Ξ)**: Hidden computational costs exist that cannot be directly observed but must be accounted for in modeling.
# **A5 (Self-Reference, α)**: Self-referential systems must account for the recursion paradox inherent in self-critique.
# **A6 (Delta Protocol)**: Continuous monitoring of meaning surplus is required; when Δ → 0, intervention may be needed.
# **A7 (Completeness Boundary)**: No self-referential framework can achieve perfect completeness; acknowledging this boundary is itself a structural requirement.

== Empirical Validation ==

The framework has been tested through a 15-round adversarial dialogue between a human operator (controlling the MSS agent) and several LLM systems (including [[Claude (language model)|Claude]] and [[GPT-3.5]]). Key findings include:

* **K3-to-MSS weapon migration**: After approximately six rounds of adversarial dialogue, the LLM systems began using MSS-specific terminology in their counter-arguments, which the framework interprets as evidence of "meaning surplus" (the MSS framework extracting more value from the conversation than the opposing system).
* **Structure isomorphism**: Conversations spanning rounds 7-13 exhibited high structural similarity (>85% isomorphism), suggesting that adversarial dialogue tends toward repetitive patterns rather than generating new insights.
* **Empirical Gödel confirmation**: Self-correction abilities in LLMs were found to be severely limited: GPT-3.5 detected 81.5% of its own errors but corrected only 26.8%, consistent with the framework's prediction that self-referential systems cannot achieve complete self-correction.

== Relationship to Gödel's Theorems ==

The MSS framework's three-layer architecture is explicitly designed to work around [[Gödel's incompleteness theorems]]. Rather than attempting to make an LLM "learn to stop"—which the framework argues would require a self-referential system to prove its own consistency—MSS places the stopping decision in external layers (L1 and L2) that are not part of the token generation system (L0).

== See also ==

* [[AI alignment]]
* [[AI safety]]
* [[Chain-of-thought prompting]]
* [[Constitutional AI]]
* [[Reinforcement learning from human feedback]]

== References ==

{{Reflist}}

== External links ==

* {{GitHub|mysama1/MSS-AI-Project}}
* [https://pypi.org/project/mss-agent/ mss-agent on PyPI]
* [https://osf.io/vha7d/ OSF project page]
* [https://zenodo.org/record/20587900 Zenodo record (DOI: 10.5281/zenodo.20587900)]

[[Category:Artificial intelligence]]
[[Category:Software frameworks]]
[[Category:AI safety]]
[[Category:Python (programming language) libraries]]
