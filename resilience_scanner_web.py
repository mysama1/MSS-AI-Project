"""
MSS Resilience Scanner - Web Interface
Simple HTML interface for resilience scanning
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from resilience_scanner_saas import ResilienceScannerSaaS

# Create global scanner
scanner = ResilienceScannerSaaS()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>MSS Resilience Scanner</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 8px; border: 1px solid #ddd; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 5px; }
        .grade-A { color: green; }
        .grade-B { color: blue; }
        .grade-C { color: orange; }
        .grade-D { color: red; }
    </style>
</head>
<body>
    <h1>🔍 MSS Resilience Scanner</h1>
    <p>Organizational Resilience Assessment Tool</p>
    
    <form id="scanForm">
        <div class="form-group">
            <label>Organization Name:</label>
            <input type="text" id="orgName" value="Test Organization">
        </div>
        
        <div class="form-group">
            <label>Industry:</label>
            <select id="industry">
                <option value="tech_startup">Tech Startup</option>
                <option value="tech_enterprise">Tech Enterprise</option>
                <option value="manufacturing">Manufacturing</option>
                <option value="finance">Finance</option>
                <option value="healthcare">Healthcare</option>
            </select>
        </div>
        
        <div class="form-group">
            <label>Departments (JSON):</label>
            <textarea id="departments" rows="10">
[
    {"name": "R&D", "M": 0.85, "O_d": 0.90, "Φ": 120, "γ": 0.15},
    {"name": "Marketing", "M": 0.65, "O_d": 0.70, "Φ": 80, "γ": 0.25},
    {"name": "Operations", "M": 0.55, "O_d": 0.60, "Φ": 60, "γ": 0.35},
    {"name": "Finance", "M": 0.75, "O_d": 0.80, "Φ": 100, "γ": 0.20},
    {"name": "HR", "M": 0.60, "O_d": 0.65, "Φ": 70, "γ": 0.30}
]
            </textarea>
        </div>
        
        <button type="submit">Run Scan</button>
    </form>
    
    <div id="result"></div>
    
    <script>
        document.getElementById('scanForm').onsubmit = async function(e) {
            e.preventDefault();
            
            const orgData = {
                name: document.getElementById('orgName').value,
                departments: JSON.parse(document.getElementById('departments').value)
            };
            
            const industry = document.getElementById('industry').value;
            
            try {
                const response = await fetch('/api/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({organization: orgData, industry: industry})
                });
                
                const result = await response.json();
                displayResult(result);
            } catch (error) {
                document.getElementById('result').innerHTML = '<p style="color:red">Error: ' + error.message + '</p>';
            }
        };
        
        function displayResult(result) {
            const gradeClass = 'grade-' + result.grade;
            
            let html = '<div class="result">';
            html += '<h2>Scan Results</h2>';
            html += '<p><strong>Scan ID:</strong> ' + result.scan_id + '</p>';
            html += '<p><strong>Risk Level:</strong> ' + result.risk_level + '</p>';
            html += '<p><strong>Overall Score:</strong> <span class="' + gradeClass + '">' + result.overall_score + ' (' + result.grade + ')</span></p>';
            
            html += '<h3>Metrics</h3>';
            html += '<div class="metric">M (Resilience): ' + result.metrics.M + '</div>';
            html += '<div class="metric">O_d (Order): ' + result.metrics.O_d + '</div>';
            html += '<div class="metric">Φ (Potential): ' + result.metrics.Φ + '</div>';
            html += '<div class="metric">γ (Heat Tax): ' + result.metrics.γ + '</div>';
            
            html += '<h3>Recommendations</h3>';
            html += '<ul>';
            result.recommendations.forEach(function(rec) {
                html += '<li><strong>' + rec.area + ':</strong> ' + rec.action + '</li>';
            });
            html += '</ul>';
            
            html += '</div>';
            
            document.getElementById('result').innerHTML = html;
        }
    </script>
</body>
</html>
"""

class WebHandler(BaseHTTPRequestHandler):
    """HTTP handler with web interface"""
    
    def log_message(self, format, *args):
        pass
    
    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _send_html(self, html, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/" or path == "/index.html":
            self._send_html(HTML_TEMPLATE)
        
        elif path == "/health":
            self._send_json({"status": "healthy", "service": "resilience-scanner-web"})
        
        else:
            self._send_json({"error": "Not found"}, 404)
    
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
        
        if path == "/api/scan":
            org_data = data.get("organization", {})
            industry = data.get("industry", "tech_startup")
            result = scanner.scan(org_data, industry)
            self._send_json(result)
        
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def start_web_server(host="localhost", port=8852):
    """Start web server with HTML interface"""
    server = HTTPServer((host, port), WebHandler)
    print(f"MSS Resilience Scanner - Web Interface")
    print(f"Running at http://{host}:{port}")
    print(f"Open your browser and navigate to the URL above")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    start_web_server()
