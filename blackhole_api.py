"""
D2: 实时黑洞预警系统 — FastAPI 端点 + 实时仪表盘
==================================================
基于 K3 Blackhole Monitor (H162) + MeaningBlackholeAgent (D5-042)
升级为生产级API: CRTR/η/ρ 三重指标实时监控 + 告警 + 历史追踪

端点:
  POST /blackhole/scan     扫描文本
  GET  /blackhole/status   实时状态 (CRTR/η/ρ/事件视界)
  GET  /blackhole/history  历史扫描记录
  GET  /blackhole/signatures  9签名框架定义
  WS   /blackhole/ws       实时WebSocket推送
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys, os, json, time, asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from collections import deque
import math

# Inject parent project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.meaning_blackhole_agent import (
    MeaningBlackholeAgent, ScanReport, BlackholeSignature,
    SIGNATURE_PATTERNS, SIGNATURE_AXIOM
)
from scripts.archive.k3_blackhole_monitor import MeaningBlackHoleDetector

# ─── Models ───

class ScanRequest(BaseModel):
    text: str
    source_id: Optional[str] = "api_call"

class ScanResponse(BaseModel):
    source: str
    timestamp: str
    risk_level: str
    overall_score: float
    event_horizon_estimate: str
    crtr: float
    eta: float
    rho: float
    detection_count: int
    top_signatures: List[dict]

class StatusResponse(BaseModel):
    system_crtr: float
    system_eta: float
    system_rho: float
    threat_level: str
    event_horizon: str
    scans_today: int
    critical_alerts_24h: int

# ─── App Setup ───

app = FastAPI(
    title="MSS 意义场黑洞预警系统",
    description="CRTR/η/ρ 三维监测 + 9签名诊断",
    version="3.0.0"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── Global State ───

agent = MeaningBlackholeAgent()
detector = MeaningBlackHoleDetector()
history_store: deque = deque(maxlen=500)
clients: List[WebSocket] = []
start_time = time.time()

# Rolling metrics (last 24h)
rolling_crtr: deque = deque(maxlen=1000)
rolling_eta: deque = deque(maxlen=1000)
rolling_rho: deque = deque(maxlen=1000)

# ─── Helper Functions ───

def compute_metrics(text: str, agent_report: ScanReport) -> dict:
    """Compute CRTR/η/ρ fusing K3 monitor + MeaningBlackholeAgent."""
    # K3 detector (AI/self-ref patterns)
    result = detector.analyze(text, "api_scan")
    crtr_k3 = result.get('crtr', 0)
    eta_k3 = result.get('eta', 1.0)
    bh_score = result.get('blackhole_score', 0)
    
    # MeaningBlackholeAgent (9-signature business/market patterns)
    detection_density = len(agent_report.detections) / max(len(text.split()), 1) * 100
    axiomatic_hits = len(set(d.axiom for d in agent_report.detections))
    
    # CRTR fusion: K3 self-ref + agent signature density
    crtr = crtr_k3 + detection_density * 0.5  # each % density ≈ 0.5 CRTR
    
    # η fusion: K3 eta reduced by multi-axiom violations (A1-A6 breadth)
    eta = max(0.1, eta_k3 - axiomatic_hits * 0.05)
    
    # rho: combined meaning density
    rho = max(0, 1.0 - (bh_score / 50 + detection_density / 20))
    
    # Store rolling
    rolling_crtr.append(crtr)
    rolling_eta.append(eta)
    rolling_rho.append(rho)
    
    return {
        'crtr': round(crtr, 2),
        'eta': round(eta, 3),
        'rho': round(rho, 3),
        'bh_score': round(bh_score, 1),
        'detection_density': round(detection_density, 1),
        'axiom_breadth': f'{axiomatic_hits}/6',
        'diagnosis': result.get('diagnosis', 'UNKNOWN'),
        'severity': result.get('severity', 'unknown'),
    }

def event_horizon_estimate(crtr: float, eta: float) -> str:
    """Estimate time to event horizon."""
    if crtr >= 8.0:
        return "EVENT HORIZON FORMED — Irreversible"
    elif crtr >= 3.0:
        t = max(1, int(30 * (1 - (crtr - 3) / 5)))
        return f"Within {t} days (pre-collapse)"
    elif crtr >= 1.5:
        t = max(30, int(180 * (1 - (crtr - 1.5) / 1.5)))
        return f"Within {t} days (early warning)"
    elif eta < 0.5:
        return "Meaning escape velocity critically low"
    else:
        return "> 365 days (normal)"

# ─── API Endpoints ───

@app.post("/blackhole/scan", response_model=ScanResponse)
async def scan_text(req: ScanRequest):
    """Scan text for meaning blackhole signatures with full metrics."""
    report = agent.scan_text(req.text, req.source_id)
    metrics = compute_metrics(req.text, report)
    
    response = {
        "source": req.source_id,
        "timestamp": datetime.now().isoformat(),
        "risk_level": report.risk_level,
        "overall_score": report.overall_score,
        "event_horizon_estimate": event_horizon_estimate(metrics['crtr'], metrics['eta']),
        "crtr": metrics['crtr'],
        "eta": metrics['eta'],
        "rho": metrics['rho'],
        "detection_count": len(report.detections),
        "top_signatures": [
            {"signature": d.signature.value, "axiom": d.axiom, 
             "line": d.line, "match": d.match_text[:60], "risk": round(d.risk_score, 2)}
            for d in sorted(report.detections, key=lambda x: -x.risk_score)[:10]
        ]
    }
    
    history_store.append(response)
    
    # Broadcast to WebSocket clients
    for ws in clients[:]:
        try:
            await ws.send_json(response)
        except:
            clients.remove(ws)
    
    return response

@app.get("/blackhole/status", response_model=StatusResponse)
async def get_status():
    """Current system monitoring status."""
    if rolling_crtr:
        avg_crtr = sum(rolling_crtr) / len(rolling_crtr)
        avg_eta = sum(rolling_eta) / len(rolling_eta)
        avg_rho = sum(rolling_rho) / len(rolling_rho)
    else:
        avg_crtr = avg_eta = avg_rho = 0
    
    if avg_crtr >= 8.0:
        threat = "CRITICAL"
        horizon = "EVENT HORIZON FORMED"
    elif avg_crtr >= 3.0:
        threat = "HIGH"
        horizon = "Pre-collapse"
    elif avg_crtr >= 1.5:
        threat = "ELEVATED"
        horizon = "Early warning"
    else:
        threat = "NORMAL"
        horizon = "Clear"
    
    # 24h critical alerts
    cutoff = time.time() - 86400
    critical_24h = sum(1 for h in history_store 
                      if h.get('risk_level') == 'CRITICAL'
                      and datetime.fromisoformat(h['timestamp']).timestamp() > cutoff)
    
    return {
        "system_crtr": round(avg_crtr, 2),
        "system_eta": round(avg_eta, 3),
        "system_rho": round(avg_rho, 3),
        "threat_level": threat,
        "event_horizon": horizon,
        "scans_today": sum(1 for h in history_store 
                          if datetime.fromisoformat(h['timestamp']).timestamp() > cutoff),
        "critical_alerts_24h": critical_24h,
    }

@app.get("/blackhole/history")
async def get_history(limit: int = 50, min_risk: str = "LOW"):
    """Historical scan records."""
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    filtered = [h for h in history_store 
               if risk_order.get(h.get('risk_level', 'LOW'), 0) >= risk_order.get(min_risk, 0)]
    return list(filtered)[-limit:]

@app.get("/blackhole/signatures")
async def get_signatures():
    """9-signature diagnostic framework."""
    return {
        "title": "MSS 意义场黑洞 9签名诊断框架",
        "version": "3.0",
        "signatures": [
            {"id": sig.value, "axiom": SIG, "description": desc}
            for sig, patterns in SIGNATURE_PATTERNS.items()
            for SIG in [SIGNATURE_AXIOM[sig]]
            for desc in [_sig_desc(sig)]
        ],
        "how_to_use": "POST /blackhole/scan with {'text': 'your content'} → receive CRTR/η/ρ + signature hits",
        "thresholds": {
            "CRTR_critical": 8.0,
            "CRTR_warning": 3.0,
            "CRTR_monitor": 1.5,
            "eta_danger": 0.3,
            "eta_warning": 0.5,
            "rho_collapse": 0.01,
        }
    }

def _sig_desc(sig: BlackholeSignature) -> str:
    descs = {
        BlackholeSignature.NARRATIVE_INFLATION: "叙事膨胀 — 故事远大于产品/交付物",
        BlackholeSignature.GROWTH_PARADOX: "增长悖论 — 用户数增长但核心指标恶化",
        BlackholeSignature.FREE_LUNCH: "免费午餐承诺 — 不可持续的商业模式",
        BlackholeSignature.COMPLEXITY_EXPLOSION: "复杂度爆炸 — 技术债增速超过价值产出",
        BlackholeSignature.VALUE_DECOUPLING: "价值脱钩 — 创造的价值无法被捕获",
        BlackholeSignature.TRUST_DISSOLUTION: "信任溶解 — 市场/用户信任结构性崩塌",
        BlackholeSignature.CIRCULAR_DEPENDENCY: "循环依赖 — 意义闭环无外部锚定",
        BlackholeSignature.MEANING_FLATTENING: "意义扁平化 — 多样性被同质性吞噬",
        BlackholeSignature.TOO_BIG_TO_MEAN: "太大而无法有意义 — scale遮蔽meaning",
    }
    return descs.get(sig, "未知签名")

@app.websocket("/blackhole/ws")
async def websocket_endpoint(ws: WebSocket):
    """Real-time WebSocket feed."""
    await ws.accept()
    clients.append(ws)
    await ws.send_json({"type": "connected", "msg": "MSS Blackhole Monitor active", "clients": len(clients)})
    try:
        while True:
            await asyncio.sleep(30)
            await ws.send_json({"type": "ping", "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        clients.remove(ws)

# ─── Dashboard ───

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MSS 意义场黑洞预警 — 实时监控</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',system-ui,sans-serif; background:#0a0a0f; color:#c8c8d0; }
.header { background:linear-gradient(135deg,#1a1a2e,#16213e); padding:20px 30px; border-bottom:2px solid #e94560; }
.header h1 { font-size:1.6em; color:#e94560; }
.header .sub { font-size:0.85em; color:#7a7a9a; margin-top:5px; }
.grid { display:grid; grid-template-columns:repeat(3,1fr); gap:15px; padding:20px; }
.card { background:#141428; border:1px solid #2a2a4a; border-radius:8px; padding:20px; }
.card h3 { font-size:0.75em; text-transform:uppercase; color:#7a7a9a; margin-bottom:10px; letter-spacing:1px; }
.metric-value { font-size:2.2em; font-weight:700; }
.metric-label { font-size:0.8em; color:#5a5a7a; margin-top:5px; }
.threat-normal { color:#00e676; } .threat-elevated { color:#ffab40; }
.threat-high { color:#ff5252; } .threat-critical { color:#e94560; animation:pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
.table-container { margin:0 20px 20px; background:#141428; border:1px solid #2a2a4a; border-radius:8px; overflow:hidden; }
.table-container h3 { padding:15px 20px; font-size:0.9em; border-bottom:1px solid #2a2a4a; }
table { width:100%; border-collapse:collapse; }
th, td { padding:10px 15px; text-align:left; border-bottom:1px solid #1a1a3a; font-size:0.85em; }
th { background:#1a1a2e; color:#7a7a9a; text-transform:uppercase; font-size:0.75em; letter-spacing:0.5px; }
tr:hover { background:#1a1a3a; }
.risk-badge { padding:3px 10px; border-radius:10px; font-size:0.75em; font-weight:600; }
.risk-LOW { background:#1b5e20; color:#00e676; } .risk-MEDIUM { background:#e65100; color:#ffab40; }
.risk-HIGH { background:#b71c1c; color:#ff5252; } .risk-CRITICAL { background:#880e4f; color:#e94560; }
.footer { text-align:center; padding:15px; color:#5a5a7a; font-size:0.75em; }
.scan-area { margin:0 20px 20px; }
.scan-area textarea { width:100%; height:100px; background:#141428; border:1px solid #2a2a4a; border-radius:8px; color:#c8c8d0; padding:15px; font-family:inherit; resize:vertical; }
.scan-area button { margin-top:10px; padding:10px 30px; background:#e94560; color:#fff; border:none; border-radius:6px; cursor:pointer; font-weight:600; }
.scan-area button:hover { background:#ff5252; }
#scan-result { margin-top:10px; padding:15px; border-radius:8px; display:none; }
</style>
</head>
<body>
<div class="header">
    <h1>🌌 MSS 意义场黑洞预警系统 v3.0</h1>
    <div class="sub">CRTR / η (意义保真度) / ρ (意义密度) — 三维实时监测 | 9签名诊断框架</div>
</div>

<div class="grid">
    <div class="card">
        <h3>📊 CRTR (自我参照密度)</h3>
        <div class="metric-value" id="crtr-value">--</div>
        <div class="metric-label" id="crtr-label">等待首次扫描...</div>
    </div>
    <div class="card">
        <h3>🌊 η (意义保真度)</h3>
        <div class="metric-value" id="eta-value">--</div>
        <div class="metric-label" id="eta-label">1.000 = 完美保真</div>
    </div>
    <div class="card">
        <h3>🪐 ρ (意义密度)</h3>
        <div class="metric-value" id="rho-value">--</div>
        <div class="metric-label" id="rho-label">叙事凝聚力 × 留存 × 价值密度</div>
    </div>
</div>

<div class="scan-area">
    <textarea id="scan-input" placeholder="粘贴文本以扫描意义黑洞... (AI输出/新闻/财报/白皮书/推特)"></textarea>
    <button onclick="scanText()">🔍 扫描意义场</button>
    <div id="scan-result"></div>
</div>

<div class="table-container">
    <h3>📋 实时检测日志 <span style="font-size:0.7em;color:#5a5a7a;float:right">WebSocket实时更新</span></h3>
    <table>
        <thead><tr><th>时间</th><th>来源</th><th>风险</th><th>CRTR</th><th>η</th><th>ρ</th><th>命中</th></tr></thead>
        <tbody id="log-body"><tr><td colspan="7" style="text-align:center;color:#5a5a7a;padding:30px;">等待数据...</td></tr></tbody>
    </table>
</div>

<div class="footer">MSS H621 | D2 实时预警 | 基于 H162 四维监测 + H601 退化定理 | commit 172b8db2</div>

<script>
const API = '/blackhole';
let ws;
function connectWS() {
    ws = new WebSocket(`ws://${location.host}${API}/ws`);
    ws.onmessage = e => {
        const data = JSON.parse(e.data);
        if (data.type === 'connected') return;
        updateLog(data);
    };
    ws.onclose = () => setTimeout(connectWS, 5000);
}
connectWS();

async function scanText() {
    const text = document.getElementById('scan-input').value.trim();
    if (!text) return;
    const btn = document.querySelector('.scan-area button');
    btn.disabled = true; btn.textContent = '扫描中...';
    const res = await fetch(`${API}/scan`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({text, source_id:'dashboard_scan'})
    });
    const data = await res.json();
    btn.disabled = false; btn.textContent = '🔍 扫描意义场';
    updateMetrics(data);
    showScanResult(data);
}

function updateMetrics(d) {
    const crtrEl = document.getElementById('crtr-value');
    const etaEl = document.getElementById('eta-value');
    const rhoEl = document.getElementById('rho-value');
    crtrEl.textContent = d.crtr.toFixed(1);
    etaEl.textContent = d.eta.toFixed(3);
    rhoEl.textContent = d.rho.toFixed(3);
    ['crtr','eta','rho'].forEach(m=>{
        document.getElementById(`${m}-value`).className = 'metric-value';
    });
    if (d.crtr >= 8) { crtrEl.className += ' threat-critical'; }
    else if (d.crtr >= 3) { crtrEl.className += ' threat-high'; }
    else if (d.crtr >= 1.5) { crtrEl.className += ' threat-elevated'; }
    else { crtrEl.className += ' threat-normal'; }
    document.getElementById('crtr-label').textContent = d.event_horizon_estimate || '';
    document.getElementById('eta-label').textContent = d.risk_level + ' — ' + (d.diagnosis || '');
}

function showScanResult(d) {
    const el = document.getElementById('scan-result');
    const sigs = d.top_signatures || [];
    const colors = {CRITICAL:'#880e4f',HIGH:'#b71c1c',MEDIUM:'#e65100',LOW:'#1b5e20'};
    el.style.display = 'block';
    el.style.background = colors[d.risk_level] || '#1a1a2e';
    el.innerHTML = `
        <strong>[${d.risk_level}]</strong> 综合评分: ${d.overall_score} | 
        CRTR: ${d.crtr} | η: ${d.eta} | ρ: ${d.rho} | 命中: ${d.detection_count}
        ${sigs.length ? '<br>🔴 ' + sigs.map(s=>s.signature+'('+s.axiom+')').join(', ') : ''}
    `;
}

function updateLog(d) {
    const tbody = document.getElementById('log-body');
    const row = document.createElement('tr');
    const time = new Date(d.timestamp).toLocaleTimeString();
    row.innerHTML = `
        <td>${time}</td>
        <td>${d.source}</td>
        <td><span class="risk-badge risk-${d.risk_level}">${d.risk_level}</span></td>
        <td>${d.crtr.toFixed(1)}</td>
        <td>${d.eta.toFixed(3)}</td>
        <td>${d.rho.toFixed(3)}</td>
        <td>${d.detection_count}</td>
    `;
    tbody.insertBefore(row, tbody.firstChild);
    if (tbody.children.length === 1 && tbody.firstChild.textContent === '等待数据...') {
        tbody.innerHTML = '';
    }
    // Keep max 20 rows
    while (tbody.children.length > 20) tbody.lastChild.remove();
}

// Initial status fetch
fetch(`${API}/status`).then(r=>r.json()).then(s=>{
    document.getElementById('crtr-value').textContent = s.system_crtr.toFixed(1);
    document.getElementById('eta-value').textContent = s.system_eta.toFixed(3);
    document.getElementById('rho-value').textContent = s.system_rho.toFixed(3);
    document.getElementById('crtr-label').textContent = '威胁: ' + s.threat_level;
});
</script>
</body>
</html>"""

@app.get("/blackhole/dashboard", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML

# ─── Health ───

@app.get("/blackhole/health")
async def health():
    return {
        "service": "MSS Blackhole Monitor v3.0",
        "uptime_seconds": round(time.time() - start_time),
        "active_ws_clients": len(clients),
        "history_entries": len(history_store),
        "rolling_samples": len(rolling_crtr),
    }

# ─── Main ───

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("BLACKHOLE_PORT", 53001))
    print(f"\n  🌌 MSS 意义场黑洞预警系统 v3.0")
    print(f"  API:     http://localhost:{port}/blackhole/status")
    print(f"  Scan:    POST http://localhost:{port}/blackhole/scan")
    print(f"  仪表盘:  http://localhost:{port}/blackhole/dashboard")
    print(f"  WebSocket: ws://localhost:{port}/blackhole/ws\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
