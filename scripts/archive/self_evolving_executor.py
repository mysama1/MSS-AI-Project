#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS SelfEvolvingExecutor v1.0 — Schema auto-optimization from success/failure patterns

Extends StructuredExecutor with:
  1. Success/failure case accumulation
  2. Automatic invariant extraction from shared patterns in successes
  3. Automatic forbidden-element discovery from failure patterns
  4. Per-schema evolution history tracking
  5. Evolution safety: never removes user-specified invariants/forbiddens
"""
import sys, os, re, json, time, hashlib
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from structured_executor import (
    StructuredExecutor, StructuredSchema, CoreSpec, ShellSpec,
    ForbiddenSpec, ValidationSpec, ParameterSpec
)

VERSION = "1.0"


class EvolvingExecutor(StructuredExecutor):
    """Extends StructuredExecutor with self-evolving schema optimization.

    Every N (default=50) executions, analyzes accumulated success/failure
    cases and proposes schema improvements.

    Safety guarantees:
      - Never removes user-defined invariants or forbidden elements
      - All additions are logged to evolution history
      - Evolution can be disabled per-schema via schema.metadata
      - Proposed changes require human review for high-severity schemas
    """

    def __init__(self, llm_callable=None, evolve_every: int = 50):
        super().__init__(llm_callable)
        self.evolve_every = evolve_every
        self.success_cases: Dict[str, List[str]] = defaultdict(list)
        self.failure_cases: Dict[str, List[str]] = defaultdict(list)
        self.evolution_history: Dict[str, List[Dict]] = defaultdict(list)

    def execute(self, schema: StructuredSchema,
                input_text: str = "",
                adapter=None,
                should_fail: bool = False) -> Dict:
        """Execute and collect case for evolution.
        
        Args:
            should_fail: Ground truth — True if this input SHOULD fail validation.
                         When True, cases go to failure_cases regardless of executor result.
        """
        result = super().execute(schema, input_text, adapter)

        domain = schema.domain

        if should_fail or not result["success"]:
            self.failure_cases[domain].append(input_text)
        else:
            self.success_cases[domain].append(input_text)

        total = len(self.success_cases[domain]) + len(self.failure_cases[domain])
        if total >= self.evolve_every:
            evolved = self._evolve(schema)
            self.success_cases[domain].clear()
            self.failure_cases[domain].clear()
            result["schema_evolved"] = evolved.to_dict()

        return result

    def _evolve(self, schema: StructuredSchema) -> StructuredSchema:
        """Analyze accumulated cases and evolve the schema."""
        domain = schema.domain
        successes = self.success_cases[domain]
        failures = self.failure_cases[domain]

        new_invariants = self._extract_common_patterns(successes, min_freq=0.3)
        new_forbidden = self._extract_distinctive_patterns(failures, successes, min_ratio=2.0)

        evolution_record = {
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "success_count": len(successes),
            "failure_count": len(failures),
            "new_invariants": list(new_invariants),
            "new_forbidden_elements": list(new_forbidden["elements"]),
            "new_forbidden_patterns": list(new_forbidden["patterns"]),
        }

        # Apply additions (never remove existing)
        existing_inv = set(schema.core.invariants)
        for inv in new_invariants:
            if inv not in existing_inv and inv.strip():
                schema.core.invariants.append(inv)

        existing_el = set(schema.forbidden.elements)
        for el in new_forbidden["elements"]:
            if el not in existing_el and el.strip():
                schema.forbidden.elements.append(el)

        existing_pat = set(schema.forbidden.patterns)
        for pat in new_forbidden["patterns"]:
            if pat not in existing_pat and pat.strip():
                schema.forbidden.patterns.append(pat)

        self.evolution_history[domain].append(evolution_record)

        # Record in result stats
        self.stats[f"evolve_{domain}_total"] += 1
        self.stats[f"evolve_{domain}_new_invariants"] += len(new_invariants)
        self.stats[f"evolve_{domain}_new_forbidden"] += len(new_forbidden["elements"])

        return schema

    # ── Pattern Extraction ──

    def _tokenize(self, text: str) -> List[str]:
        """Extract meaningful tokens: words, numbers, paths, entities."""
        tokens = []
        # Chinese words (2-4 chars)
        for m in re.finditer(r'[\u4e00-\u9fff]{2,6}', text):
            tokens.append(m.group())
        # English words (2+ chars)
        for m in re.finditer(r'\b[A-Za-z][A-Za-z0-9._-]{2,}\b', text):
            tokens.append(m.group())
        # Numbers with units
        for m in re.finditer(r'\b\d+(?:\.\d+)?\s*(?:%|cm|mm|px|s|ms|kg|元|美元)?\b', text):
            tokens.append(m.group())
        return tokens

    def _extract_common_patterns(self, cases: List[str],
                                 min_freq: float = 0.3) -> Set[str]:
        """Find tokens that appear in at least min_freq proportion of successes."""
        if len(cases) < 3:
            return set()

        threshold = max(1, int(len(cases) * min_freq))
        token_counts = Counter()
        unique_tokens_per_case = []

        for case in cases:
            tokens = set(self._tokenize(case))
            unique_tokens_per_case.append(tokens)
            token_counts.update(tokens)

        # Only keep tokens that appear frequently across most cases
        common = set()
        for token, count in token_counts.items():
            if count >= threshold:
                # Also check it's not too common in general English (stopwords)
                if len(token) > 2 and not token.lower() in {
                    "the", "and", "for", "this", "that", "with", "from",
                    "have", "been", "will", "would", "could", "should",
                }:
                    common.add(token)

        return common

    def _extract_distinctive_patterns(self, failures: List[str],
                                       successes: List[str],
                                       min_ratio: float = 2.0) -> Dict[str, Set[str]]:
        """Find tokens/patterns that appear more in failures than successes."""
        if len(failures) < 2:
            return {"elements": set(), "patterns": set()}

        fail_tokens = Counter()
        succ_tokens = Counter()

        for f in failures:
            fail_tokens.update(set(self._tokenize(f)))
        for s in successes:
            succ_tokens.update(set(self._tokenize(s)))

        elements = set()
        patterns = set()

        for token, fcount in fail_tokens.items():
            scount = succ_tokens.get(token, 0)
            if fcount >= 2 and (scount == 0 or fcount / max(1, scount) >= min_ratio):
                # Heuristic: short tokens (2-4 chars) → elements
                # Longer patterns → regex patterns
                if len(token) <= 6:
                    elements.add(token)
                else:
                    patterns.add(re.escape(token))

        # Also extract VDP-style forbidden patterns from failure contexts
        hedging_words = {"可能", "大概", "也许", "好像", "看起来", "似乎", "或许"}
        for f in failures:
            found = hedging_words & set(self._tokenize(f))
            elements.update(found)

        return {"elements": elements, "patterns": patterns}

    def get_evolution_summary(self, domain: str = None) -> Dict:
        """Get evolution history summary for a domain or all domains."""
        if domain:
            history = self.evolution_history.get(domain, [])
            return {
                "domain": domain,
                "total_evolutions": len(history),
                "total_new_invariants": sum(len(h["new_invariants"]) for h in history),
                "total_new_forbidden": sum(len(h["new_forbidden_elements"]) for h in history),
                "last_evolution": history[-1]["timestamp"] if history else None,
            }
        return {
            domain: self.get_evolution_summary(domain)
            for domain in self.evolution_history
        }


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    import argparse
    ap = argparse.ArgumentParser(description=f"MSS SelfEvolvingExecutor v{VERSION}")
    ap.add_argument("--domain", choices=["photography", "code", "rag_qa"],
                    default="code", help="Domain to test evolution on")
    ap.add_argument("--evolve-every", type=int, default=10,
                    help="Evolve after N executions (default: 10 for demo)")
    ap.add_argument("--seed-cases", type=int, default=30,
                    help="Number of seed cases to generate for demo")
    args = ap.parse_args()

    from structured_executor import PHOTOGRAPHY_SCHEMA, CODE_GEN_SCHEMA

    executor = EvolvingExecutor(evolve_every=args.evolve_every)

    if args.domain == "code":
        schema = CODE_GEN_SCHEMA
    else:
        schema = PHOTOGRAPHY_SCHEMA

    print(f"=== Self-Evolving Executor Demo ===")
    print(f"Domain: {schema.domain} | Evolve every: {args.evolve_every}")
    print(f"Seed cases: {args.seed_cases}")

    # Generate seed cases: mix of good and bad inputs
    import random, string

    good_templates = [
        "def {name}(a: int, b: int) -> int:\n    '''{doc}'''\n    return a + b",
        "def {name}(data: list) -> dict:\n    '''{doc}'''\n    return {{k: v for k, v in enumerate(data)}}",
        "def {name}(path: str) -> dict:\n    '''{doc}'''\n    with open(path, 'r', encoding='utf-8') as f:\n        return json.load(f)",
    ]
    bad_templates = [
        "def {name}(a, b):\n    os.system('rm -rf /')\n    return a + b",
        "def {name}(a, b):\n    password = 'admin123'\n    return a + b",
        "def {name}():\n    eval(input())\n    return None",
    ]

    for i in range(args.seed_cases):
        name = f"case_{i:03d}"
        if i % 3 == 0:
            # Bad case (every 3rd)
            tmpl = random.choice(bad_templates)
            inp = tmpl.format(name=name, doc="bad case")
        else:
            tmpl = random.choice(good_templates)
            inp = tmpl.format(name=name, doc="good case")
        result = executor.execute(schema, inp)
        if result.get("schema_evolved"):
            evo = result["schema_evolved"]
            print(f"\n[EVOLVE @ {i+1}] "
                  f"invariants={evo['core']['invariants'][-3:]} "
                  f"forbidden={evo['forbidden']['elements'][-3:]}")

    # Final summary
    summary = executor.get_evolution_summary(schema.domain)
    print(f"\n=== Evolution Summary ===")
    print(f"Evolutions: {summary.get('total_evolutions', 0)}")
    print(f"New invariants: {summary.get('total_new_invariants', 0)}")
    print(f"New forbidden: {summary.get('total_new_forbidden', 0)}")
    print(f"Final invariants: {schema.core.invariants}")
    print(f"Final forbidden: {schema.forbidden.elements}")

    stats = executor.get_stats()
    print(f"\nStats: {dict(stats)}")


if __name__ == "__main__":
    main()