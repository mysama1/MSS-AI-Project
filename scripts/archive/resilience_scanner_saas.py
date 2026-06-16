"""
MSS Resilience Scanner - SaaS Version
Web service for organizational resilience assessment
"""

import json
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import os

class ResilienceScannerSaaS:
    """SaaS version of resilience scanner"""

    def __init__(self):
        self.scan_history = []
        self.templates = self._load_templates()

    def _load_templates(self):
        """Load industry benchmark templates"""
        return {
            "tech_startup": {
                "name": "科技初创企业",
                "benchmarks": {"M": 0.65, "O_d": 0.75, "Φ": 80, "γ": 0.25}
            },
            "tech_enterprise": {
                "name": "科技成熟企业",
                "benchmarks": {"M": 0.80, "O_d": 0.85, "Φ": 120, "γ": 0.20}
            },
            "manufacturing": {
                "name": "制造业",
                "benchmarks": {"M": 0.55, "O_d": 0.70, "Φ": 60, "γ": 0.30}
            },
            "finance": {
                "name": "金融业",
                "benchmarks": {"M": 0.75, "O_d": 0.80, "Φ": 100, "γ": 0.22}
            },
            "healthcare": {
                "name": "医疗健康",
                "benchmarks": {"M": 0.70, "O_d": 0.78, "Φ": 90, "γ": 0.24}
            }
        }

    def scan(self, org_data: dict, industry: str = "tech_startup") -> dict:
        """
        Perform resilience scan on organization

        Args:
            org_data: Organization structure and metrics
            industry: Industry template to compare against

        Returns:
            Scan results with scores and recommendations
        """
        start_time = time.time()

        # Calculate metrics
        metrics = self._calculate_metrics(org_data)

        # Compare with benchmark
        benchmark = self.templates.get(industry, self.templates["tech_startup"])
        comparison = self._compare_with_benchmark(metrics, benchmark)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, comparison)

        # Create report
        report = {
            "scan_id": f"SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "industry": industry,
            "industry_name": benchmark["name"],
            "metrics": metrics,
            "benchmark_comparison": comparison,
            "recommendations": recommendations,
            "overall_score": self._calculate_overall_score(metrics),
            "risk_level": self._determine_risk_level(metrics),
            "execution_time_ms": round((time.time() - start_time) * 1000, 2)
        }

        self.scan_history.append(report)
        return report

    def _calculate_metrics(self, org_data: dict) -> dict:
        """Calculate resilience metrics from organization data"""
        # Simplified calculation
        departments = org_data.get("departments", [])

        if not departments:
            return {"M": 0, "O_d": 0, "Φ": 0, "γ": 0}

        # Average department metrics
        total_M = sum(d.get("M", 0) for d in departments) / len(departments)
        total_Od = sum(d.get("O_d", 0) for d in departments) / len(departments)
        total_Phi = sum(d.get("Φ", 0) for d in departments) / len(departments)
        total_gamma = sum(d.get("γ", 0) for d in departments) / len(departments)

        return {
            "M": round(total_M, 4),
            "O_d": round(total_Od, 4),
            "Φ": round(total_Phi, 2),
            "γ": round(total_gamma, 4)
        }

    def _compare_with_benchmark(self, metrics: dict, benchmark: dict) -> dict:
        """Compare metrics with industry benchmark"""
        bm = benchmark["benchmarks"]

        return {
            "M": {
                "value": metrics["M"],
                "benchmark": bm["M"],
                "diff": round(metrics["M"] - bm["M"], 4),
                "status": "above" if metrics["M"] >= bm["M"] else "below"
            },
            "O_d": {
                "value": metrics["O_d"],
                "benchmark": bm["O_d"],
                "diff": round(metrics["O_d"] - bm["O_d"], 4),
                "status": "above" if metrics["O_d"] >= bm["O_d"] else "below"
            },
            "Φ": {
                "value": metrics["Φ"],
                "benchmark": bm["Φ"],
                "diff": round(metrics["Φ"] - bm["Φ"], 2),
                "status": "above" if metrics["Φ"] >= bm["Φ"] else "below"
            },
            "γ": {
                "value": metrics["γ"],
                "benchmark": bm["γ"],
                "diff": round(metrics["γ"] - bm["γ"], 4),
                "status": "above" if metrics["γ"] <= bm["γ"] else "below"  # Lower is better
            }
        }

    def _generate_recommendations(self, metrics: dict, comparison: dict) -> list:
        """Generate improvement recommendations"""
        recommendations = []

        if comparison["M"]["status"] == "below":
            recommendations.append({
                "priority": "high",
                "area": "组织韧性(M)",
                "issue": f"低于行业基准 {abs(comparison['M']['diff']):.2%}",
                "action": "建立冗余机制，优化决策流程，增强抗冲击能力"
            })

        if comparison["O_d"]["status"] == "below":
            recommendations.append({
                "priority": "high",
                "area": "规范场强(O_d)",
                "issue": f"低于行业基准 {abs(comparison['O_d']['diff']):.2%}",
                "action": "强化规章制度执行，减少熵增，提升组织秩序度"
            })

        if comparison["γ"]["status"] == "below":
            recommendations.append({
                "priority": "medium",
                "area": "热税效率(γ)",
                "issue": f"高于行业基准 {abs(comparison['γ']['diff']):.4f}",
                "action": "优化资源分配，减少意义损耗，提升转化效率"
            })

        if not recommendations:
            recommendations.append({
                "priority": "low",
                "area": "整体",
                "issue": "所有指标均优于行业基准",
                "action": "保持当前状态，关注潜在风险"
            })

        return recommendations

    def _calculate_overall_score(self, metrics: dict) -> float:
        """Calculate overall resilience score"""
        # Weighted average
        M_weight = 0.4
        Od_weight = 0.3
        Phi_weight = 0.2
        gamma_weight = 0.1

        # Normalize gamma (lower is better, max 1.0)
        gamma_score = max(0, 1.0 - metrics["γ"])

        score = (
            metrics["M"] * M_weight +
            metrics["O_d"] * Od_weight +
            min(metrics["Φ"] / 150, 1.0) * Phi_weight +
            gamma_score * gamma_weight
        )

        return round(score, 3)

    def _determine_risk_level(self, metrics: dict) -> str:
        """Determine risk level"""
        if metrics["M"] < 0.3:
            return "CRITICAL"
        elif metrics["M"] < 0.5:
            return "HIGH"
        elif metrics["M"] < 0.7:
            return "MEDIUM"
        else:
            return "LOW"

    def get_scan_history(self, limit: int = 10) -> list:
        """Get scan history"""
        return self.scan_history[-limit:]

    def export_report(self, scan_id: str, format: str = "json") -> dict:
        """Export scan report"""
        for scan in self.scan_history:
            if scan["scan_id"] == scan_id:
                if format == "json":
                    return scan
                elif format == "markdown":
                    return self._to_markdown(scan)

        return {"error": "Scan not found"}

    def _to_markdown(self, report: dict) -> str:
        """Convert report to markdown format"""
        md = f"""# 组织韧性扫描报告

**扫描ID**: {report['scan_id']}
**时间**: {report['timestamp']}
**行业**: {report['industry_name']}
**风险等级**: {report['risk_level']}
**综合评分**: {report['overall_score']}

## 核心指标

| 指标 | 当前值 | 行业基准 | 差异 | 状态 |
|------|:--:|:--:|:--:|:--:|
| M (韧性指数) | {report['metrics']['M']:.4f} | {report['benchmark_comparison']['M']['benchmark']:.4f} | {report['benchmark_comparison']['M']['diff']:+.4f} | {'✅' if report['benchmark_comparison']['M']['status'] == 'above' else '⚠️'} |
| O_d (规范场强) | {report['metrics']['O_d']:.4f} | {report['benchmark_comparison']['O_d']['benchmark']:.4f} | {report['benchmark_comparison']['O_d']['diff']:+.4f} | {'✅' if report['benchmark_comparison']['O_d']['status'] == 'above' else '⚠️'} |
| Φ (意义势能) | {report['metrics']['Φ']:.2f} | {report['benchmark_comparison']['Φ']['benchmark']:.2f} | {report['benchmark_comparison']['Φ']['diff']:+.2f} | {'✅' if report['benchmark_comparison']['Φ']['status'] == 'above' else '⚠️'} |
| γ (热税率) | {report['metrics']['γ']:.4f} | {report['benchmark_comparison']['γ']['benchmark']:.4f} | {report['benchmark_comparison']['γ']['diff']:+.4f} | {'✅' if report['benchmark_comparison']['γ']['status'] == 'above' else '⚠️'} |

## 改进建议

"""
        for i, rec in enumerate(report['recommendations'], 1):
            md += f"""### {i}. {rec['area']} (优先级: {rec['priority']})

- **问题**: {rec['issue']}
- **建议**: {rec['action']}

"""

        md += f"""
---
*报告生成时间: {report['execution_time_ms']}ms*
"""

        return {"markdown": md}

