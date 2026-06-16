"""
MSS Documentation Generator
Generates comprehensive documentation for the project
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class DocumentationGenerator:
    """Generate project documentation"""
    
    def __init__(self, project_dir: str = r"C:\MSS-AI-Project"):
        self.project_dir = Path(project_dir)
        self.docs_dir = self.project_dir / "docs"
        self.docs_dir.mkdir(exist_ok=True)
    
    def generate_module_documentation(self, module_name: str, 
                                     source_file: str) -> str:
        """
        Generate documentation for a module
        
        Args:
            module_name: Module name
            source_file: Source file path
        
        Returns:
            Markdown documentation
        """
        doc = []
        doc.append(f"# {module_name}")
        doc.append("")
        doc.append(f"**Source**: `{source_file}`")
        doc.append(f"**Generated**: {datetime.now().isoformat()}")
        doc.append("")
        
        # Read source file
        source_path = self.project_dir / source_file
        if source_path.exists():
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract docstring
            if '"""' in content:
                start = content.find('"""') + 3
                end = content.find('"""', start)
                if end > start:
                    docstring = content[start:end].strip()
                    doc.append("## Description")
                    doc.append("")
                    doc.append(docstring)
                    doc.append("")
            
            # Extract classes
            doc.append("## Classes")
            doc.append("")
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('class '):
                    class_name = line.split('(')[0].replace('class ', '').strip(':')
                    doc.append(f"### {class_name}")
                    doc.append("")
                    
                    # Extract methods
                    for j in range(i+1, len(lines)):
                        if lines[j].startswith('    def ') and not lines[j].startswith('    def __'):
                            method_name = lines[j].split('(')[0].replace('    def ', '').strip()
                            doc.append(f"- `{method_name}()`")
                        elif lines[j].startswith('class '):
                            break
                    
                    doc.append("")
        
        return "\n".join(doc)
    
    def generate_api_documentation(self) -> str:
        """Generate API documentation"""
        doc = []
        doc.append("# MSS-AI API Documentation")
        doc.append("")
        doc.append(f"**Version**: 1.0")
        doc.append(f"**Generated**: {datetime.now().isoformat()}")
        doc.append("")
        
        # Symbolic Engine API
        doc.append("## Symbolic Engine API")
        doc.append("")
        doc.append("### Endpoints")
        doc.append("")
        doc.append("| Endpoint | Method | Description |")
        doc.append("|----------|--------|-------------|")
        doc.append("| `/api/v1/search` | POST | Search knowledge base |")
        doc.append("| `/api/v1/path` | POST | Find path between nodes |")
        doc.append("| `/api/v1/node/{id}` | GET | Get node details |")
        doc.append("| `/api/v1/health` | GET | Health check |")
        doc.append("")
        
        # Compliance Scanner API
        doc.append("## Compliance Scanner API")
        doc.append("")
        doc.append("### Endpoints")
        doc.append("")
        doc.append("| Endpoint | Method | Description |")
        doc.append("|----------|--------|-------------|")
        doc.append("| `/api/v1/analyze` | POST | Analyze text compliance |")
        doc.append("| `/api/v1/batch` | POST | Batch analyze |")
        doc.append("| `/api/v1/rules` | GET | Get compliance rules |")
        doc.append("")
        
        # Resilience Scanner API
        doc.append("## Resilience Scanner API")
        doc.append("")
        doc.append("### Endpoints")
        doc.append("")
        doc.append("| Endpoint | Method | Description |")
        doc.append("|----------|--------|-------------|")
        doc.append("| `/api/v1/scan` | POST | Scan organization resilience |")
        doc.append("| `/api/v1/report` | GET | Generate report |")
        doc.append("| `/api/v1/visualize` | GET | Get visualization data |")
        doc.append("")
        
        return "\n".join(doc)
    
    def generate_architecture_documentation(self) -> str:
        """Generate architecture documentation"""
        doc = []
        doc.append("# MSS-AI Architecture")
        doc.append("")
        doc.append(f"**Version**: 4.0")
        doc.append(f"**Generated**: {datetime.now().isoformat()}")
        doc.append("")
        
        doc.append("## System Overview")
        doc.append("")
        doc.append("MSS-AI is a meaning-based AI system built on the MSS (Meaning Structure System) framework.")
        doc.append("")
        
        doc.append("## Core Components")
        doc.append("")
        
        doc.append("### 1. Symbolic Engine")
        doc.append("- CSR graph data structure")
        doc.append("- A* path finding")
        doc.append("- Plugin system")
        doc.append("- Query cache")
        doc.append("")
        
        doc.append("### 2. Compliance Scanner")
        doc.append("- 7 compliance rules")
        doc.append("- Real-time analysis")
        doc.append("- Report generation")
        doc.append("")
        
        doc.append("### 3. Resilience Scanner")
        doc.append("- Organization resilience analysis")
        doc.append("- Visualization")
        doc.append("- Web interface")
        doc.append("")
        
        doc.append("### 4. Data Collection")
        doc.append("- Real-time data streaming")
        doc.append("- Visualization")
        doc.append("- Export capabilities")
        doc.append("")
        
        doc.append("## Data Flow")
        doc.append("")
        doc.append("```")
        doc.append("User Input → Symbolic Engine → Compliance Check → Response")
        doc.append("                ↓")
        doc.append("         Knowledge Base")
        doc.append("                ↓")
        doc.append("         Data Collection")
        doc.append("```")
        doc.append("")
        
        return "\n".join(doc)
    
    def generate_all_documentation(self):
        """Generate all documentation"""
        # Generate module docs
        modules = [
            ("Symbolic Engine v4", "symbolic_engine_v4/engine.py"),
            ("Compliance Scanner", "compliance_scanner_enhanced.py"),
            ("Resilience Scanner", "resilience_visualizer.py"),
            ("Data Collection", "data_collection_system.py"),
            ("Task Bar Manager", "task_bar_manager.py"),
        ]
        
        for name, file in modules:
            doc = self.generate_module_documentation(name, file)
            output_file = self.docs_dir / f"{name.lower().replace(' ', '_')}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(doc)
            print(f"Generated: {output_file}")
        
        # Generate API docs
        api_doc = self.generate_api_documentation()
        with open(self.docs_dir / "api_documentation.md", 'w', encoding='utf-8') as f:
            f.write(api_doc)
        print(f"Generated: {self.docs_dir / 'api_documentation.md'}")
        
        # Generate architecture docs
        arch_doc = self.generate_architecture_documentation()
        with open(self.docs_dir / "architecture.md", 'w', encoding='utf-8') as f:
            f.write(arch_doc)
        print(f"Generated: {self.docs_dir / 'architecture.md'}")
        
        # Generate index
        self._generate_index()
    
    def _generate_index(self):
        """Generate documentation index"""
        index = []
        index.append("# MSS-AI Documentation Index")
        index.append("")
        index.append(f"**Generated**: {datetime.now().isoformat()}")
        index.append("")
        index.append("## Modules")
        index.append("")
        
        for doc_file in sorted(self.docs_dir.glob("*.md")):
            if doc_file.name != "index.md":
                index.append(f"- [{doc_file.stem.replace('_', ' ').title()}]({doc_file.name})")
        
        index.append("")
        index.append("## Quick Links")
        index.append("")
        index.append("- [API Documentation](api_documentation.md)")
        index.append("- [Architecture](architecture.md)")
        index.append("- [Task Bar Manager](task_bar_manager.md)")
        index.append("")
        
        with open(self.docs_dir / "index.md", 'w', encoding='utf-8') as f:
            f.write("\n".join(index))
        print(f"Generated: {self.docs_dir / 'index.md'}")

# Example usage
if __name__ == "__main__":
    generator = DocumentationGenerator()
    generator.generate_all_documentation()
    print("\nAll documentation generated successfully!")
