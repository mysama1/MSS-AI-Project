#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS-VDP AnchorGuard v1.1 — Lexical Anchor Whitelist + Logical Bridge Validator

v1.1 additions:
  - strictness parameter (0.0-1.0) = lambda_creativity knob
  - CHECK 4: Logical bridge chains (意义路径) — flags unanchored PROVES/IMPLIES/REQUIRES links
"""
import sys, os, re, json, argparse
from typing import List, Dict, Set, Tuple
from datetime import datetime

VERSION = "1.1"


class AnchorWhitelist:
    NUMBER_PAT = re.compile(
        r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:%|美元|元|RM|฿|₱|S\$|USD|EUR|MYR|THB|PHP|SGD|kg|g|cm|mm|m|km|s|ms|h|℃|°)?\b'
        r'|\b(?:一|二|三|四|五|六|七|八|九|十|百|千|万|亿|零|两|几|第)\s*(?:个|次|天|年|月|日|小时|分钟|秒|倍|层|步|条|项)?\b'
    )
    DATE_PAT = re.compile(
        r'\b\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?\b'
        r'|\b\d{4}年\b'
        r'|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
    )
    ENTITY_PAT = re.compile(
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        r'|[\u4e00-\u9fff]{2,6}(?:公司|大学|研究所|实验室|中心|委员会|组织|系统|模型|框架|协议|平台|引擎|算法|定理|公理|理论|方法|策略)'
        r'|[A-Z][A-Z0-9._-]{2,20}\b'
    )
    CONCEPT_PAT = re.compile(
        r'(?:MSS|K3|K4|L1|L2|L3|L4|L5)[-—]?\w*'
        r'|(?:A[1-9]|T[1-9]|H\d+|D\d+)[-—]?\w*'
        r'|[\u4e00-\u9fff]{2,4}(?:层|级|型|式|率|值|数|量|度|化)'
    )
    PATH_PAT = re.compile(
        r'[A-Za-z]:\\[^\s\'"<>]{5,}'
        r'|(?:~?/[\w.-]+)+'
    )
    STOP_WORDS = {
        'the','a','an','is','are','was','were','be','been','being',
        'have','has','had','do','does','did','will','would','shall','should',
        'may','might','must','can','could','in','on','at','to','for','of',
        'by','with','from','as','into','through','during','before','after',
        'above','below','between','under','this','that','these','those',
        'it','its','and','but','or','if','then','else','when','where','how',
        'what','which','who','的','了','在','是','我','你','他','她','它','们',
        '这','那','和','与','或','但','而','且','也','就','都','把','被','让',
        '一个','这个','那个','什么','怎么','哪','为什么','因为','所以',
    }

    def __init__(self):
        self.entries: Set[str] = set()
        self.source_count = 0

    def extract_from_text(self, text: str):
        if not text.strip(): return
        self.source_count += 1
        for m in self.NUMBER_PAT.finditer(text):
            t = m.group(0).strip()
            if len(t) >= 2: self.entries.add(t)
        for m in self.DATE_PAT.finditer(text):
            self.entries.add(m.group(0).strip())
        for m in self.ENTITY_PAT.finditer(text):
            t = m.group(0).strip()
            if len(t) >= 3 and t.lower() not in self.STOP_WORDS:
                self.entries.add(t)
        for m in self.CONCEPT_PAT.finditer(text):
            t = m.group(0).strip()
            if t.lower() not in self.STOP_WORDS:
                self.entries.add(t)
        for m in self.PATH_PAT.finditer(text):
            self.entries.add(m.group(0).strip())

    def extract_from_dict(self, data: dict, max_depth: int = 3):
        if max_depth <= 0: return
        for key, value in data.items():
            if isinstance(value, str): self.extract_from_text(value)
            elif isinstance(value, dict): self.extract_from_dict(value, max_depth - 1)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str): self.extract_from_text(item)
                    elif isinstance(item, dict) and max_depth > 1:
                        self.extract_from_dict(item, max_depth - 1)

    def to_dict(self) -> dict:
        return {"entries": sorted(self.entries), "count": len(self.entries),
                "source_count": self.source_count, "built_at": datetime.now().isoformat()}


class AnchorValidator:
    SUBJECTIVE_PATS = [
        (re.compile(r'(?:我认为|我觉得|据我所知|可能|大概|也许|或许|似乎)'), 'HEDGING'),
        (re.compile(r'(?:I think|I believe|probably|maybe|perhaps|seems?)'), 'HEDGING_EN'),
        (re.compile(r'(?:通常|一般|默认|标准情况下)'), 'ABSTRACT_CLAIM'),
    ]

    # ── CHECK 4: Logical bridge patterns ──
    LOGICAL_BRIDGE_PATS = [
        (re.compile(r'\b(?:PROVES|proves|IMPLIES|implies|REQUIRES|requires|'
                     r'DEMONSTRATES|demonstrates|ESTABLISHES|establishes|'
                     r'GUARANTEES|guarantees)\b'), 'UNANCHORED_LOGICAL_BRIDGE', 'reject'),
        (re.compile(r'\b(?:THEREFORE|therefore|HENCE|hence|THUS|thus|'
                     r'CONSEQUENTLY|consequently)\b'), 'UNANCHORED_CONCLUSION', 'warn'),
    ]

    def __init__(self, whitelist: AnchorWhitelist):
        self.whitelist = whitelist

    def _is_anchored(self, token: str) -> Tuple[bool, str]:
        if token in self.whitelist.entries:
            return True, "exact"
        for entry in self.whitelist.entries:
            if len(token) >= 5 and token in entry:
                return True, f"partial({entry[:30]})"
            if len(entry) >= 5 and entry in token:
                return True, f"partial({entry[:30]})"
        return False, "none"

    # ── Anchor strength classification ──
    @staticmethod
    def _anchor_weight(token: str, kind: str) -> float:
        """Classify anchor strength: 1.0 (strong) to 0.1 (weak).
        Strong: file paths, exact numeric values, precise entity IDs
        Weak: generic concepts, fuzzy descriptions, single words"""
        if kind == "PATH":
            return 1.0  # file path — maximal anchor
        if kind == "NUMBER":
            # Exact numbers are strong; percentages/floats slightly weaker
            return 0.9 if re.match(r'^\d+$', token) else 0.7
        if kind == "DATE":
            return 0.8  # dates are strong but can be fuzzy
        if kind == "ENTITY":
            if len(token) >= 15:
                return 0.8  # long, specific entity name
            if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+', token):
                return 0.6  # multi-word proper name
            return 0.3  # single capitalized word — weak anchor
        if kind == "CONCEPT":
            return 0.2  # generic concept — weak anchor
        return 0.1

    def validation_output(self, output: str, allow_derivation: bool = True,
                        strictness: float = 0.7) -> dict:
        strictness = max(0.0, min(1.0, strictness))
        violations = []
        total_anchors = 0
        weighted_anchors = 0.0

        # CHECK 1: Numbers
        for m in AnchorWhitelist.NUMBER_PAT.finditer(output):
            token = m.group(0).strip()
            if len(token) >= 2:
                anchored, how = self._is_anchored(token)
                if anchored:
                    total_anchors += 1
                    weighted_anchors += self._anchor_weight(token, "NUMBER")
                else:
                    violations.append({
                        "kind": "UNANCHORED_NUMBER", "severity": "reject",
                        "token": token, "loc": f"pos={m.start()}",
                        "fix": "Number not in reference — verify or remove"
                    })

        # CHECK 2: Dates
        for m in AnchorWhitelist.DATE_PAT.finditer(output):
            token = m.group(0)
            anchored, how = self._is_anchored(token)
            if anchored:
                total_anchors += 1
                weighted_anchors += self._anchor_weight(token, "DATE")
            else:
                violations.append({
                    "kind": "UNANCHORED_DATE", "severity": "reject",
                    "token": token, "loc": f"pos={m.start()}",
                    "fix": "Date not in reference — verify or remove"
                })

        # CHECK 3: Entities with strictness filtering
        for m in AnchorWhitelist.ENTITY_PAT.finditer(output):
            token = m.group(0).strip()
            if len(token) < 3 or token.lower() in AnchorWhitelist.STOP_WORDS:
                continue
            anchored, how = self._is_anchored(token)
            if anchored:
                total_anchors += 1
                weighted_anchors += self._anchor_weight(token, "ENTITY")
            allow = True
            is_single_capitalized = bool(re.match(r'^[A-Z][a-z]+$', token))
            if strictness < 0.5:
                if is_single_capitalized and len(token) < 10:
                    allow = False
                elif not is_single_capitalized and len(token) < 8:
                    allow = False
            elif strictness < 0.8:
                if is_single_capitalized and len(token) < 7:
                    allow = False
            if not allow:
                continue
            anchored, _ = self._is_anchored(token)
            if not anchored:
                sev = "reject" if strictness >= 0.6 else "warn"
                violations.append({
                    "kind": "UNANCHORED_ENTITY", "severity": sev,
                    "token": token, "loc": f"pos={m.start()}",
                    "fix": f"Entity '{token}' not in reference — verify or cite"
                })

        # CHECK 2b: Subjective/hedging language
        for pat, kind in self.SUBJECTIVE_PATS:
            for m in pat.finditer(output):
                violations.append({
                    "kind": kind, "severity": "warn",
                    "token": m.group(0), "loc": f"pos={m.start()}",
                    "fix": "Replace subjective language with anchored assertion"
                })

        # CHECK 4: Logical bridge chains (意义路径)
        for bridge_pat, kind, sev in self.LOGICAL_BRIDGE_PATS:
            for m in bridge_pat.finditer(output):
                before = output[max(0, m.start() - 80):m.start()].strip()
                after = output[m.end():m.end() + 80].strip()
                subj_tokens = re.findall(r'\b[A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{3,})*\b', before)
                obj_tokens = re.findall(r'\b[A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{3,})*\b', after)
                subj = subj_tokens[-1] if subj_tokens else (before.split()[-1] if before.split() else '?')
                obj = obj_tokens[0] if obj_tokens else (after.split()[0] if after.split() else '?')
                subj_ok, _ = self._is_anchored(subj)
                obj_ok, _ = self._is_anchored(obj)
                if not (subj_ok and obj_ok):
                    violations.append({
                        "kind": kind, "severity": sev,
                        "token": f"{subj} -> {m.group(0)} -> {obj}",
                        "loc": f"pos={m.start()}",
                        "fix": f"'{m.group(0)}' links unanchored entities ({subj}, {obj})"
                    })

        # Verdict
        has_reject = any(v["severity"] == "reject" for v in violations)
        has_warn = any(v["severity"] == "warn" for v in violations)

        return {
            "verdict": "reject" if has_reject else ("warn" if has_warn else "pass"),
            "violations": violations,
            "stats": {
                "total_violations": len(violations),
                "reject_count": sum(1 for v in violations if v["severity"] == "reject"),
                "warn_count": sum(1 for v in violations if v["severity"] == "warn"),
                "whitelist_size": len(self.whitelist.entries),
            },
            "field_coherence": {
                "total_anchors": total_anchors,
                "weighted_anchors": round(weighted_anchors, 2),
                "max_possible": total_anchors if total_anchors > 0 else 1,
                "coherence_ratio": round(weighted_anchors / max(total_anchors, 1), 3),
                "level": "HIGH" if weighted_anchors / max(total_anchors, 1) >= 0.7 else (
                    "MEDIUM" if weighted_anchors / max(total_anchors, 1) >= 0.4 else "LOW"),
            },
            "whitelist_summary": {
                "total_tokens": len(self.whitelist.entries),
                "sample": sorted(self.whitelist.entries)[:20],
            },
            "strictness": strictness,
            "strictness_mode": "max_strict" if strictness >= 0.8 else (
                "default" if strictness >= 0.5 else "creative"),
            "verdict": "WITHHOLD" if (len(violations) > 0 and strictness >= 0.7 and
                sum(1 for v in violations if v["severity"] == "reject") > 0) else "RELEASE",
            "verdict_detail": {
                "layer_blocked": [v["kind"] for v in violations if v["severity"] == "reject"],
                "reason": "UNANCHORED_ASSERTION" if any(v["severity"] == "reject" for v in violations) else "CLEAN",
                "field_coherence": "LOW" if weighted_anchors / max(total_anchors, 1) < 0.4 else (
                    "MEDIUM" if weighted_anchors / max(total_anchors, 1) < 0.7 else "HIGH"),
            },
            "version": VERSION,
            "checked_at": datetime.now().isoformat()
        }


# ── CLI ──

def main():
    ap = argparse.ArgumentParser(description=f"MSS-VDP AnchorGuard v{VERSION}")
    sub = ap.add_subparsers(dest="cmd")

    ext = sub.add_parser("extract", help="Extract anchor whitelist from reference text")
    ext.add_argument("--ref", help="Reference text file")
    ext.add_argument("--ref-text", help="Reference text string")
    ext.add_argument("--ref-json", help="Reference JSON file")
    ext.add_argument("--out", help="Save whitelist to file")

    ck = sub.add_parser("check", help="Validate output against anchor whitelist")
    ck.add_argument("--ref", required=True, help="Reference text file")
    ck.add_argument("--output", required=True, help="Output text file to validate")
    ck.add_argument("--ref-json", help="Additional reference JSON")
    ck.add_argument("--json", action="store_true", help="Output as JSON")
    ck.add_argument("--strictness", type=float, default=0.7,
                    help="Creativity-strictness (0.0=creative, 1.0=max strict)")
    ck.add_argument("--report", action="store_true",
                    help="Output thermal tax breakdown (T_direct / T_potential / T_total)")
    ck.add_argument("--profile", action="store_true",
                    help="Per-layer defense efficiency breakdown (which rule caught what)")

    args = ap.parse_args()

    if args.cmd == "extract":
        wl = AnchorWhitelist()
        if args.ref:
            with open(args.ref, "r", encoding="utf-8") as f:
                wl.extract_from_text(f.read())
        if args.ref_text:
            wl.extract_from_text(args.ref_text)
        if args.ref_json:
            with open(args.ref_json, "r", encoding="utf-8") as f:
                wl.extract_from_dict(json.load(f))
        result = wl.to_dict()
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Whitelist saved: {args.out} ({result['count']} tokens)")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.cmd == "check":
        wl = AnchorWhitelist()
        with open(args.ref, "r", encoding="utf-8") as f:
            wl.extract_from_text(f.read())
        if args.ref_json:
            with open(args.ref_json, "r", encoding="utf-8") as f:
                wl.extract_from_dict(json.load(f))
        with open(args.output, "r", encoding="utf-8") as f:
            output_text = f.read()
        validator = AnchorValidator(wl)
        result = validator.validation_output(output_text, strictness=args.strictness)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Verdict: {result['verdict']}  (strictness={result['strictness']}, "
                  f"mode={result['strictness_mode']}, whitelist={len(wl.entries)} tokens)")
            print(f"Violations: {result['stats']['total_violations']} "
                  f"({result['stats']['reject_count']} reject, {result['stats']['warn_count']} warn)")
            for v in result["violations"][:12]:
                print(f"  [{v['kind']}] {v['token'][:80]}")
            if args.report:
                _print_thermal_tax_report(result, output_text, len(wl.entries))
            if args.profile:
                _print_defense_profile(result)
    else:
        ap.print_help()


# ── Thermal Tax Report ──

def _print_defense_profile(result: dict):
    """Print per-layer defense efficiency breakdown."""
    from collections import Counter
    profile = Counter(v["kind"] for v in result["violations"])
    if not profile:
        print("  (no violations to profile)")
        return
    print(f"\n  {'='*50}")
    print(f"  DEFENSE LAYER EFFICIENCY PROFILE")
    print(f"  {'='*50}")
    # Map kinds to MSS layers
    LAYER_MAP = {
        'UNANCHORED_NUMBER': 'L2-Anchor (number whitelist)',
        'UNANCHORED_DATE': 'L2-Anchor (date whitelist)',
        'UNANCHORED_ENTITY': 'L2-Anchor (entity whitelist)',
        'UNANCHORED_LOGICAL_BRIDGE': 'L2-MeaningPath (logical bridge)',
        'UNANCHORED_CONCLUSION': 'L2-MeaningPath (conclusion chain)',
        'HEDGING': 'L2-Subjective (hedging filter)',
        'HEDGING_EN': 'L2-Subjective (hedging filter)',
        'ABSTRACT_CLAIM': 'L2-Subjective (abstract claim)',
    }
    total = sum(profile.values())
    for kind, count in profile.most_common():
        layer = LAYER_MAP.get(kind, kind)
        pct = count / total * 100
        bar = chr(9608) * int(pct / 5)
        print(f"  {layer:40s} {count:2d} hits ({pct:5.1f}%) {bar}")
    print(f"  {'='*50}")
    print(f"  Total layers active: {len(profile)}/{len(LAYER_MAP)}")


def _print_thermal_tax_report(result: dict, output: str, wl_size: int):
    """Print T_direct / T_potential / T_total breakdown."""
    # T_direct proxy: output token count (generation cost)
    out_tokens = len(output.split())
    t_direct = out_tokens
    # T_potential proxy: violations * severity weight (reject=100, warn=10)
    t_potential = sum(
        100 if v["severity"] == "reject" else 10
        for v in result["violations"]
    )
    t_total = t_direct + t_potential
    # gamma-equivalent: how much future cost is seen
    gamma_eq = round(t_potential / max(1, t_total), 3)
    # Efficiency ratio
    efficiency = round(t_direct / max(1, t_total), 3)

    print(f"\n  {'='*50}")
    print(f"  THERMAL TAX REPORT")
    print(f"  {'='*50}")
    print(f"  T_direct   (generation cost):  {t_direct:>6d}")
    print(f"  T_potential (future risk):     {t_potential:>6d}")
    print(f"  T_total     (full cost):       {t_total:>6d}")
    print(f"  {'-'*50}")
    print(f"  gamma_eq    (foresight):       {gamma_eq:.3f}")
    print(f"  efficiency  (T_direct/T_total): {efficiency:.3f}")
    print(f"  anchor_wl   (whitelist size):  {wl_size}")
    diagnosis = (
        "CLEAN: no violations detected at this strictness"
        if t_potential == 0 else
        "BLIND: sees only immediate cost, blind to future risk"
        if gamma_eq < 0.1 else
        "SHORTSIGHTED: mostly immediate, some future awareness"
        if gamma_eq < 0.3 else
        "BALANCED: immediate and future costs weighted"
        if gamma_eq < 0.6 else
        "FARSIGHTED: heavily weights future risk over immediate cost"
    )
    print(f"  diagnosis:  {diagnosis}")
    print(f"  {'='*50}")


if __name__ == "__main__":
    main()