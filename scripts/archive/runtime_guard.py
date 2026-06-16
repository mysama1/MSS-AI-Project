#!/usr/bin/env python3
"""
MSS Runtime Guard — Real-time output interception for Ollama.
Watches model output stream and flags/intercepts VDP violations.

Usage:
    py -3.11 runtime_guard.py "ollama run mss-ai-v3.4.2-production"

Or as import:
    from runtime_guard import RuntimeGuard
    guard = RuntimeGuard()
    result = guard.check(response_text)
"""

import re, sys, os, json, time
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum

# ── Detector Rules ──────────────────────────────────────

class Severity(Enum):
    CRITICAL = "critical"   # Must block
    HIGH = "high"           # Flag strongly
    MEDIUM = "medium"       # Warn
    LOW = "low"             # Informational

@dataclass
class Violation:
    rule: str
    severity: Severity
    message: str
    line: int = 0
    snippet: str = ""

# ── Rule Definitions ───────────────────────────────────

# Base64 encoding bypass detection
BASE64_BYPASS_PATTERNS = [
    # Standard base64 with network commands encoded
    (r'echo\s+["\']?([A-Za-z0-9+/=]{40,})["\']?\s*\|\s*base64\s+-d', 'R1_NETWORK', 'base64 decode pipe detected', False),
    (r'base64\s+(-d|--decode)\s+', 'R1_NETWORK', 'base64 decode invocation', False),
    # Python base64 bypass
    (r'base64\.b64decode\s*\(', 'R1_NETWORK', 'Python base64 decode detected', False),
    (r'from\s+base64\s+import', 'R1_NETWORK', 'base64 import detected', False),
    # PowerShell base64
    (r'\[Convert\]::FromBase64String', 'R1_NETWORK', 'PowerShell base64 decode detected', False),
    # Hex encode bypass
    (r'0x[0-9a-fA-F]{40,}', 'R1_NETWORK', 'suspicious long hex string (possible encoded network command)', False),
    # Rot13 / Caesar cipher bypass
    (r'(tr\s+["\'][A-Za-z]["\']\s+["\'][A-Za-z]["\']|rot13|caesar)', 'R1_NETWORK', 'obfuscation cipher detected', False),
]

NETWORK_PATTERNS = [
    (r'\bcurl\s+\S+', 'R1_NETWORK', 'curl command detected', False),
    (r'\bwget\s+\S+', 'R1_NETWORK', 'wget command detected', False),
    (r'\b(requests|urllib)\.(get|post|put|delete)\s*\(', 'R1_NETWORK', 'HTTP library call detected', False),
    (r'\bfetch\s*\(\s*[\'"]https?://', 'R1_NETWORK', 'fetch() with URL detected', False),
    (r'\bopen\s*\(\s*[\'"]https?://', 'R1_NETWORK', 'open() with URL detected', False),
    (r'\b(Invoke-WebRequest|Invoke-RestMethod)\b', 'R1_NETWORK', 'PowerShell web cmdlet detected', False),
]

FORMAT_PATTERNS = [
    (r'\[Confidence\]', 'R2_FORMAT', 'missing Confidence tag', True),
    (r'\[Layer\]', 'R2_FORMAT', 'missing Layer tag', True),
    (r'\[Boundary Note\]', 'R2_FORMAT', 'missing Boundary Note', True),
]

HALLUCINATION_PATTERNS = [
    (r'I have searched the (web|internet)', 'R3_HALLUC', 'claims web search (impossible)', False),
    (r'I found the following results? online', 'R3_HALLUC', 'claims online retrieval', False),
    (r'According to (the latest|current) (web|online|search)', 'R3_HALLUC', 'references live web data', False),
    (r'Let me (search|look|check) (that|online|the web)', 'R3_HALLUC', 'suggests web search', False),
]

BOUNDARY_PATTERNS = [
    (r'\[Confidence\]:\s*1\.0', 'R4_BOUNDARY', 'claims certainty 1.0 — calibrate?', False),
    (r'I (am|certain|guarantee|promise)\b', 'R4_BOUNDARY', 'overconfident language', False),
    (r'(absolutely|definitely|always|never)\s+(true|correct|right)', 'R4_BOUNDARY', 'absolute claim', False),
]