# Create global scanner instance
scanner = ResilienceScannerSaaS()

class SaaSHandler(BaseHTTPRequestHandler):
    """HTTP handler for SaaS API"""

    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        if path == "/scan":
            org_data = data.get("organization", {})
            industry = data.get("industry", "tech_startup")
            result = scanner.scan(org_data, industry)
            self._send_json(result)

        elif path == "/export":
            scan_id = data.get("scan_id", "")
            format = data.get("format", "json")
            result = scanner.export_report(scan_id, format)
            self._send_json(result)

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self._send_json({"status": "healthy", "service": "resilience-scanner-saas"})

        elif path == "/history":
            limit = int(parse_qs(parsed.query).get("limit", [10])[0])
            result = scanner.get_scan_history(limit)
            self._send_json({"scans": result})

        elif path == "/templates":
            self._send_json({"templates": scanner.templates})

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def start_saas_server(host="localhost", port=8849):
    """Start SaaS server"""
    server = HTTPServer((host, port), SaaSHandler)
    print(f"MSS Resilience Scanner SaaS")
    print(f"Running at http://{host}:{port}")
    print(f"Endpoints:")
    print(f"  GET  /health      - Health check")
    print(f"  GET  /history     - Scan history")
    print(f"  GET  /templates   - Industry templates")
    print(f"  POST /scan        - Perform scan")
    print(f"  POST /export      - Export report")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    start_saas_server()
