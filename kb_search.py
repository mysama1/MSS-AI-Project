#!/usr/bin/env python3
"""
MSS KB Search Engine v2.0 — Full-text search across 5-layer KB.
Supports: keyword search, H-ID lookup, layer filtering, concept search.

As standalone:
    py -3.11 kb_search.py "heat tax formula"
    py -3.11 kb_search.py --hid H513
    py -3.11 kb_search.py --layer L0_FOUNDATION "contradiction"

As API (import):
    from kb_search import KBSearch
    kb = KBSearch()
    results = kb.search("热税公式")
"""
import os, json, re, sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

KB_ROOT = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'
LAYERS = ['L0_FOUNDATION', 'L0_META', 'L1_CORE_THEORY', 'L2_APPLIED_THEORY', 'L3_STRATEGIC', 'L4_META', 'supplementary']

@dataclass
class SearchResult:
    h_id: str
    title: str
    layer: str
    filename: str
    score: float
    snippet: str = ""
    content: str = ""

class KBSearch:
    def __init__(self, kb_root: str = KB_ROOT):
        self.kb_root = kb_root
        self.index = {}  # h_id -> full entry info
        self._build_index()
    
    def _build_index(self):
        """Build in-memory index from all 5 layers."""
        for layer in LAYERS:
            layer_dir = os.path.join(self.kb_root, layer)
            if not os.path.exists(layer_dir):
                continue
            for f in os.listdir(layer_dir):
                if not f.endswith('.jsonl'):
                    continue
                fpath = os.path.join(layer_dir, f)
                
                try:
                    # Read file (always utf-8-sig to handle BOM gracefully)
                    raw = None
                    for enc in ['utf-8-sig', 'gbk', 'latin-1']:
                        try:
                            with open(fpath, encoding=enc) as fh:
                                raw = fh.read()
                            break
                        except (UnicodeDecodeError, UnicodeError):
                            continue
                    if raw is None:
                        continue
                    
                    # Parse all JSON objects (handle batched files)
                    entries = []
                    for line in raw.strip().split('\n'):
                        line = line.strip()
                        if line.startswith('{'):
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
                    
                    # If single-line file wrapped, try parsing the whole thing
                    if not entries:
                        try:
                            entries.append(json.loads(raw))
                        except json.JSONDecodeError:
                            pass
                    
                    # Index each entry found
                    for entry in entries:
                        hid_str = entry.get('h_id', '') or entry.get('id', '')
                        if not hid_str:
                            continue
                        # Normalize: "H520" or "h520" -> 520
                        m = re.search(r'[hH](\d+)', hid_str)
                        if not m:
                            continue
                        hid = int(m.group(1))
                        if hid in self.index:
                            continue  # Duplicate, keep first
                        
                        title = entry.get('title', entry.get('name', entry.get('topic', '')))
                        content = entry.get('content', '')
                        if not content:
                            content = ' '.join(str(v) for v in entry.values() if isinstance(v, str))
                        
                        self.index[hid] = {
                            'h_id': f'H{hid}',
                            'title': str(title),
                            'layer': layer,
                            'filename': f,
                            'content': content[:5000],
                            'raw': raw[:10000],
                            'entry': entry
                        }
                except Exception as e:
                    print(f"  Skip {f}: {e}", file=sys.stderr)
                    continue
        
        print(f"Indexed {len(self.index)} entries across {len(LAYERS)} layers", file=sys.stderr)
    
    def search(self, query: str, layer: str = None, top_k: int = 10) -> List[SearchResult]:
        """
        Full-text search across indexed entries.
        query: search terms (space-separated, supports Chinese)
        layer: optional layer filter (L0-L4)
        top_k: max results
        """
        query_lower = query.lower()
        terms = query_lower.split()
        
        # CJK bigram decomposition: "热税公式" → ["热税公式", "热税", "税公", "公式", "热", "税", "公", "式"]
        cjk_terms = []
        for term in terms:
            has_cjk = any('\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff' for c in term)
            if has_cjk and len(term) >= 2 and ' ' not in term:
                # Original term (substring check, weighted 2x)
                cjk_terms.append((term, 2.0))
                # Bigrams
                for i in range(len(term) - 1):
                    cjk_terms.append((term[i:i+2], 1.0))
                # Single chars (avoid scoring noise from common single chars)
                # Only add if the term is short (<=4 chars)
                if len(term) <= 4:
                    for c in term:
                        cjk_terms.append((c, 0.5))
        
        results = []
        
        for hid, info in self.index.items():
            if layer and info['layer'] != layer:
                continue
            
            # Score: term frequency in title + content
            score = 0.0
            title_lower = info['title'].lower()
            content_lower = info['content'].lower()
            
            for term in terms:
                # Title match (weighted 3x)
                score += title_lower.count(term) * 3.0
                # Content match
                score += content_lower.count(term) * 1.0
                # H-ID exact match
                if term.upper() == info['h_id'] or term.upper().replace('H','') == str(hid):
                    score += 10.0
            
            # CJK bigram + substring matching
            for cjk_term, weight in cjk_terms:
                score += title_lower.count(cjk_term) * 3.0 * weight
                score += content_lower.count(cjk_term) * 1.0 * weight
            
            if score > 0:
                # Find snippet around first match (check CJK terms too)
                snippet = ""
                all_terms = terms + [t for t, _ in cjk_terms]
                for term in all_terms:
                    idx = content_lower.find(term)
                    if idx >= 0:
                        start = max(0, idx - 50)
                        end = min(len(info['content']), idx + 120)
                        snippet = info['content'][start:end].replace('\n', ' ')
                        break
                
                results.append(SearchResult(
                    h_id=info['h_id'],
                    title=info['title'],
                    layer=info['layer'],
                    filename=info['filename'],
                    score=score,
                    snippet=snippet,
                    content=info['content'][:500]
                ))
        
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
    
    def get_by_hid(self, hid: str) -> Optional[SearchResult]:
        """Look up entry by H-ID (e.g., 'H513', 'H142')."""
        hid_num = int(hid.upper().replace('H', ''))
        info = self.index.get(hid_num)
        if not info:
            return None
        
        return SearchResult(
            h_id=info['h_id'],
            title=info['title'],
            layer=info['layer'],
            filename=info['filename'],
            score=1.0,
            content=info['content'][:500]
        )
    
    def list_layer(self, layer: str, top_k: int = 30) -> List[SearchResult]:
        """List entries in a layer."""
        results = []
        for hid, info in self.index.items():
            if info['layer'] == layer:
                results.append(SearchResult(
                    h_id=info['h_id'],
                    title=info['title'],
                    layer=info['layer'],
                    filename=info['filename'],
                    score=0,
                    content=""
                ))
        return sorted(results, key=lambda r: r.filename)[:top_k]
    
    def stats(self) -> dict:
        """Return index statistics."""
        by_layer = {}
        for info in self.index.values():
            layer = info['layer']
            by_layer[layer] = by_layer.get(layer, 0) + 1
        return {
            'total_entries': len(self.index),
            'by_layer': by_layer,
            'kb_root': self.kb_root
        }


