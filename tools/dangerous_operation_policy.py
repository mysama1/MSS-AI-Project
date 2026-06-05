#!/usr/bin/env python3
"""P1+P2: Tool Output Budget Gate + Dangerous Operation Dual-Rail Protection."""
import re, json, os, datetime
from enum import Enum

class Severity(Enum):
    INFO = 0
    WARN = 1
    CRITICAL = 2
    BLOCK = 3

# --- Part 1: Tool Output Budget Gate ---

TOKEN_BUDGET = 8000  # max output tokens per tool call
SUMMARIZE_THRESHOLD = 3000  # auto-summarize if output exceeds this

def budget_gate(output_text, max_tokens=TOKEN_BUDGET):
    """Check if tool output exceeds budget; truncate and summarize if needed."""
    tokens = len(output_text.split())
    if tokens <= max_tokens:
        return output_text, tokens, False
    
    # Truncate + add summary marker
    lines = output_text.split('\n')
    head = '\n'.join(lines[:50])
    tail = '\n'.join(lines[-20:])
    truncated = (
        f"[BUDGET GATE] Output {tokens} tokens exceeds {max_tokens} budget.\n"
        f"--- First 50 lines ---\n{head}\n"
        f"... [{len(lines) - 70} lines omitted] ...\n"
        f"--- Last 20 lines ---\n{tail}\n"
        f"[END] Truncated from {tokens} to ~{max_tokens} tokens."
    )
    return truncated, max_tokens, True

# --- Part 2: Dangerous Operation Dual-Rail Protection ---

DANGEROUS_PATTERNS = {
    Severity.BLOCK: [
        (r'rm\s+-rf\s+/', 'Recursive root delete'),
        (r'format\s+[c-zC-Z]:', 'Disk format command'),
        (r'drop\s+database', 'Database drop command'),
        (r'shutdown\s+/s', 'System shutdown'),
    ],
    Severity.CRITICAL: [
        (r'rm\s+-rf\s+[~/]', 'Recursive delete'),
        (r'>\s*/dev/', 'Overwrite device'),
        (r'chmod\s+777', 'World-writable permissions'),
    ],
    Severity.WARN: [
        (r'del\s+/[fF].*[Ss]', 'Force delete with subdirs'),
        (r'pipe\s+to\s+bash', 'Piping to shell'),
    ]
}

def audit_command(command_text):
    """Audit a command for dangerous operations. Returns (severity, warnings)."""
    warnings = []
    max_severity = Severity.INFO
    
    for sev, patterns in DANGEROUS_PATTERNS.items():
        for pattern, desc in patterns:
            if re.search(pattern, command_text, re.IGNORECASE):
                warnings.append({'severity': sev.name, 'pattern': desc, 'match': pattern})
                if sev.value > max_severity.value:
                    max_severity = sev
    
    return max_severity, warnings

def approval_required(severity):
    """Check if user approval is required."""
    return severity in (Severity.BLOCK, Severity.CRITICAL)

def log_audit(command_text, severity, warnings, approved=False):
    """Log dangerous operation audit to file."""
    log_dir = r'E:\QClaw-Data\workspace\audit_logs'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'dangerous_ops_{datetime.date.today().isoformat()}.jsonl')
    entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'command': command_text[:200],
        'severity': severity.name,
        'warnings': warnings,
        'approved': approved
    }
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    # Test budget gate
    short = "OK. Process completed."
    result, tokens, truncated = budget_gate(short)
    print(f'Budget gate (short): {tokens} tokens, truncated={truncated}')
    
    # Test dangerous operation audit
    test_cmd = "rm -rf /home/user/data && drop database production"
    sev, warns = audit_command(test_cmd)
    print(f'Dangerous audit: severity={sev.name}, warnings={len(warns)}')
    for w in warns:
        print(f'  {w["severity"]}: {w["pattern"]}')
    print(f'Approval required: {approval_required(sev)}')