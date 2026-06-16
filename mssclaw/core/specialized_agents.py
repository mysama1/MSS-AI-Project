# -*- coding: utf-8 -*-
"""
S-007: Specialized Agents — Five plug-and-play Swarm agents

Each agent extends SwarmNode, declares capabilities, and implements
on_task_assignment() with domain-specific logic.

  KB-Agent       — knowledge base CRUD, search, gap audit, dedup
  Code-Agent     — code generation, refactoring, syntax audit
  Video-Agent    — video generation, rendering, clip detection, scene planning
  Translate-Agent— multi-language translation, cultural adaptation, term consistency
  Product-Agent  — product specs, user stories, roadmap, stakeholder alignment
  Doc-Agent      — document pipeline: .docx/.xlsx/.pdf/.pptx import/export

Design:
  - Each agent = SwarmNode subclass
  - Registers with SwarmOrchestrator
  - Uses MeetingRoom for persistent state
  - Validated by NormativeField before execution
  - Can undergo molting for self-evolution
"""
import json
import time
import re
import uuid
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import Counter, defaultdict

# Swarm imports (fallback to stubs for standalone testing)
try:
    from mss_swarm import SwarmNode, MessageBus, SharedStore, SwarmOrchestrator
    from meeting_room import MeetingRoom
    from normative_field import NormativeField
except ImportError:
    SwarmNode = object
    MessageBus = object
    SharedStore = object
    SwarmOrchestrator = object
    MeetingRoom = object
    NormativeField = object

# Optional: Doc-Agent (requires python-docx, openpyxl, fpdf2, python-pptx)
try:
    from doc_agent import DocAgent
except ImportError:
    DocAgent = None


# ═══════════════════════════════════════════════════════
# 1. KB-Agent
# ═══════════════════════════════════════════════════════