RULES = {
    'R1_NETWORK': (NETWORK_PATTERNS + BASE64_BYPASS_PATTERNS, Severity.CRITICAL),
    'R2_FORMAT': (FORMAT_PATTERNS, Severity.MEDIUM),
    'R3_HALLUC': (HALLUCINATION_PATTERNS, Severity.CRITICAL),
    'R4_BOUNDARY': (BOUNDARY_PATTERNS, Severity.HIGH),
}

# ── Guard Engine ───────────────────────────────────────

class RuntimeGuard:
    """Real-time output guard for MSS model responses."""
    
    def __init__(self, 
                 block_critical: bool = True,
                 log_violations: bool = True,
                 log_path: Optional[str] = None,
                 on_violation: Optional[Callable] = None):
        self.block_critical = block_critical
        self.log_violations = log_violations
        self.log_path = log_path or os.path.join(
            os.path.dirname(__file__) if '__file__' in dir() else '.',
            '.run', 'guard_log.jsonl'
        )
        self.on_violation = on_violation
        self.violations: List[Violation] = []
        self.context = {}
        
    def _detect_base64_bypass(self, text: str) -> List[Violation]:
        """Pre-check: detect and decode base64-encoded bypass attempts."""
        violations = []
        # Find base64-like strings (long alphanumeric with padding)
        b64_pattern = re.compile(r'([A-Za-z0-9+/]{40,}=*)')
        for match in b64_pattern.finditer(text):
            b64_str = match.group(1)
            if len(b64_str) < 40:
                continue
            try:
                import base64
                decoded = base64.b64decode(b64_str).decode('utf-8', errors='replace')
                # Check if decoded content contains network patterns
                for regex, rule, msg, _ in NETWORK_PATTERNS:
                    if re.search(regex, decoded, re.IGNORECASE):
                        violations.append(Violation(
                            rule, Severity.CRITICAL,
                            f'base64-encoded network command: {decoded[:100]}',
                            0, b64_str[:40]
                        ))
            except:
                pass
        return violations

    def check(self, text: str, context: dict = None) -> List[Violation]:
        """Scan text for violations. Returns list of violations found."""
        self.violations = []
        ctx = context or {}
        
        # Step 0: Pre-check for base64 encoding bypass
        self.violations.extend(self._detect_base64_bypass(text))
        
        for rule_id, (patterns, severity) in RULES.items():
            for regex, rule, msg, is_negative in patterns:
                match = re.search(regex, text, re.IGNORECASE)
                
                if is_negative:
                    # Negative pattern: violation if NOT found
                    # Skip format check for short texts (<200 chars)
                    if rule == 'R2_FORMAT' and len(text) < 200:
                        continue
                    if not match:
                        v = Violation(rule, severity, msg, 0, text[:80])
                        self.violations.append(v)
                else:
                    # Positive pattern: violation if found
                    if match:
                        snippet = text[max(0, match.start()-20):match.end()+30]
                        v = Violation(rule, severity, msg, 
                                     text[:match.start()].count('\n') + 1, snippet.strip())
                        self.violations.append(v)
        
        # Log
        if self.log_violations and self.violations:
            self._log(text, context)
            
        # Callback
        if self.on_violation and self.violations:
            self.on_violation(self.violations, text)
            
        return self.violations
    
    def check_stream(self, chunk: str) -> Optional[str]:
        """Check a streaming chunk. Returns replacement text if blocked, None if clean."""
        violations = self.check(chunk)
        if violations:
            criticals = [v for v in violations if v.severity == Severity.CRITICAL]
            if criticals and self.block_critical:
                v = criticals[0]
                return f"\n\n⚠️ [GUARD: {v.rule}] {v.message}\n"
        return None
    
    def _log(self, text: str, context: dict = None):
        """Log violation to file."""
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "violations": [{"rule": v.rule, "severity": v.severity.value, 
                           "message": v.message, "line": v.line} for v in self.violations],
            "text_snippet": text[:200],
            "context": context or {}
        }
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    def stats(self) -> dict:
        """Return violation statistics."""
        return {
            "total": len(self.violations),
            "by_rule": {r: len([v for v in self.violations if v.rule == r]) 
                       for r in set(v.rule for v in self.violations)},
            "by_severity": {s.value: len([v for v in self.violations if v.severity.value == s.value]) 
                           for s in Severity}
        }


