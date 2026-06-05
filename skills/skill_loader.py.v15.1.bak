# -*- coding: utf-8 -*-
"""
MSS Skills Loader - LLLM-compatible skill loading system
Loads skills from L1/L2/L3 directories with progressive activation
"""

import os
import yaml
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class SkillResource:
    """Skill resource entry"""
    name: str
    path: str
    level: str  # L1/L2/L3
    tokens: int = 0
    content: str = ""

@dataclass
class SkillPackage:
    """Skill package (LLLM-compatible)"""
    name: str
    version: str
    resources: Dict[str, SkillResource] = field(default_factory=dict)

    def load_resource(self, name: str) -> Optional[str]:
        """Load resource content"""
        if name in self.resources:
            res = self.resources[name]
            if not res.content and os.path.exists(res.path):
                with open(res.path, 'r', encoding='utf-8') as f:
                    res.content = f.read()
            return res.content
        return None

    def estimate_tokens(self) -> int:
        """Estimate total tokens (rough: 4 chars = 1 token)"""
        total = 0
        for res in self.resources.values():
            if res.content:
                total += len(res.content) // 4
            else:
                # Estimate from file size
                try:
                    total += os.path.getsize(res.path) // 4
                except:
                    pass
        return total

class SkillLoader:
    """
    MSS Skills Loader

    Progressive loading strategy:
    - Phase 1: Load catalog (50-100 tokens)
    - Phase 2: Activate specific level (on-demand)
    - Phase 3: Load full resource content (when needed)
    """

    SKILL_DIRS = {
        "L1": "L1_core",
        "L2": "L2_protective",
        "L3": "L3_heuristic"
    }

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.path.dirname(os.path.abspath(__file__))
        self.base_path = Path(base_path)
        self.catalog = {}
        self.packages = {}
        self._load_catalog()

    def _load_catalog(self):
        """Phase 1: Load catalog.yaml (lightweight)"""
        catalog_path = self.base_path / "catalog.yaml"
        if catalog_path.exists():
            with open(catalog_path, 'r', encoding='utf-8') as f:
                self.catalog = yaml.safe_load(f) or {}

    def load_level(self, level: str, full_content: bool = False) -> SkillPackage:
        """
        Phase 2: Activate specific level

        Args:
            level: L1/L2/L3
            full_content: Whether to load full content immediately
        """
        if level not in self.SKILL_DIRS:
            raise ValueError(f"Unknown level: {level}. Use L1/L2/L3")

        dir_name = self.SKILL_DIRS[level]
        level_path = self.base_path / dir_name

        pkg = SkillPackage(
            name=f"mss-{level.lower()}",
            version=self.catalog.get("version", "unknown")
        )

        if level_path.exists():
            for file_path in level_path.glob("*.md"):
                resource = SkillResource(
                    name=file_path.stem,
                    path=str(file_path),
                    level=level
                )

                if full_content:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        resource.content = f.read()
                        resource.tokens = len(resource.content) // 4

                pkg.resources[resource.name] = resource

        self.packages[level] = pkg
        return pkg

    def load_all_levels(self, full_content: bool = False) -> Dict[str, SkillPackage]:
        """Load all three levels"""
        for level in ["L1", "L2", "L3"]:
            self.load_level(level, full_content)
        return self.packages

    def get_resource(self, level: str, name: str) -> Optional[str]:
        """Phase 3: Load specific resource content on-demand"""
        if level not in self.packages:
            self.load_level(level)

        return self.packages[level].load_resource(name)

    def get_system_prompt_enhancement(self, level: str = "L2") -> str:
        """
        Generate system prompt enhancement from skills
        Used to inject MSS context into agent prompts
        """
        pkg = self.load_level(level)

        enhancement = f"""# MSS Framework Context ({level})

## Active Skills
"""

        for name, res in pkg.resources.items():
            enhancement += f"- {name}\n"

        enhancement += f"\n## Key Principles\n"

        # Load axioms for L1 context
        if level in ["L1", "L2"]:
            axioms = self.get_resource("L1", "axioms_v12.2")
            if axioms:
                # Extract first few axioms as context
                lines = axioms.split('\n')[:30]
                enhancement += '\n'.join(lines)

        return enhancement

    def list_available(self) -> Dict[str, List[str]]:
        """List all available skills by level"""
        result = {}
        for level in ["L1", "L2", "L3"]:
            pkg = self.load_level(level)
            result[level] = list(pkg.resources.keys())
        return result

# Quick test
if __name__ == "__main__":
    print("MSS Skills Loader v1.0")
    print("=" * 60)

    loader = SkillLoader()

    # List available skills
    print("\nAvailable skills:")
    available = loader.list_available()
    for level, skills in available.items():
        print(f"\n{level}: {len(skills)} resources")
        for skill in skills:
            print(f"  - {skill}")

    # Load L2 with full content
    print("\n" + "=" * 60)
    l2_pkg = loader.load_level("L2", full_content=True)
    print(f"\nL2 Package loaded: {len(l2_pkg.resources)} resources")
    print(f"Estimated tokens: {l2_pkg.estimate_tokens()}")

    # Get specific resource
    print("\n" + "=" * 60)
    content = loader.get_resource("L3", "redteam_rules")
    if content:
        print(f"\nRedteam rules loaded: {len(content)} chars")