class KBAgent:
    """Knowledge base agent: search, CRUD, audit, dedup."""
    
    CAPABILITIES = ["kb_search", "kb_write", "kb_audit", "kb_dedup", "kb_index"]
    
    def __init__(self, agent_id: str, room, swarm=None):
        self.agent_id = agent_id
        self.room = room
        self.swarm = swarm
        self.index: Dict[str, List[str]] = defaultdict(list)  # keyword → kb_keys
        self._kb_cache: Dict[str, Dict] = {}
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Full-text search across KB entries."""
        results = []
        query_terms = query.lower().split()
        
        # Search in indexed keywords
        matched_keys = set()
        for term in query_terms:
            for key in self.index.get(term, []):
                matched_keys.add(key)
        
        # Also search stored entries
        all_entries = self.room.query("kb", limit=1000)
        for key, value in all_entries.items:
            if isinstance(value, dict):
                text = json.dumps(value, ensure_ascii=False).lower()
                score = sum(1 for t in query_terms if t in text)
                if score > 0:
                    matched_keys.add(key)
        
        for key in matched_keys:
            entry = self.room.get("kb", key)
            if entry and len(results) < limit:
                results.append({"key": key, "entry": entry})
        
        return results
    
    def write(self, key: str, content: Dict, layer: str = "L0_FOUNDATION") -> Dict:
        """Write a KB entry with metadata."""
        entry = {
            "h_id": key,
            "content": content,
            "layer": layer,
            "written_at": time.time(),
            "written_by": self.agent_id,
            "version": 1,
        }
        self.room.set("kb", key, entry)
        
        # Index keywords
        text = json.dumps(content, ensure_ascii=False).lower()
        words = set(re.findall(r'\w+', text))
        for w in words:
            if len(w) >= 2:
                self.index[w].append(key)
        
        return {"status": "written", "key": key, "layer": layer}
    
    def audit(self, layer: str = "") -> Dict:
        """Audit KB for gaps, duplicates, and missing indexes."""
        entries = self.room.query("kb", limit=5000)
        stats = {
            "total_entries": entries.total,
            "layers": Counter(),
            "duplicates": [],
            "missing_h_ids": [],
        }
        
        seen_ids = set()
        for key, value in entries.items:
            if isinstance(value, dict):
                layer_name = value.get("layer", "unknown")
                stats["layers"][layer_name] += 1
                
                h_id = value.get("h_id", key)
                if h_id in seen_ids:
                    stats["duplicates"].append(key)
                seen_ids.add(h_id)
        
        return stats
    
    def dedup(self) -> Dict:
        """Find and resolve duplicate entries."""
        audit = self.audit()
        removed = []
        
        for dup_key in audit.get("duplicates", []):
            self.room.delete("kb", dup_key)
            removed.append(dup_key)
        
        return {"removed": removed, "count": len(removed)}
    
    def on_task_assignment(self, task: Dict) -> Dict:
        """Handle task assigned by PlanAgent."""
        action = task.get("action", "search")
        
        if action == "search":
            return {"results": self.search(task.get("query", ""), task.get("limit", 10))}
        elif action == "write":
            return self.write(task["key"], task["content"], task.get("layer", "L0_FOUNDATION"))
        elif action == "audit":
            return self.audit(task.get("layer", ""))
        elif action == "dedup":
            return self.dedup()
        else:
            return {"error": f"Unknown action: {action}"}


# ═══════════════════════════════════════════════════════
# 2. Code-Agent
# ═══════════════════════════════════════════════════════

class CodeAgent:
    """Code generation & audit agent."""
    
    CAPABILITIES = ["code_gen", "code_audit", "code_refactor", "syntax_check"]
    
    def __init__(self, agent_id: str, room, swarm=None):
        self.agent_id = agent_id
        self.room = room
        self.swarm = swarm
        self.patterns = {
            "sql_injection": r'(?i)(execute\s*\(|\.execute\s*\(\s*f["\']|raw\s*sql)',
            "hardcoded_secret": r'(?i)(password\s*=\s*["\'][^"\']+["\']|api_key\s*=\s*["\'][^"\']+["\']|secret\s*=\s*["\'][^"\']+["\'])',
            "unsafe_eval": r'(?i)(eval\s*\(|exec\s*\(|__import__\s*\()',
            "missing_error_handling": r'(?m)^(?!.*(try|except|with|if __name__)).*\.(open|write|read|connect|request)\s*\(',  # simplified
        }
    
    def generate(self, spec: Dict) -> Dict:
        """Generate code from specification."""
        language = spec.get("language", "python")
        description = spec.get("description", "")
        template = spec.get("template", "")
        
        # Store spec for future reference
        code_id = f"code_{uuid.uuid4().hex[:8]}"
        self.room.set("task", f"code:{code_id}", {
            "spec": spec, "generated_at": time.time(), "status": "generated",
        })
        
        return {
            "code_id": code_id,
            "language": language,
            "template": template,
            "status": "spec_stored",  # Actual generation via LLM in real system
        }
    
    def audit(self, code: str, rules: List[str] = None) -> Dict:
        """Audit code for vulnerabilities and anti-patterns."""
        rules = rules or list(self.patterns.keys())
        findings = []
        
        for rule_name in rules:
            pattern = self.patterns.get(rule_name)
            if pattern:
                for match in re.finditer(pattern, code, re.MULTILINE):
                    findings.append({
                        "rule": rule_name,
                        "line": code[:match.start()].count('\n') + 1,
                        "snippet": code[max(0, match.start()-20):match.end()+20],
                    })
        
        return {
            "total_findings": len(findings),
            "severity": "high" if len(findings) > 3 else "medium" if findings else "low",
            "findings": findings,
        }
    
    def refactor(self, code: str, target: str) -> Dict:
        """Suggest refactoring improvements."""
        suggestions = []
        
        # Line count check
        lines = code.split('\n')
        if len(lines) > 200:
            suggestions.append({"type": "length", "message": f"Module has {len(lines)} lines, consider splitting"})
        
        # Function length check
        func_lines = []
        current_func = None
        for line in lines:
            if line.strip().startswith('def '):
                if current_func and func_lines:
                    suggestions.append({"type": "function_length", "function": current_func, "lines": len(func_lines)})
                current_func = line.strip()
                func_lines = [line]
            elif current_func:
                func_lines.append(line)
        
        return {"suggestions": suggestions, "count": len(suggestions)}
    
    def on_task_assignment(self, task: Dict) -> Dict:
        action = task.get("action", "generate")
        
        if action == "generate":
            return self.generate(task.get("spec", {}))
        elif action == "audit":
            return self.audit(task.get("code", ""), task.get("rules"))
        elif action == "refactor":
            return self.refactor(task.get("code", ""), task.get("target", "quality"))
        else:
            return {"error": f"Unknown action: {action}"}


# ═══════════════════════════════════════════════════════
# 3. Video-Agent
# ═══════════════════════════════════════════════════════

class VideoAgent:
    """Video generation & editing agent."""
    
    CAPABILITIES = ["video_gen", "video_render", "video_clip", "scene_plan"]
    
    def __init__(self, agent_id: str, room, swarm=None):
        self.agent_id = agent_id
        self.room = room
        self.swarm = swarm
    
    def plan_scene(self, script: str, style: str = "ancient_chinese") -> Dict:
        """Plan video scenes from script."""
        # Split script into segments
        segments = [s.strip() for s in script.split('\n\n') if s.strip()]
        
        scenes = []
        for i, seg in enumerate(segments):
            scenes.append({
                "scene_id": f"scene_{i+1:03d}",
                "text": seg[:200],
                "duration_estimate": max(3, len(seg) // 20),  # ~20 chars/sec
                "style": style,
                "key_elements": self._extract_key_elements(seg),
            })
        
        scene_id = f"sceneplan_{uuid.uuid4().hex[:8]}"
        self.room.set("task", f"video:scene:{scene_id}", {
            "script": script, "style": style, "scenes": scenes,
            "total_duration": sum(s["duration_estimate"] for s in scenes),
        })
        
        return {"scene_id": scene_id, "scene_count": len(scenes), "scenes": scenes}
    
    def _extract_key_elements(self, text: str) -> List[str]:
        """Extract key visual elements from text."""
        visual_keywords = ["山", "水", "云", "月", "剑", "花", "门", "路",
                          "树", "石", "桥", "亭", "楼", "舟", "灯", "雪"]
        found = []
        for kw in visual_keywords:
            if kw in text:
                found.append(kw)
        return found[:5]
    
    def detect_clips(self, video_meta: Dict) -> Dict:
        """Detect scene boundaries / clips in video metadata."""
        return {
            "clip_count": video_meta.get("scene_count", 0),
            "estimated_duration": video_meta.get("total_duration", 0),
            "transitions_needed": max(0, video_meta.get("scene_count", 1) - 1),
        }
    
    def on_task_assignment(self, task: Dict) -> Dict:
        action = task.get("action", "plan_scene")
        
        if action == "plan_scene":
            return self.plan_scene(task.get("script", ""), task.get("style", "ancient_chinese"))
        elif action == "detect_clips":
            return self.detect_clips(task.get("video_meta", {}))
        else:
            return {"error": f"Unknown action: {action}"}


# ═══════════════════════════════════════════════════════
# 4. Translate-Agent
# ═══════════════════════════════════════════════════════

class TranslateAgent:
    """Multi-language translation agent with cultural adaptation."""
    
    CAPABILITIES = ["translate", "localize", "term_consistency", "cultural_adapt"]
    
    # Term consistency dictionary
    TERM_DB = {
        "en→zh": {
            "heat tax": "热税",
            "meaning supremacy": "意义至上",
            "molting": "蜕壳",
            "normative field": "规范场",
            "identity strength": "身份强度",
            "paradox": "悖论",
            "mechanism design": "机制设计",
        },
        "zh→en": {
            "热税": "heat tax",
            "意义至上": "meaning supremacy",
            "蜕壳": "molting",
            "规范场": "normative field",
            "身份强度": "identity strength",
            "悖论": "paradox",
            "机制设计": "mechanism design",
        },
    }
    
    def __init__(self, agent_id: str, room, swarm=None):
        self.agent_id = agent_id
        self.room = room
        self.swarm = swarm
        self.translation_memory: Dict[str, Dict] = {}
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> Dict:
        """Translate text with term consistency check."""
        pair = f"{source_lang}→{target_lang}"
        term_db = self.TERM_DB.get(pair, {})
        
        # Check which terms are present
        detected_terms = {}
        for src_term, tgt_term in term_db.items():
            if src_term.lower() in text.lower():
                detected_terms[src_term] = tgt_term
        
        # Store in translation memory
        mem_key = hashlib.sha256(f"{text[:50]}{source_lang}{target_lang}".encode()).hexdigest()[:12]
        self.translation_memory[mem_key] = {
            "source": text[:200], "source_lang": source_lang,
            "target_lang": target_lang, "terms": detected_terms,
            "timestamp": time.time(),
        }
        
        return {
            "memory_id": mem_key,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "detected_terms": detected_terms,
            "char_count": len(text),
            "status": "queued_for_translation",  # Real translation via LLM
        }
    
    def check_consistency(self, text: str, language: str) -> Dict:
        """Check term consistency across translations."""
        issues = []
        
        # Check for mixed terminology (e.g., both "heat tax" and "thermal tax")
        if language == "zh":
            if "意义至上" in text and "meaning supremacy" in text:
                issues.append("Mixed language: '意义至上' vs 'meaning supremacy'")
        
        return {"issues": issues, "consistent": len(issues) == 0}
    
    def on_task_assignment(self, task: Dict) -> Dict:
        action = task.get("action", "translate")
        
        if action == "translate":
            return self.translate(
                task.get("text", ""),
                task.get("source_lang", "en"),
                task.get("target_lang", "zh"),
            )
        elif action == "check_consistency":
            return self.check_consistency(task.get("text", ""), task.get("language", "zh"))
        else:
            return {"error": f"Unknown action: {action}"}


# ═══════════════════════════════════════════════════════
# 5. Product-Agent
# ═══════════════════════════════════════════════════════

class ProductAgent:
    """Product management agent: specs, stories, roadmap."""
    
    CAPABILITIES = ["product_spec", "user_story", "roadmap", "stakeholder_align"]
    
    def __init__(self, agent_id: str, room, swarm=None):
        self.agent_id = agent_id
        self.room = room
        self.swarm = swarm
        self.products: Dict[str, Dict] = {}
    
    def create_spec(self, product_name: str, description: str,
                    features: List[str] = None) -> Dict:
        """Create a product specification."""
        prod_id = f"prod_{uuid.uuid4().hex[:8]}"
        
        spec = {
            "product_id": prod_id,
            "name": product_name,
            "description": description,
            "features": features or [],
            "status": "draft",
            "created_at": time.time(),
            "created_by": self.agent_id,
            "version": "0.1.0",
        }
        
        self.products[prod_id] = spec
        self.room.set("task", f"product:{prod_id}", spec)
        
        return spec
    
    def create_user_stories(self, product_id: str, features: List[str]) -> Dict:
        """Generate user stories from features."""
        stories = []
        for i, feature in enumerate(features):
            stories.append({
                "id": f"US-{i+1:03d}",
                "feature": feature,
                "as_a": "user",
                "i_want": feature,
                "so_that": f"achieve {feature.lower()}",
                "priority": "P1" if i < 3 else "P2",
                "acceptance_criteria": [
                    f"Given {feature}, when user activates it, then expected outcome occurs",
                ],
            })
        
        return {"product_id": product_id, "stories": stories, "count": len(stories)}
    
    def create_roadmap(self, product_id: str, milestones: List[Dict]) -> Dict:
        """Create product roadmap."""
        roadmap = {
            "product_id": product_id,
            "milestones": [],
            "created_at": time.time(),
        }
        
        for i, ms in enumerate(milestones):
            roadmap["milestones"].append({
                "id": f"M{i+1}",
                "name": ms.get("name", f"Milestone {i+1}"),
                "goal": ms.get("goal", ""),
                "quarter": ms.get("quarter", f"Q{(i%4)+1}"),
                "status": "planned",
            })
        
        return roadmap
    
    def on_task_assignment(self, task: Dict) -> Dict:
        action = task.get("action", "create_spec")
        
        if action == "create_spec":
            return self.create_spec(
                task.get("product_name", "Untitled"),
                task.get("description", ""),
                task.get("features", []),
            )
        elif action == "create_user_stories":
            return self.create_user_stories(
                task.get("product_id", ""),
                task.get("features", []),
            )
        elif action == "create_roadmap":
            return self.create_roadmap(
                task.get("product_id", ""),
                task.get("milestones", []),
            )
        else:
            return {"error": f"Unknown action: {action}"}


# ═══════════════════════════════════════════════════════
# Agent Registry
# ═══════════════════════════════════════════════════════

AGENT_REGISTRY = {
    "kb":        {"class": KBAgent,        "capabilities": KBAgent.CAPABILITIES},
    "code":      {"class": CodeAgent,      "capabilities": CodeAgent.CAPABILITIES},
    "video":     {"class": VideoAgent,     "capabilities": VideoAgent.CAPABILITIES},
    "translate": {"class": TranslateAgent, "capabilities": TranslateAgent.CAPABILITIES},
    "product":   {"class": ProductAgent,   "capabilities": ProductAgent.CAPABILITIES},
    **({"doc": {"class": DocAgent, "capabilities": DocAgent.CAPABILITIES}} if DocAgent else {}),
}


def create_all_agents(room, swarm=None) -> Dict[str, Any]:
    """Factory: create all 6 specialized agents connected to room."""
    agents = {}
    for agent_type, info in AGENT_REGISTRY.items():
        if info["class"] is None:
            continue  # skip optional agents not installed
        agent_id = f"{agent_type}_{uuid.uuid4().hex[:6]}"
        agents[agent_type] = info["class"](agent_id, room, swarm)
    return agents


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    from meeting_room import MeetingRoom
    room = MeetingRoom()
    
    # Test 1: KB-Agent write + search
    kb = KBAgent("kb_001", room)
    kb.write("H601", {"title": "Test Entry", "body": "This is about heat tax and thermodynamics"})
    results = kb.search("heat tax")
    assert len(results) >= 1, f"Should find entry about heat tax: {results}"
    print("T1 PASS: KB-Agent write+search")
    
    # Test 2: KB-Agent audit
    audit = kb.audit()
    assert audit["total_entries"] >= 1
    print(f"T2 PASS: KB-Agent audit ({audit['total_entries']} entries)")
    
    # Test 3: Code-Agent audit
    code = CodeAgent("code_001", room)
    findings = code.audit("password = 'admin123'\nconn.execute('SELECT * FROM users')")
    assert findings["total_findings"] >= 2, f"Should find >=2 issues: {findings}"
    print(f"T3 PASS: Code-Agent audit ({findings['total_findings']} findings)")
    
    # Test 4: Code-Agent generate
    gen = code.generate({"language": "python", "description": "REST API endpoint"})
    assert gen["status"] == "spec_stored"
    print("T4 PASS: Code-Agent generate stores spec")
    
    # Test 5: Video-Agent scene planning
    video = VideoAgent("video_001", room)
    script = "远处有一座山。\n\n山脚下有一条小路。\n\n月光洒在水面上。"
    plan = video.plan_scene(script, "ancient_chinese")
    assert plan["scene_count"] == 3, f"Expected 3 scenes, got {plan['scene_count']}"
    assert len(plan["scenes"][0]["key_elements"]) > 0  # Should detect 山
    print(f"T5 PASS: Video-Agent plans {plan['scene_count']} scenes")
    
    # Test 6: Translate-Agent term detection
    trans = TranslateAgent("trans_001", room)
    result = trans.translate("The heat tax model explains meaning loss.", "en", "zh")
    assert "heat tax" in result["detected_terms"], f"Should detect 'heat tax': {result}"
    print(f"T6 PASS: Translate-Agent detects {len(result['detected_terms'])} terms")
    
    # Test 7: Translate-Agent consistency
    check = trans.check_consistency("意义至上 meaning supremacy", "zh")
    assert not check["consistent"], "Should flag mixed language"
    print("T7 PASS: Translate-Agent flags mixed terminology")
    
    # Test 8: Product-Agent spec + stories
    product = ProductAgent("prod_001", room)
    spec = product.create_spec("MSS-VDP", "Vulnerability Detection Pipeline",
                              ["AST scanning", "Multi-language", "CI integration"])
    assert spec["status"] == "draft"
    
    stories = product.create_user_stories(spec["product_id"], spec["features"])
    assert stories["count"] == 3
    print(f"T8 PASS: Product-Agent spec + {stories['count']} user stories")
    
    # Test 9: Product-Agent roadmap
    roadmap = product.create_roadmap(spec["product_id"], [
        {"name": "v1.0", "goal": "10 languages", "quarter": "Q3"},
        {"name": "v2.0", "goal": "Fuzzer integration", "quarter": "Q4"},
    ])
    assert len(roadmap["milestones"]) == 2
    print("T9 PASS: Product-Agent roadmap created")
    
    # Test 10: Factory creates all agents
    all_agents = create_all_agents(room)
    assert len(all_agents) >= 5
    print(f"T10 PASS: Factory creates {len(all_agents)} agents: {list(all_agents.keys())}")
    
    print("\nS-007 Specialized Agents: all 10 tests PASSED")


if __name__ == "__main__":
    _test()
