"""
MSS Code Cleanup Tool
Prepares codebase for open source release
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class CodeCleanupTool:
    """Tool for cleaning and preparing code for open source"""

    def __init__(self, project_dir: str = r"C:\MSS-AI-Project"):
        self.project_dir = Path(project_dir)
        self.report = {
            "files_processed": 0,
            "issues_found": 0,
            "issues_fixed": 0,
            "sensitive_data_found": [],
            "documentation_status": {}
        }

    def scan_sensitive_data(self) -> List[Dict]:
        """Scan for potentially sensitive data"""
        sensitive_patterns = [
            (r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']', "API Key"),
            (r'password\s*[=:]\s*["\'][^"\']+["\']', "Password"),
            (r'secret\s*[=:]\s*["\'][^"\']+["\']', "Secret"),
            (r'token\s*[=:]\s*["\'][^"\']+["\']', "Token"),
            (r'[\w.-]+@[\w.-]+\.\w+', "Email"),
            (r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', "IP Address")
        ]

        findings = []

        for root, dirs, files in os.walk(self.project_dir):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv']]

            for file in files:
                if not file.endswith(('.py', '.js', '.ts', '.json', '.md', '.txt', '.yml', '.yaml')):
                    continue

                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                except:
                    continue

                for pattern, ptype in sensitive_patterns:
                    matches = list(re.finditer(pattern, content, re.IGNORECASE))
                    for match in matches:
                        findings.append({
                            "file": str(filepath.relative_to(self.project_dir)),
                            "type": ptype,
                            "line": content[:match.start()].count('\n') + 1,
                            "context": match.group()[:50] + "..." if len(match.group()) > 50 else match.group()
                        })

        self.report["sensitive_data_found"] = findings
        return findings

    def check_documentation(self) -> Dict:
        """Check documentation completeness"""
        required_docs = [
            "README.md",
            "LICENSE",
            "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md",
            "docs/"
        ]

        status = {}
        for doc in required_docs:
            path = self.project_dir / doc
            status[doc] = {
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0
            }

        self.report["documentation_status"] = status
        return status

    def generate_readme(self) -> str:
        """Generate README.md template"""
        readme = """# MSS-AI Project

## 项目简介

MSS-AI（Meta-Self-Similarity System AI）是一个基于意义本体论（MSS）的符号推理引擎和AI系统。

## 核心特性

- **符号推理引擎v4.0**: 基于CSR稀疏矩阵的高效图遍历
- **知识库系统**: 支持L1-L4层级分类的知识管理
- **韧性扫描器**: 组织韧性评估工具
- **合规扫描器**: 文本合规性分析
- **数据采集系统**: 实验数据收集与管理

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动符号引擎

```bash
cd symbolic_engine_v4
python api/rest.py
```

### 启动韧性扫描器

```bash
python resilience_scanner_saas.py
```

## 项目结构

```
MSS-AI-Project/
├── symbolic_engine_v4/     # 符号推理引擎v4.0
│   ├── core/               # 核心类型和图结构
│   ├── parser/             # 知识库解析器
│   ├── reasoner/           # 推理引擎
│   ├── api/                # RESTful API
│   └── monitor/            # 健康监控
├── knowledge_base/         # 知识库文件
├── resilience_scanner_saas.py  # 韧性扫描器SaaS
├── compliance_scanner_api.py   # 合规扫描器API
└── data_collection_system.py   # 数据采集系统
```

## 贡献指南

请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)

## 许可证

[LICENSE](LICENSE)

## 联系方式

- 项目主页: [待添加]
- 问题反馈: [待添加]
- 邮件: [待添加]

---

*本项目基于MSS（Meta-Self-Similarity System）意义本体论框架开发*
"""

        return readme

    def generate_license(self) -> str:
        """Generate LICENSE file"""
        license_text = """MIT License

