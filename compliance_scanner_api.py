"""
MSS Compliance Scanner - API Version
Text compliance analysis API service
"""

import json
import re
from typing import Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

class ComplianceAnalyzer:
    """Text compliance analyzer"""

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict]:
        """Load compliance rules"""
        return [
            {
                "id": "RULE-001",
                "name": "绝对化表述检测",
                "pattern": r"(100%|绝对|永远|终极|完美|不可|必然|一定)",
                "severity": "high",
                "category": "绝对化",
                "description": "检测文本中的绝对化表述"
            },
            {
                "id": "RULE-002",
                "name": "层级混淆检测",
                "pattern": r"(L1.*L3|L3.*L1|硬核.*试探|试探.*硬核)",
                "severity": "medium",
                "category": "层级混淆",
                "description": "检测不同层级概念的混用"
            },
            {
                "id": "RULE-003",
                "name": "热税违规检测",
                "pattern": r"(零热税|无热税|热税为零)",
                "severity": "high",
                "category": "热税违规",
                "description": "检测违反热税定律的表述"
            },
            {
                "id": "RULE-004",
                "name": "K3术语污染",
                "pattern": r"(暗物质|暗能量|量子纠缠.*意识|相对论.*意义)",
                "severity": "medium",
                "category": "K3污染",
                "description": "检测K3物理术语的误用"
            },
            {
                "id": "RULE-005",
                "name": "逻辑矛盾检测",
                "pattern": r"(既是.*又不是|同时.*又不|矛盾.*统一)",
                "severity": "low",
                "category": "逻辑矛盾",
                "description": "检测明显的逻辑矛盾表述"
            }
        ]

    def analyze(self, text: str, options: Optional[Dict] = None) -> Dict:
        """
        Analyze text for compliance issues

        Returns:
            Analysis report with scores and violations
        """
        violations = []
        scores = {
            "cleanliness": 1.0,
            "layer_integrity": 1.0,
            "heat_tax_compliance": 1.0,
            "k3_isolation": 1.0
        }

        for rule in self.rules:
            matches = list(re.finditer(rule["pattern"], text, re.IGNORECASE))

            for match in matches:
                violation = {
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "category": rule["category"],
                    "severity": rule["severity"],
                    "position": match.start(),
                    "matched_text": match.group(),
                    "description": rule["description"]
                }
                violations.append(violation)

                # Update scores
                if rule["severity"] == "high":
                    penalty = 0.2
                elif rule["severity"] == "medium":
                    penalty = 0.1
                else:
                    penalty = 0.05

                if rule["category"] == "绝对化":
                    scores["cleanliness"] -= penalty
                elif rule["category"] == "层级混淆":
                    scores["layer_integrity"] -= penalty
                elif rule["category"] == "热税违规":
                    scores["heat_tax_compliance"] -= penalty
                elif rule["category"] == "K3污染":
                    scores["k3_isolation"] -= penalty

        # Clamp scores to [0, 1]
        for key in scores:
            scores[key] = max(0, min(1, scores[key]))

        # Calculate overall score
        overall = sum(scores.values()) / len(scores)

        # Determine grade
        if overall >= 0.9:
            grade = "A"
            status = "合规"
        elif overall >= 0.7:
            grade = "B"
            status = "基本合规"
        elif overall >= 0.5:
            grade = "C"
            status = "需要改进"
        else:
            grade = "D"
            status = "严重违规"

        return {
            "status": "success",
            "text_length": len(text),
            "violation_count": len(violations),
            "violations": violations,
            "scores": {k: round(v, 3) for k, v in scores.items()},
            "overall_score": round(overall, 3),
            "grade": grade,
            "compliance_status": status
        }

    def batch_analyze(self, texts: List[str]) -> List[Dict]:
        """Analyze multiple texts"""
        return [self.analyze(text) for text in texts]

# Create global analyzer
analyzer = ComplianceAnalyzer()

class ComplianceHandler(BaseHTTPRequestHandler):
    """HTTP handler for compliance API"""

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

        if path == "/analyze":
            text = data.get("text", "")
            if text:
                result = analyzer.analyze(text)
                self._send_json(result)
            else:
                self._send_json({"error": "Missing text"}, 400)

        elif path == "/batch":
            texts = data.get("texts", [])
            if texts:
                results = analyzer.batch_analyze(texts)
                self._send_json({"results": results})
            else:
                self._send_json({"error": "Missing texts"}, 400)

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self._send_json({"status": "healthy", "service": "compliance-scanner"})

        elif path == "/rules":
            self._send_json({"rules": analyzer.rules})

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def start_compliance_server(host="localhost", port=8850):
    """Start compliance API server"""
    server = HTTPServer((host, port), ComplianceHandler)
    print(f"MSS Compliance Scanner API")
    print(f"Running at http://{host}:{port}")
    print(f"Endpoints:")
    print(f"  GET  /health    - Health check")
    print(f"  GET  /rules     - List rules")
    print(f"  POST /analyze   - Analyze text")
    print(f"  POST /batch     - Batch analyze")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    start_compliance_server()
