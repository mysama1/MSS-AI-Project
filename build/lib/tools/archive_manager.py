#!/usr/bin/env python3
"""
MSS-AI Archive Manager
Unified knowledge base archival with validation and deduplication.
Handles JSONL entries for knowledge_base/*.jsonl files.
"""

import json
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Set

KB_DIR = Path("C:/MSS-AI-Project/knowledge_base")
ARCHIVE_LOG = Path("C:/MSS-AI-Project/knowledge_base/.archive_log.jsonl")


class ArchiveManager:
    """Manages knowledge base archival with deduplication and validation."""
    
    def __init__(self, kb_dir: Optional[Path] = None):
        self.kb_dir = kb_dir or KB_DIR
        self.kb_dir.mkdir(exist_ok=True)
        self.archive_log = ARCHIVE_LOG
        self._seen_hashes: Set[str] = self._load_seen_hashes()
    
    def _load_seen_hashes(self) -> Set[str]:
        """Load hashes of previously archived entries."""
        seen = set()
        if self.archive_log.exists():
            with open(self.archive_log, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            seen.add(entry.get("hash", ""))
                        except json.JSONDecodeError:
                            pass
        return seen
    
    def _compute_hash(self, content: Dict[str, Any]) -> str:
        """Compute content hash for deduplication."""
        # Normalize: sort keys, exclude timestamp
        normalized = {k: v for k, v in sorted(content.items()) if k not in {"timestamp", "hash"}}
        content_str = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()[:16]
    
    def _validate_entry(self, entry: Dict[str, Any]) -> List[str]:
        """Validate archive entry. Returns list of errors."""
        errors = []
        
        required = ["id", "title", "layer", "content"]
        for key in required:
            if key not in entry:
                errors.append(f"Missing required field: {key}")
        
        if "layer" in entry and entry["layer"] not in {"L1", "L2", "L3", "L4"}:
            errors.append(f"Invalid layer: {entry['layer']} (must be L1/L2/L3/L4)")
        
        if "content" in entry and len(entry["content"]) < 10:
            errors.append("Content too short (min 10 chars)")
        
        return errors
    
    def archive(self, entry: Dict[str, Any], target_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Archive a single entry to knowledge base.
        
        Args:
            entry: Dictionary with id, title, layer, content, etc.
            target_file: Target JSONL filename (default: auto-detect from layer)
        
        Returns:
            Result dict with status, path, hash
        """
        # Validate
        errors = self._validate_entry(entry)
        if errors:
            return {"status": "error", "errors": errors}
        
        # Compute hash
        content_hash = self._compute_hash(entry)
        
        # Check for duplicates
        if content_hash in self._seen_hashes:
            return {"status": "duplicate", "hash": content_hash}
        
        # Determine target file
        if not target_file:
            layer = entry.get("layer", "L3")
            category = entry.get("category", "general")
            target_file = f"{category}_{layer.lower()}_archive.jsonl"
        
        target_path = self.kb_dir / target_file
        
        # Add metadata
        entry["timestamp"] = datetime.now().isoformat()
        entry["hash"] = content_hash
        
        # Append to JSONL
        with open(target_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        # Log
        log_entry = {
            "timestamp": entry["timestamp"],
            "hash": content_hash,
            "id": entry["id"],
            "target": str(target_path),
            "status": "archived"
        }
        with open(self.archive_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        self._seen_hashes.add(content_hash)
        
        return {
            "status": "success",
            "hash": content_hash,
            "path": str(target_path),
            "id": entry["id"]
        }
    
    def archive_batch(self, entries: List[Dict[str, Any]], 
                     target_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Archive multiple entries."""
        results = []
        for entry in entries:
            result = self.archive(entry, target_file)
            results.append(result)
        return results
    
    def search(self, query: str, layer: Optional[str] = None) -> List[Dict[str, Any]]:
        """Simple text search across knowledge base."""
        results = []
        query_lower = query.lower()
        
        for jsonl_file in self.kb_dir.glob("*.jsonl"):
            if jsonl_file.name.startswith('.'):
                continue
            
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        if layer and entry.get("layer") != layer:
                            continue
                        
                        # Search in title and content
                        text = f"{entry.get('title', '')} {entry.get('content', '')}".lower()
                        if query_lower in text:
                            results.append({
                                "id": entry.get("id"),
                                "title": entry.get("title"),
                                "layer": entry.get("layer"),
                                "file": jsonl_file.name,
                                "timestamp": entry.get("timestamp")
                            })
                    except json.JSONDecodeError:
                        pass
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        stats = {
            "total_files": 0,
            "total_entries": 0,
            "by_layer": {"L1": 0, "L2": 0, "L3": 0, "L4": 0},
            "total_size_mb": 0
        }
        
        for jsonl_file in self.kb_dir.glob("*.jsonl"):
            if jsonl_file.name.startswith('.'):
                continue
            
            stats["total_files"] += 1
            stats["total_size_mb"] += jsonl_file.stat().st_size / (1024 * 1024)
            
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        stats["total_entries"] += 1
                        layer = entry.get("layer", "L3")
                        if layer in stats["by_layer"]:
                            stats["by_layer"][layer] += 1
                    except json.JSONDecodeError:
                        pass
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        stats["unique_entries"] = len(self._seen_hashes)
        
        return stats


def main():
    """CLI interface for archive management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MSS-AI Archive Manager")
    parser.add_argument("action", choices=["archive", "batch", "search", "stats"])
    parser.add_argument("--file", "-f", help="JSON file with entry/entries")
    parser.add_argument("--id", help="Entry ID")
    parser.add_argument("--title", help="Entry title")
    parser.add_argument("--layer", choices=["L1", "L2", "L3", "L4"], default="L3")
    parser.add_argument("--content", help="Entry content")
    parser.add_argument("--target", help="Target JSONL file")
    parser.add_argument("--query", "-q", help="Search query")
    
    args = parser.parse_args()
    
    am = ArchiveManager()
    
    if args.action == "archive":
        if args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                entry = json.load(f)
        else:
            entry = {
                "id": args.id or f"AUTO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "title": args.title or "Untitled",
                "layer": args.layer,
                "content": args.content or ""
            }
        
        result = am.archive(entry, args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.action == "batch" and args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        
        results = am.archive_batch(entries, args.target)
        success = sum(1 for r in results if r["status"] == "success")
        duplicate = sum(1 for r in results if r["status"] == "duplicate")
        error = sum(1 for r in results if r["status"] == "error")
        
        print(f"Batch complete: {success} archived, {duplicate} duplicates, {error} errors")
    
    elif args.action == "search":
        results = am.search(args.query or "", args.layer)
        for r in results:
            print(f"[{r['layer']}] {r['id']}: {r['title']} ({r['file']})")
    
    elif args.action == "stats":
        stats = am.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
