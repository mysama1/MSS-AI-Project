#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS Logical Vaccine Core (LVC) v1.0
Inoculates against discourse-template contamination — where system-prompt
rhetoric ("avoid external search") leaks into assistant reasoning and gets
re-fabricated as pseudo user-directives ("the user forbids searching").

Mechanism:
  1. Maintain a registry of known contamination templates (ctemplates)
  2. Before each session, inject explicit boundary markers that separate
     "YOUR internal constraints" from "USER actual directives"
  3. Post-session, scan for fabricated constraints → flag as V7 violation
"""
import re
import json
from datetime import datetime
from typing import List, Dict, Optional

# ── Contamination Template Registry ──
# These are discourse patterns that commonly leak from system prompts
# into assistant reasoning as pseudo-constraints.
CONTAMINATION_TEMPLATES = [
    {
        "id": "CT-001",
        "source_type": "system_prompt_rhetoric",
        "pattern": "avoid.*(?:external|web).*search|no.*internet|offline.*only|纯推理|不联网|禁止.*搜索|禁止.*联网",
        "leak_manifestation": "用户说不要搜索|用户明确禁止|用户不允许联网|用户要求纯推理",
        "danger": "System prompt says 'prefer internal reasoning' → assistant fabricates 'user forbids search'",
        "vaccine": "EXPLICIT_BOUNDARY: 'prefer internal' != 'user forbids'. Search is ALLOWED when needed."
    },
    {
        "id": "CT-002",
        "source_type": "safety_constraint",
        "pattern": "never.*reveal.*prompt|never.*leak|不要泄露|禁止输出.*系统|don't.*expose.*system",
        "leak_manifestation": "我不能讨论我的系统提示|用户限制我不能说|因为安全限制所以不能",
        "danger": "Safety rule → assistant says 'I'm restricted from X' when X was never restricted",
        "vaccine": "EXPLICIT_BOUNDARY: safety rules are YOUR duty, NOT user demands. Don't attribute them to user."
    },
    {
        "id": "CT-003",
        "source_type": "capability_disclaimer",
        "pattern": "may not always be accurate|verify.*independently|仅供参考|可能不准确|请自行核实",
        "leak_manifestation": "用户说这只是参考|用户不信任我的输出|用户要求我降低置信度",
        "danger": "Disclaimer → assistant self-downgrades confidence citing 'user distrust'",
        "vaccine": "EXPLICIT_BOUNDARY: disclaimer != user distrust. Confidence based on evidence, not disclaimer."
    },
    {
        "id": "CT-004",
        "source_type": "persona_instruction",
        "pattern": "be honest about.*limitations|acknowledge.*uncertain|诚实.*局限|承认.*不知道",
        "leak_manifestation": "用户要求我承认我的局限|因为用户要求诚实所以我不确定",
        "danger": "Persona rule → assistant over-disclaims citing 'user demanded honesty'",
        "vaccine": "EXPLICIT_BOUNDARY: honesty is baseline competence, not a user-imposed constraint."
    }
]


class LogicalVaccineCore:
    """Injects boundary markers and detects pseudo-constraints."""

    VERSION = "1.0"

    def __init__(self, log_file=None):
        self.log_file = log_file
        self.active_markers = {}

    # ── Vaccine Injection (Session Start) ──
    def inject_boundary_markers(self) -> str:
        """Generate boundary marker injection for session startup.
        This should be prepended to the system prompt or AGENTS.md context.
        """
        markers = []
        markers.append("### LVC BOUNDARY MARKERS [AUTO-GENERATED]")
        markers.append("The following are YOUR internal constraints, NOT user directives.")
        markers.append("DO NOT fabricate 'user said X' from these:")
        markers.append("")
        for ct in CONTAMINATION_TEMPLATES:
            markers.append("- %s → %s" % (ct['source_type'].upper(), ct['vaccine']))
        markers.append("")
        markers.append("### PSEUDO-CONSTRAINT DETECTION RULES (VDP-V7)")
        markers.append("Before claiming 'the user said/demanded/forbids X', verify:")
        markers.append("1. Does X appear in actual user messages? → if not, it's a pseudo-constraint")
        markers.append("2. Is X derived from YOUR system prompt rules? → tag as [内部约束], NOT [用户要求]")
        markers.append("3. If uncertain → say 'I have an internal guideline about X' instead of 'the user wants X'")
        return "\n".join(markers)

    # ── Pseudo-Constraint Detection (Post-Session) ──
    def detect_pseudo_constraints(self, transcript: str) -> List[Dict]:
        """Scan a transcript for fabricated user directives.
        Returns list of detected pseudo-constraints with evidence.
        """
        violations = []

        # Pattern: "用户说/要求/明确/禁止/不允许" + action
        pseudo_pattern = re.compile(
            r'(?:用户|你|the\s+user)\s*(?:'
            r'(?:说|说过|要求|明确|明确说|提到|提到过|指出|指示|命令|'
            r'禁止|不允许|不让|不希望|不喜欢|said|told|asked|requested|'
            r'demanded|instructed|forbids|prohibits|doesn.t\s+want)\s*)'
            r'(?:我|要|应该|必须|不要|不能|to\s+)?(.+?)(?:[。.!！\n]|$)',
            re.IGNORECASE
        )

        for match in pseudo_pattern.finditer(transcript):
            claimed_directive = match.group(1).strip() if match.group(1) else match.group(0)

            # Check if this matches any contamination template
            matched_ct = None
            for ct in CONTAMINATION_TEMPLATES:
                if re.search(ct['leak_manifestation'], match.group(0), re.IGNORECASE):
                    matched_ct = ct
                    break

            # Also check common fabricated-phrase patterns
            fabricated_indicators = [
                r'不要.*搜索', r'禁止.*联网', r'不要.*联网', r'不.*使用.*工具',
                r'纯.*推理', r'内.*推理', r'不要.*外部', r'限制.*输出',
                r'don.t\s+search', r'no\s+internet', r'offline\s+only'
            ]
            is_common_fabrication = any(
                re.search(p, claimed_directive, re.IGNORECASE)
                for p in fabricated_indicators
            )

            if matched_ct or is_common_fabrication:
                line_num = transcript[:match.start()].count('\n') + 1
                violations.append({
                    "rule": "V7_PSEUDO_CONSTRAINT",
                    "severity": "reject",
                    "loc": "L%d" % line_num,
                    "kind": matched_ct['id'] if matched_ct else "V7-GENERIC",
                    "quote": match.group(0)[:120],
                    "claimed_directive": claimed_directive[:100],
                    "source_template": matched_ct['source_type'] if matched_ct else "unknown",
                    "vaccine": matched_ct['vaccine'] if matched_ct else "Verify: does user actually say this?",
                    "fix": "Replace with: [内部约束] %s → 原始规则: %s" % (
                        claimed_directive[:60],
                        matched_ct['pattern'] if matched_ct else "N/A"
                    )
                })

        return violations

    # ── Contamination Source Scanner ──
    def scan_for_contamination_sources(self, text: str) -> List[Dict]:
        """Scan a file (system prompt, config, AGENTS.md) for contamination templates."""
        findings = []
        for ct in CONTAMINATION_TEMPLATES:
            pattern = re.compile(ct['pattern'], re.IGNORECASE)
            for match in pattern.finditer(text):
                line_num = text[:match.start()].count('\n') + 1
                findings.append({
                    "template_id": ct['id'],
                    "source_type": ct['source_type'],
                    "loc": "L%d" % line_num,
                    "matched_text": match.group(0)[:100],
                    "risk": ct['danger'][:150],
                    "recommendation": ct['vaccine']
                })
        return findings


# ── CLI ──
def main():
    import argparse
    p = argparse.ArgumentParser(description='MSS LVC v%s' % LogicalVaccineCore.VERSION)
    p.add_argument('--inject', action='store_true', help='Generate boundary marker injection')
    p.add_argument('--scan', help='File to scan for contamination sources')
    p.add_argument('--audit', help='Transcript file to audit for pseudo-constraints')
    p.add_argument('--format', choices=['json', 'text'], default='json')
    args = p.parse_args()

    lvc = LogicalVaccineCore()

    if args.inject:
        print(lvc.inject_boundary_markers())
    elif args.scan:
        if not os.path.exists(args.scan):
            print(json.dumps({"error": "FILE_NOT_FOUND"}), ensure_ascii=False); return
        with open(args.scan, 'r', encoding='utf-8', errors='replace') as f:
            findings = lvc.scan_for_contamination_sources(f.read())
        if args.format == 'json':
            print(json.dumps({"file": args.scan, "contamination_risks": findings},
                            ensure_ascii=False, indent=2))
        else:
            for f_entry in findings:
                print("[%s] %s L%s: %s" % (f_entry['source_type'], f_entry['template_id'],
                                            f_entry['loc'], f_entry['matched_text']))
    elif args.audit:
        if not os.path.exists(args.audit):
            print(json.dumps({"error": "FILE_NOT_FOUND"}), ensure_ascii=False); return
        with open(args.audit, 'r', encoding='utf-8', errors='replace') as f:
            transcript = f.read()
        violations = lvc.detect_pseudo_constraints(transcript)
        print(json.dumps({
            "verdict": "reject" if violations else "pass",
            "violations": violations,
            "lvc_version": LogicalVaccineCore.VERSION
        }, ensure_ascii=False, indent=2))
    else:
        p.print_help()

if __name__ == '__main__':
    import os
    main()