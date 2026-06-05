#!/usr/bin/env python3
"""KB Quality Scanner — beyond JSON validation. Metadata-level health check."""
import json, os, glob, re
from collections import Counter, defaultdict

KB_DIR = r"E:\AI_Workspace\MSS-AI\project\knowledge_base"

def scan():
    files = glob.glob(os.path.join(KB_DIR, "*.jsonl"))
    stats = {"total": 0, "valid": 0, "broken": 0, "no_id": 0, "no_title": 0,
             "no_confidence": 0, "no_tags": 0, "no_references": 0, "no_created": 0}
    confs = []
    tags_all = []
    refs_all = []
    sizes = []
    ids = set()
    broken_refs = []

    for fp in sorted(files):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
            if not line:
                stats["broken"] += 1
                continue
            d = json.loads(line)
            stats["valid"] += 1
            stats["total"] += 1

            eid = d.get("id", "")
            if not eid: stats["no_id"] += 1
            else: ids.add(eid)

            if not d.get("title", ""): stats["no_title"] += 1
            if "confidence" not in d: stats["no_confidence"] += 1
            else:
                try:
                    confs.append(float(d["confidence"]))
                except (ValueError, TypeError):
                    pass
            if not d.get("tags", []): stats["no_tags"] += 1
            else: tags_all.extend(d["tags"])
            if not d.get("references", []): stats["no_references"] += 1
            else: refs_all.extend(d["references"])
            if "created" not in d: stats["no_created"] += 1
            sizes.append(len(line))
        except (json.JSONDecodeError, UnicodeDecodeError):
            stats["broken"] += 1
            stats["total"] += 1

    # Reference validity
    for ref in refs_all:
        rid = ref.split("::")[0] if "::" in ref else ref
        if rid.startswith("H") and rid not in ids:
            broken_refs.append(rid)

    # Print report
    print(f"Total entries: {stats['total']}")
    print(f"  Valid (JSON):  {stats['valid']}")
    print(f"  Broken:        {stats['broken']}")
    print()
    print(f"Missing fields:")
    if stats['no_confidence']: print(f"  confidence: {stats['no_confidence']}")
    if stats['no_tags']: print(f"  tags:       {stats['no_tags']}")
    if stats['no_references']: print(f"  references: {stats['no_references']}")
    if stats['no_created']: print(f"  created:    {stats['no_created']}")
    if stats['no_id']: print(f"  id:         {stats['no_id']}")
    print()
    if confs:
        print(f"Confidence: min={min(confs):.2f} max={max(confs):.2f} mean={sum(confs)/len(confs):.2f} ({len(confs)} entries)")
    if sizes:
        avg = sum(sizes)/len(sizes)
        print(f"Size:       min={min(sizes)} max={max(sizes)} avg={avg:.0f} bytes")
    if tags_all:
        tc = Counter(tags_all).most_common(10)
        print(f"Top tags:   {', '.join(f'{t}({c})' for t,c in tc)}")
    if broken_refs:
        bc = Counter(broken_refs).most_common(10)
        print(f"Broken refs: {', '.join(f'{r}({c})' for r,c in bc)}")
    else:
        print("Broken refs: none")

if __name__ == '__main__':
    scan()
