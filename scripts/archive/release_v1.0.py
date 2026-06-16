# -*- coding: utf-8 -*-
"""
MSS-AI v1.0 Release Script
Validates system readiness and creates release package
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

class ReleaseManager:
    """Manages v1.0 release process"""

    REQUIRED_FILES = [
        "mss_tactic_integrated.py",
        "mss_analyzer.py",
        "mss_responder_v2.py",
        "mss_model_manager.py",
        "dialog_fork.py",
        "test_integration_v1.py",
        "skills/skill_loader.py",
        "skills/catalog.yaml",
        "README_v1.0.md",
        "CHANGELOG_v1.0.md",
    ]

    SKILL_DIRS = [
        "skills/L1_core",
        "skills/L2_protective",
        "skills/L3_heuristic",
    ]

    def __init__(self, project_dir: str = None):
        if project_dir is None:
            project_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_dir = Path(project_dir)
        self.release_dir = self.project_dir / "releases"
        self.errors = []
        self.warnings = []

    def validate_structure(self) -> bool:
        """Check all required files exist"""
        print("=" * 60)
        print("RELEASE VALIDATION")
        print("=" * 60)

        print("\n1. Checking required files...")
        all_good = True
        for file_path in self.REQUIRED_FILES:
            full_path = self.project_dir / file_path
            if full_path.exists():
                size = full_path.stat().st_size
                print(f"   [OK] {file_path} ({size} bytes)")
            else:
                print(f"   [MISSING] {file_path}")
                self.errors.append(f"Missing: {file_path}")
                all_good = False

        return all_good

    def validate_skills(self) -> bool:
        """Check skill directories"""
        print("\n2. Checking skill directories...")
        all_good = True

        for dir_path in self.SKILL_DIRS:
            full_path = self.project_dir / dir_path
            if full_path.exists() and full_path.is_dir():
                files = list(full_path.glob("*.md"))
                print(f"   [OK] {dir_path} ({len(files)} files)")
            else:
                print(f"   [MISSING] {dir_path}")
                self.warnings.append(f"Empty skill dir: {dir_path}")

        return all_good

    def run_tests(self) -> bool:
        """Run integration tests"""
        print("\n3. Running integration tests...")

        try:
            result = subprocess.run(
                [sys.executable, "test_integration_v1.py"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120
            )

            if result.returncode == 0:
                print("   [PASS] All tests passed")
                return True
            else:
                print("   [FAIL] Tests failed")
                print(result.stdout[-500:])
                self.errors.append("Integration tests failed")
                return False

        except Exception as e:
            print(f"   [ERROR] {e}")
            self.errors.append(f"Test execution error: {e}")
            return False

    def check_ollama(self) -> bool:
        """Check Ollama availability"""
        print("\n4. Checking Ollama...")

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                models = [line.split()[0] for line in lines if line.strip()]
                print(f"   [OK] Ollama running ({len(models)} models)")
                for model in models:
                    print(f"      - {model}")
                return True
            else:
                print("   [WARN] Ollama not responding")
                self.warnings.append("Ollama not available")
                return False

        except FileNotFoundError:
            print("   [WARN] Ollama not installed")
            self.warnings.append("Ollama not installed")
            return False

    def create_package(self) -> str:
        """Create release package"""
        print("\n5. Creating release package...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        release_name = f"mss-ai-v1.0-{timestamp}"
        release_path = self.release_dir / release_name

        # Create directory
        release_path.mkdir(parents=True, exist_ok=True)

        # Copy core files
        for file_path in self.REQUIRED_FILES:
            src = self.project_dir / file_path
            if src.exists():
                dst = release_path / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        # Copy skill directories
        for dir_path in self.SKILL_DIRS:
            src = self.project_dir / dir_path
            if src.exists():
                dst = release_path / dir_path
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

        # Create manifest
        manifest = {
            "version": "1.0.0",
            "timestamp": timestamp,
            "files": self.REQUIRED_FILES,
            "validation": {
                "errors": len(self.errors),
                "warnings": len(self.warnings)
            }
        }

        with open(release_path / "manifest.json", 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)

        print(f"   [OK] Created: {release_path}")
        return str(release_path)

    def run_full_release(self) -> bool:
        """Execute full release process"""
        print("\n" + "=" * 60)
        print("MSS-AI v1.0 Release Process")
        print("=" * 60)

        # Validation steps
        checks = [
            ("Structure", self.validate_structure),
            ("Skills", self.validate_skills),
            ("Tests", self.run_tests),
            ("Ollama", self.check_ollama),
        ]

        results = {}
        for name, check_fn in checks:
            try:
                results[name] = check_fn()
            except Exception as e:
                print(f"   [ERROR] {e}")
                results[name] = False

        # Summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        for name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"   {status} {name}")

        if self.warnings:
            print(f"\n   Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"      - {w}")

        if self.errors:
            print(f"\n   Errors ({len(self.errors)}):")
            for e in self.errors:
                print(f"      - {e}")

        # Create package if no critical errors
        if len(self.errors) == 0:
            release_path = self.create_package()
            print(f"\n   [RELEASED] {release_path}")
            return True
        else:
            print("\n   [BLOCKED] Fix errors before releasing")
            return False

if __name__ == "__main__":
    manager = ReleaseManager()
    success = manager.run_full_release()
    sys.exit(0 if success else 1)
