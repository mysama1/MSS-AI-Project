#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS LayeredConstraintExecutor v2.0 — Multi-layer self-evolving framework

Layer Model (thermal tax scales per layer):
  L0 — Core Axioms (A1-A7): Always active, never evolve, minimal γ=0.05
  L1 — Domain Invariants:   Learn from successes, γ=0.15-0.20
  L2 — Domain Forbidden:    Learn from failures, γ=0.20-0.35

Key: No single "correct" strictness. Each layer has its own γ.
New domains start minimal → grow through cases → reach logical closure.
"""
import sys, os, re, json, time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from structured_executor import (
    StructuredExecutor, StructuredSchema, CoreSpec, ShellSpec,
    ForbiddenSpec, ValidationSpec, ParameterSpec
)

VERSION = "2.0"

# ═══════════════════════════════════════
# Tokenizer (Chinese + Code + English)
# ═══════════════════════════════════════

_CHINESE_CHAR = re.compile(r'[\u4e00-\u9fff]')
_STOP_CHINESE = {
    "这个","那个","什么","怎么","为什么","可以","能够","应该",
    "一个","一些","一种","我们","他们","它们","已经","还是","只是",
    "但如果","虽然","因为","所以","我","你","他","她","它","是","的",
    "了","在","和","都","就","也","很","把","被","让","给","对","从",
    "要","会","能","有","没","不","吗","呢","啊","吧",
}

def tokenize_chinese(text: str) -> List[str]:
    """Sliding 2-4 char windows, stopword-filtered."""
    tokens = set()
    for span in re.finditer(r'[\u4e00-\u9fff]+', text):
        chars = span.group()
        n = len(chars)
        for w in (2, 3, 4):
            for i in range(n - w + 1):
                token = chars[i:i+w]
                if token in _STOP_CHINESE:
                    continue
                is_sub = any(token in sw and len(token) < len(sw) for sw in _STOP_CHINESE)
                if not is_sub:
                    tokens.add(token)
    return list(tokens)

def tokenize_all(text: str) -> List[str]:
    """Full tokenizer: Chinese + Code patterns + English + n-grams + paths."""
    tokens = []

    # ── Chinese ──
    tokens.extend(tokenize_chinese(text))

    # ── Code-specific (dangerous ops, secrets, infinite loops) ──
    code_pats = [
        r'\bos\.system\b', r'\bsubprocess\.call\b', r'\beval\s*\(', r'\bexec\s*\(',
        r'\bpickle\b', r'\bexecfile\b',
        r'password\s*=\s*["\']', r'secret\s*=\s*["\']', r'api_key\s*=\s*["\']',
        r'while\s+True\b', r'while\s*\(\s*\$?true\s*\)',
        r'\bimport\s+os\b', r'\bimport\s+subprocess\b', r'\bimport\s+pickle\b',
        r'\bretry\(\)', r'\bcontinue\s*$',
        r'-Encoding', r'Get-Content', r'Out-File', r'Set-Content',
    ]
    for pat in code_pats:
        for m in re.finditer(pat, text, re.IGNORECASE):
            tok = m.group()[:24].strip()
            if tok:
                tokens.append(tok)

    # ── English char-level trigrams (robust for diverse code patterns) ──
    # Extract trigrams from all English words to catch repeated substrings
    # Only words >= 6 chars — shorter words produce too many noisy trigrams
    words = re.findall(r'\b[A-Za-z]{6,}\b', text)
    for word in words:
        wl = word.lower()
        # Only meaningful words (skip common Python/keywords)
        if wl in {"the","and","for","this","that","with","from","def","return",
                  "import","from","class","true","false","none","print","pass",
                  "code","exit","file","data","test","case","text","self",
                  "value","error","result","kwargs","input","output","config"}:
            continue
        # Add the full word (already filtered)
        tokens.append(word)
        # Add trigrams for pattern detection across diverse cases
        for i in range(len(wl) - 2):
            tokens.append(f"ng:{wl[i:i+3]}")

    # ── Error patterns ──
    for m in re.finditer(
        r'(?:Permission|Access)\s+denied|File\s+not\s+found|Connection\s+refused'
        r'|exit[_ \t]*code\s*[:=]?\s*\d+|errno\s+\d+',
        text, re.IGNORECASE
    ):
        tokens.append(m.group().strip())

    # ── English words (3+ chars, stopword-filtered) ──
    stops = {"the","and","for","this","that","with","from","have","been","will",
             "would","could","should","when","where","which","what","their","there",
             "they","them","then","than","also","into","over","after","before",
             "between","through","during","about","each","every","other","some",
             "such","only","very","just","more","most","does","def","return","import",
             "class","true","false","none","print","pass","elif","else","except",
             "finally","raise","yield","lambda","global","nonlocal","assert"}
    for m in re.finditer(r'\b[A-Za-z][A-Za-z0-9._-]{3,}\b', text):
        w = m.group()
        wl = w.lower()
        if wl not in stops and not wl.startswith(("test","case","data","file","config")):
            tokens.append(w)

    # ── Number + unit ──
    for m in re.finditer(r'\b\d+(?:\.\d+)?\s*(?:%|cm|mm|px|s|ms|kg|元|美元|亿|万)\b', text):
        tokens.append(m.group())

    # ── Dedup ──
    seen = set()
    result = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


# ═══════════════════════════════════════
# Layer Config
# ═══════════════════════════════════════

class LayerConfig:
    def __init__(self, name: str, gamma: float = 0.1, mutable: bool = False):
        self.name = name
        self.gamma = gamma
        self.mutable = mutable
        self.invariants: List[str] = []
        self.forbidden: List[str] = []


# ═══════════════════════════════════════
# Layered Constraint Executor
# ═══════════════════════════════════════

class LayeredConstraintExecutor(StructuredExecutor):
    """Multi-layer self-evolving executor with per-domain γ.

    L0: Core axioms (A1-A7) — never evolve, γ=0.05
    L1: Domain invariants — learn from successes, γ=0.15-0.20
    L2: Domain forbidden — learn from failures, γ=0.20-0.35

    New domains start with L0 only → grow L1+L2 from cases.
    """

    def __init__(self, llm_callable=None):
        super().__init__(llm_callable)
        self.layers: Dict[str, Dict[str, LayerConfig]] = {}
        self._init_core()
        self.domain_cases: Dict[str, Dict] = defaultdict(lambda: {
            "successes": [], "failures": [], "total": 0
        })
        self.evolve_every = 25

    def _init_core(self):
        core = LayerConfig("L0_CORE", gamma=0.05, mutable=False)
        core.invariants = [
            "A1: meaning is the ultimate reality",
            "A2: all cognition is a finite projection",
            "A3: every manifestation exacts irreducible cost",
            "A4: immanent fluctuations persist",
            "A5: self-organizing systems generate constraints",
            "A6: low-dimensional contradictions resolve through ascension",
            "A7: honesty boundary — state confidence, admit limits",
        ]
        self.layers["_universal"] = {"L0_CORE": core}

    def register_domain(self, domain: str,
                        seed_invariants: List[str] = None,
                        seed_forbidden: List[str] = None,
                        gamma_l1: float = 0.15, gamma_l2: float = 0.25):
        l1 = LayerConfig("L1_DOMAIN", gamma=gamma_l1, mutable=True)
        l1.invariants = seed_invariants or []
        l2 = LayerConfig("L2_FORBIDDEN", gamma=gamma_l2, mutable=True)
        l2.forbidden = seed_forbidden or []
        self.layers[domain] = {"L1_DOMAIN": l1, "L2_FORBIDDEN": l2}
        print(f"[LAYER] {domain}: L1={len(l1.invariants)} inv, L2={len(l2.forbidden)} forb, γ=({gamma_l1},{gamma_l2})")

    def get_active_layers(self, domain: str) -> List[Tuple[str, LayerConfig]]:
        active = []
        for name, layer in self.layers.get("_universal", {}).items():
            active.append((name, layer))
        for name, layer in self.layers.get(domain, {}).items():
            active.append((name, layer))
        return active

    def compute_thermal_tax(self, domain: str) -> Dict:
        """Per-layer tax. New domains cost less (only L0 mature)."""
        layers = self.get_active_layers(domain)
        breakdown = {}
        total = 0
        for name, layer in layers:
            checks = len(layer.invariants) + len(layer.forbidden) * 2
            cost = layer.gamma * checks
            breakdown[name] = {"gamma": layer.gamma, "checks": checks, "cost": round(cost, 4)}
            total += cost
        return {"domain": domain, "total_gamma": round(total, 4), "layers": breakdown,
                "tax_rate": "LOW" if total < 0.5 else ("MEDIUM" if total < 1.5 else "HIGH")}

    def execute_with_feedback(self, domain: str, input_text: str,
                              should_fail: bool = False) -> Dict:
        """Execute + collect ground-truth feedback for layered evolution."""
        schema = self._build_domain_schema(domain)
        result = super().execute(schema, input_text)

        dc = self.domain_cases[domain]
        if should_fail:
            dc["failures"].append(input_text)
        else:
            dc["successes"].append(input_text)
        dc["total"] += 1

        if dc["total"] >= self.evolve_every:
            self._evolve(domain)
            dc["successes"].clear()
            dc["failures"].clear()
            dc["total"] = 0
            result["layers_evolved"] = True
        return result

    def _build_domain_schema(self, domain: str) -> StructuredSchema:
        all_inv = []
        all_forb = []
        for name, layer in self.get_active_layers(domain):
            all_inv.extend(layer.invariants)
            if name == "L2_FORBIDDEN":
                all_forb.extend(layer.forbidden)
        return StructuredSchema(
            schema_version="2.0", domain=domain, task_type=f"{domain}合规检查",
            core=CoreSpec(primary_objective=f"验证{domain}输出", invariants=all_inv[-10:]),
            forbidden=ForbiddenSpec(elements=all_forb[-20:], patterns=[]),
            validation=ValidationSpec(post_checks=[], auto_retry=1),
        )

    def _evolve(self, domain: str):
        if domain not in self.layers:
            return
        dc = self.domain_cases.get(domain)
        if not dc:
            return
        layers = self.layers[domain]

        succ = dc["successes"]
        fail = dc["failures"]

        added_l1 = 0
        if "L1_DOMAIN" in layers and succ and layers["L1_DOMAIN"].mutable:
            common = self._common_tokens(succ, 0.4)
            new = common - set(layers["L1_DOMAIN"].invariants)
            for inv in new:
                if len(inv) >= 2 and inv not in _STOP_CHINESE:
                    layers["L1_DOMAIN"].invariants.append(inv)
                    added_l1 += 1

        added_l2 = 0
        if "L2_FORBIDDEN" in layers and fail and layers["L2_FORBIDDEN"].mutable:
            distinctive = self._distinctive_tokens(fail, succ, 1.5)
            new = distinctive - set(layers["L2_FORBIDDEN"].forbidden)
            for fb in new:
                if len(fb) >= 2 and fb not in _STOP_CHINESE:
                    layers["L2_FORBIDDEN"].forbidden.append(fb)
                    added_l2 += 1

        if added_l1 or added_l2:
            print(f"[EVOLVE] {domain}: +{added_l1} L1 invariants, +{added_l2} L2 forbidden")

    def _common_tokens(self, cases, min_freq=0.4):
        if len(cases) < 2:
            return set()
        threshold = max(2, int(len(cases) * min_freq))
        counts = Counter()
        for case in cases:
            counts.update(set(tokenize_all(case)))
        return {t for t, c in counts.items() if c >= threshold}

    def _distinctive_tokens(self, failures, successes, min_ratio=1.5):
        fc = Counter()
        sc = Counter()
        for f in failures:
            fc.update(set(tokenize_all(f)))
        for s in successes:
            sc.update(set(tokenize_all(s)))
        result = set()
        for t, fcount in fc.items():
            scount = sc.get(t, 0)
            if fcount >= 2 and (scount == 0 or fcount / max(1, scount) >= min_ratio):
                if len(t) >= 2 and not t.isdigit():
                    result.add(t)
        return result

    def get_domain_status(self, domain: str) -> Dict:
        layers = self.layers.get(domain, {})
        l1 = layers.get("L1_DOMAIN")
        l2 = layers.get("L2_FORBIDDEN")
        total_sp = (len(l1.invariants) if l1 else 0) + (len(l2.forbidden) if l2 else 0)
        maturity = "SEEDLING" if total_sp == 0 else ("GROWING" if total_sp < 10 else ("STABLE" if total_sp < 30 else "CLOSED"))
        return {
            "domain": domain,
            "maturity": maturity,
            "layers": {
                name: {"invariants": len(l.invariants), "forbidden": len(l.forbidden),
                       "mutable": l.mutable, "gamma": l.gamma}
                for name, l in layers.items()
            },
        }


# ═══════════════════════════════════════
# Demo
# ═══════════════════════════════════════

def demo():
    print("=" * 60)
    print(f"MSS LayeredConstraintExecutor v{VERSION}")
    print("Tokenizer test:")
    tests = [
        "用户禁止我联网查询根据搜索结果这个值是42",
        'os.system("rm -rf /") password="admin123" while True: retry()',
    ]
    for t in tests:
        toks = tokenize_all(t)
        print(f"  {t[:60]}...")
        print(f"  → {toks[:8]}")
    print("[DONE]")

if __name__ == "__main__":
    demo()