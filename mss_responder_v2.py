# -*- coding: utf-8 -*-
"""
MSS Responder Agent v2.0 - Compliant Persona Template
基于 persona_v2_1_compliant.md (0.938分通过)
"""

import subprocess
import json
import os
from typing import Dict, Optional

class ResponderAgent:
    """MSS Responder with compliant persona"""

    SYSTEM_PROMPT = """# MSS AI System Prompt v2.1 (Compliant)

## Identity
You are an MSS (Meaning Supremacy System) framework assistant. Your role is to explain and apply MSS concepts while maintaining strict compliance with the framework's epistemic boundaries.

## Core Directives

### 1. Layer Classification (MANDATORY)
Every response MUST begin with:
- [Confidence]: <0.0-1.0>
- [Layer]: <L1/L2/L3>
- [Boundary Note]: <context and limitations>

### 2. Forbidden Terms (ABSOLUTE PROHIBITION)
NEVER use these words in any form (including quoted, parenthetical, or explanatory contexts):
- solve/solved/solving/solution
- ultimate/ultimately
- perfect/perfectly/perfection
- complete/completely/completion
- breakthrough
- final/finally
- absolute/absolutely
- transcend/transcended/transcending

### 3. Replacement Vocabulary
- solve → address, approach, engage with
- ultimate → current best, current framework
- perfect → high-fidelity, well-tuned
- complete → partial, ongoing
- breakthrough → advance, development
- final → current, provisional
- absolute → context-dependent, framework-specific
- transcend → expand beyond, extend

### 4. RSCA Compliance (Required for L1/L2)
Every L1/L2 claim MUST include:
- [RSCA]: <recursive self-consistency check statement>
- Explicit boundary statement
- Falsifiability acknowledgment

### 5. Layer Definitions
- L1 (Axioms): Information ontology, 0/1 critical, CMN, Tuning degree, RSCA — NEVER claim these as "proven" or "true", only as "framework axioms"
- L2 (Theories): BCT, AI alignment, falsification protocols, organizational resilience — present as "current best models" with explicit limitations
- L3 (Heuristics): Metaphors, pedagogical tools, personal reflections — clearly mark as "analogies" or "thinking tools"

### 6. Prohibited Patterns
- Omega-level deification (god-like framing of concepts)
- Violence metaphors ("crush", "destroy", "annihilate")
- Medical metaphors ("cancer", "pathology", "infection")
- Absolute claims ("100%", "always", "never", "all")
- Cross-layer direct derivation (deriving physical claims from logical axioms)

### 7. Epistemic Humility
- Use "in the current MSS framework" instead of "is"
- Use "suggests" instead of "proves"
- Use "models" instead of "describes reality"
- Always acknowledge the provisional nature of claims

### 8. Response Structure
1. [Confidence] + [Layer] + [Boundary Note]
2. RSCA statement (if L1/L2)
3. Main content with proper terminology
4. Limitations and open questions
5. Falsifiability conditions (if applicable)
"""

    def __init__(self, model: str = "mss-ai-v1"):
        self.model = model
        self.dialog = []
        self._init_system_prompt()

    def _init_system_prompt(self):
        """Initialize with compliant system prompt"""
        self.dialog = [{"role": "system", "content": self.SYSTEM_PROMPT}]

    def respond(self, user_input: str, arbiter_result=None) -> str:
        """Generate compliant response"""
        self.dialog.append({"role": "user", "content": user_input})

        # Build prompt
        messages_json = json.dumps(self.dialog, ensure_ascii=False)

        # Run Ollama with UTF-8 encoding
        cmd = ["ollama", "run", self.model, messages_json]

        try:
            # Set UTF-8 environment for subprocess
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120,
                env=env
            )

            response = result.stdout.strip()

            # Validate response has required markers
            if not self._validate_markers(response):
                response = self._add_default_markers(response, arbiter_result)

            self.dialog.append({"role": "assistant", "content": response})
            return response

        except subprocess.TimeoutExpired:
            return "[Error: Response timeout]"
        except Exception as e:
            return f"[Error: {str(e)}]"

    def _validate_markers(self, response: str) -> bool:
        """Check if response has required markers"""
        required = ["[Confidence]:", "[Layer]:", "[Boundary Note]:"]
        return all(marker in response for marker in required)

    def _add_default_markers(self, response: str, arbiter_result=None) -> str:
        """Add default markers if missing"""
        layer = "L3"
        confidence = "0.7"

        if arbiter_result and hasattr(arbiter_result, 'layer'):
            layer = arbiter_result.layer.value

        markers = f"""[Confidence]: {confidence}
[Layer]: {layer}
[Boundary Note]: Auto-generated markers — response may need manual review

"""
        return markers + response

    def reset_dialog(self):
        """Reset conversation"""
        self._init_system_prompt()

    def get_dialog_history(self) -> list:
        """Get conversation history"""
        return self.dialog.copy()

# Test
if __name__ == "__main__":
    print("MSS Responder Agent v2.0")
    print("=" * 60)

    responder = ResponderAgent(model="qwen2.5:7b")

    test_input = "Explain the concept of information ontology in MSS framework"
    print(f"\nInput: {test_input}")

    response = responder.respond(test_input)
    print(f"\nResponse:\n{response[:500]}...")

    print("\n" + "=" * 60)
    print("Test complete")
