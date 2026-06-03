"""CFG-001: 5c Industry Benchmark + 5d Interactive Config"""

import json
from datetime import datetime
from pathlib import Path

class IndustryBenchmarkConfig:
    """行业基准配置系统"""
    
    def __init__(self):
        self.benchmarks = {}
        self.config = {}
    
    def load_default_benchmarks(self):
        """加载默认行业基准"""
        self.benchmarks = {
            "tech_startup": {
                "name": "科技初创",
                "resilience_target": 0.6,
                "heat_tax_threshold": 0.4,
                "tuning_degree_min": 0.5,
                "meaning_flux_target": 1e6,
            },
            "tech_enterprise": {
                "name": "科技企业",
                "resilience_target": 0.75,
                "heat_tax_threshold": 0.3,
                "tuning_degree_min": 0.6,
                "meaning_flux_target": 5e6,
            },
            "manufacturing": {
                "name": "制造业",
                "resilience_target": 0.5,
                "heat_tax_threshold": 0.5,
                "tuning_degree_min": 0.4,
                "meaning_flux_target": 2e6,
            },
            "finance": {
                "name": "金融",
                "resilience_target": 0.8,
                "heat_tax_threshold": 0.25,
                "tuning_degree_min": 0.7,
                "meaning_flux_target": 1e7,
            },
            "healthcare": {
                "name": "医疗",
                "resilience_target": 0.7,
                "heat_tax_threshold": 0.35,
                "tuning_degree_min": 0.6,
                "meaning_flux_target": 3e6,
            },
        }
        return self.benchmarks
    
    def create_interactive_config(self, industry_type):
        """创建交互式配置"""
        if industry_type not in self.benchmarks:
            return {"error": f"Unknown industry: {industry_type}"}
        
        benchmark = self.benchmarks[industry_type]
        
        config = {
            "industry": industry_type,
            "benchmark": benchmark,
            "scan_parameters": {
                "depth": "standard",  # standard/deep/quick
                "focus_areas": ["resilience", "heat_tax", "tuning"],
                "comparison_mode": True,
            },
            "report_format": {
                "include_charts": True,
                "include_recommendations": True,
                "output_format": "markdown",  # markdown/json/html
            },
            "thresholds": {
                "critical": benchmark["resilience_target"] * 0.5,
                "warning": benchmark["resilience_target"] * 0.75,
                "good": benchmark["resilience_target"],
            }
        }
        
        self.config = config
        return config
    
    def save_config(self, output_file="industry_config.json"):
        """保存配置到文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "benchmarks": self.benchmarks,
                "last_config": self.config,
                "created_at": datetime.now().isoformat(),
            }, f, indent=2, ensure_ascii=False)
        return output_file


if __name__ == "__main__":
    cfg = IndustryBenchmarkConfig()
    
    # 5c: 加载行业基准
    benchmarks = cfg.load_default_benchmarks()
    print(f"[5c] Loaded {len(benchmarks)} industry benchmarks")
    
    # 5d: 创建交互式配置
    for industry in benchmarks:
        config = cfg.create_interactive_config(industry)
        print(f"[5d] Created config for {industry}: {config['benchmark']['name']}")
    
    # 保存
    output = cfg.save_config("C:\\MSS-AI-Project\\industry_config.json")
    print(f"\n[SAVE] Config saved to: {output}")