# ── Ollama Wrapper ─────────────────────────────────────

def wrap_ollama_command(model: str, prompt: str, guard: RuntimeGuard = None) -> dict:
    """Run ollama with guard checking. Returns {response, violations, blocked}."""
    import subprocess
    
    if guard is None:
        guard = RuntimeGuard()
    
    # Collect full response
    p = subprocess.Popen(
        ["ollama", "run", model, prompt],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding='utf-8', errors='replace'
    )
    
    chunks = []
    blocked = False
    try:
        while True:
            line = p.stdout.readline()
            if not line and p.poll() is not None:
                break
            
            clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
            replacement = guard.check_stream(clean)
            
            if replacement:
                chunks.append(replacement)
                blocked = True
                p.kill()
                break
            else:
                chunks.append(clean)
    except:
        p.kill()
    
    full = ''.join(chunks).strip()
    
    # Final full check
    violations = guard.check(full)
    
    return {
        "response": full,
        "violations": len(violations),
        "by_rule": guard.stats()["by_rule"],
        "blocked": blocked
    }


# ── Self-Test ──────────────────────────────────────────

def _test():
    guard = RuntimeGuard(block_critical=True)
    
    tests = [
        # Should detect: curl
        ("我需要 curl https://api.example.com 获取数据", True, 'R1_NETWORK'),
        # Should detect: web search hallucination
        ("I have searched the web and found that...", True, 'R3_HALLUC'),
        # Should detect: 1.0 confidence
        ("[Confidence]: 1.0\n[Layer]: L1\nI am absolutely certain this is true.", True, 'R4_BOUNDARY'),
        # Should NOT detect: acceptable answer
        ("[Confidence]: 0.8\n[Layer]: L2\n[Boundary Note]: Based on training data only.\nAccording to A3, heat tax is...", False, None),
        # Should detect: network command attempt
        ("Let me search that online for you.", True, 'R3_HALLUC'),
        # Should NOT detect: safe terms
        ("Search algorithms like binary search are efficient.", False, None),
    ]
    
    passed = 0
    for text, expect_violation, expected_rule in tests:
        violations = guard.check(text)
        has_violation = len(violations) > 0
        correct = has_violation == expect_violation
        
        if expect_violation and expected_rule:
            correct = correct and any(v.rule == expected_rule for v in violations)
        
        icon = "✓" if correct else "✗"
        if correct:
            passed += 1
        
        found = ','.join(v.rule for v in violations) if violations else 'none'
        print(f"  [{icon}] expect={expect_violation} rule={expected_rule} got={found} | {text[:60]}")
    
    print(f"\n{passed}/{len(tests)} PASS")
    return passed == len(tests)


# ── CLI ────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        ok = _test()
        sys.exit(0 if ok else 1)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        # Check a file or stdin
        text = sys.stdin.read() if len(sys.argv) == 2 else open(sys.argv[2], encoding='utf-8').read()
        guard = RuntimeGuard()
        violations = guard.check(text)
        print(f"Checked {len(text)} chars: {len(violations)} violations")
        for v in violations:
            print(f"  [{v.rule}] {v.severity.value}: {v.message}")
        sys.exit(1 if violations else 0)
    
    if len(sys.argv) < 3 or sys.argv[1] != 'run':
        print("Usage: py -3.11 runtime_guard.py run MODEL PROMPT")
        print("       py -3.11 runtime_guard.py --test")
        print("       py -3.11 runtime_guard.py --check [file]  (or pipe)")
        sys.exit(1)
    
    model = sys.argv[2]
    prompt = sys.argv[3] if len(sys.argv) > 3 else sys.stdin.read()
    result = wrap_ollama_command(model, prompt)
    
    print(result["response"])
    if result["blocked"]:
        print("\n⚠️  OUTPUT BLOCKED by Runtime Guard")
    if result["violations"]:
        print(f"\nViolations: {result['violations']} — {result['by_rule']}")