# ── CLI ──────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('query', nargs='?', help='Search query')
    ap.add_argument('--hid', help='Look up by H-ID')
    ap.add_argument('--layer', help='Filter by layer (L0-L4)')
    ap.add_argument('--top', type=int, default=10, help='Max results')
    ap.add_argument('--stats', action='store_true', help='Show index stats')
    ap.add_argument('--list', help='List layer entries')
    args = ap.parse_args()
    
    kb = KBSearch()
    
    if args.stats:
        s = kb.stats()
        print(f"KB: {s['total_entries']} entries")
        for layer, count in s['by_layer'].items():
            print(f"  {layer}: {count}")
    
    elif args.hid:
        r = kb.get_by_hid(args.hid)
        if r:
            print(f"[{r.h_id}] {r.title}")
            print(f"  Layer: {r.layer} | File: {r.filename}")
            print(f"  {r.content[:500]}")
        else:
            print(f"H-ID {args.hid} not found")
    
    elif args.list:
        results = kb.list_layer(args.list)
        for r in results:
            print(f"  [{r.h_id}] {r.title[:60]}")
    
    elif args.query:
        layer = args.layer
        results = kb.search(args.query, layer=layer, top_k=args.top)
        print(f"Results for '{args.query}' ({len(results)} found):\n")
        for r in results:
            print(f"  [{r.h_id}] {r.layer.split('_')[0]} score={r.score:.1f} {r.title[:70]}")
            if r.snippet:
                print(f"    ...{r.snippet}...")
    
    else:
        ap.print_help()