Copyright (c) 2026 MSS-AI Project Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

        return license_text

    def generate_requirements(self) -> str:
        """Generate requirements.txt"""
        requirements = """# MSS-AI Project Dependencies
# Core
numpy>=1.24.0

# Optional: CUDA acceleration
# cupy-cuda13x>=14.0.0

# Optional: Visualization
# matplotlib>=3.8.0

# Optional: Web framework (for future Flask migration)
# flask>=3.0.0
"""

        return requirements

    def cleanup_code(self) -> Dict:
        """Perform code cleanup"""
        cleanup_report = {
            "files_processed": 0,
            "issues_fixed": 0,
            "actions": []
        }

        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv']]

            for file in files:
                if not file.endswith('.py'):
                    continue

                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                except:
                    continue

                original = content

                # Remove trailing whitespace
                content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)

                # Ensure file ends with newline
                if content and not content.endswith('\n'):
                    content += '\n'

                # Remove multiple blank lines
                content = re.sub(r'\n{3,}', '\n\n', content)

                if content != original:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    cleanup_report["issues_fixed"] += 1
                    cleanup_report["actions"].append(f"Cleaned: {filepath.relative_to(self.project_dir)}")

                cleanup_report["files_processed"] += 1

        self.report["files_processed"] = cleanup_report["files_processed"]
        self.report["issues_fixed"] = cleanup_report["issues_fixed"]

        return cleanup_report

    def generate_cleanup_report(self) -> str:
        """Generate cleanup report"""
        report = f"""# MSS-AI Project Cleanup Report

Generated: {datetime.now().isoformat()}

## Summary

- Files Processed: {self.report['files_processed']}
- Issues Fixed: {self.report['issues_fixed']}
- Sensitive Data Findings: {len(self.report['sensitive_data_found'])}

## Sensitive Data Scan

"""

        if self.report['sensitive_data_found']:
            report += "| File | Type | Line | Context |\n"
            report += "|------|------|------|---------|\n"
            for finding in self.report['sensitive_data_found']:
                report += f"| {finding['file']} | {finding['type']} | {finding['line']} | {finding['context']} |\n"
        else:
            report += "✅ No sensitive data found\n"

        report += "\n## Documentation Status\n\n"
        report += "| Document | Exists | Size |\n"
        report += "|----------|--------|------|\n"
        for doc, status in self.report['documentation_status'].items():
            exists = "✅" if status['exists'] else "❌"
            size = f"{status['size']} bytes" if status['exists'] else "N/A"
            report += f"| {doc} | {exists} | {size} |\n"

        return report

    def run_full_cleanup(self):
        """Run full cleanup process"""
        print("Starting code cleanup...")

        # 1. Scan for sensitive data
        print("1. Scanning for sensitive data...")
        findings = self.scan_sensitive_data()
        print(f"   Found {len(findings)} potential issues")

        # 2. Check documentation
        print("2. Checking documentation...")
        docs = self.check_documentation()
        missing = [k for k, v in docs.items() if not v['exists']]
        print(f"   Missing: {', '.join(missing) if missing else 'None'}")

        # 3. Cleanup code
        print("3. Cleaning up code...")
        cleanup = self.cleanup_code()
        print(f"   Processed {cleanup['files_processed']} files, fixed {cleanup['issues_fixed']} issues")

        # 4. Generate missing documentation
        print("4. Generating documentation...")

        if not (self.project_dir / "README.md").exists():
            with open(self.project_dir / "README.md", 'w', encoding='utf-8') as f:
                f.write(self.generate_readme())
            print("   Generated README.md")

        if not (self.project_dir / "LICENSE").exists():
            with open(self.project_dir / "LICENSE", 'w', encoding='utf-8') as f:
                f.write(self.generate_license())
            print("   Generated LICENSE")

        if not (self.project_dir / "requirements.txt").exists():
            with open(self.project_dir / "requirements.txt", 'w', encoding='utf-8') as f:
                f.write(self.generate_requirements())
            print("   Generated requirements.txt")

        # 5. Generate report
        print("5. Generating report...")
        report = self.generate_cleanup_report()
        with open(self.project_dir / "CLEANUP_REPORT.md", 'w', encoding='utf-8') as f:
            f.write(report)
        print("   Generated CLEANUP_REPORT.md")

        print("\nCleanup complete!")
        return self.report

if __name__ == "__main__":
    tool = CodeCleanupTool()
    tool.run_full_cleanup()
