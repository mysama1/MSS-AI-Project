"""
MSS Health Dashboard v1.0 — Sprint 4.2

轻量级可观测面板: 读取 OTLP export + delta history + tax state → 单一健康分.

用法:
    python -m mssclaw.core.dashboard         # 终端输出
    python -m mssclaw.core.dashboard --web   # 启动本地 Web 面板
    python -m mssclaw.core.dashboard --json  # JSON 输出 (for CI)
"""
import json
import os
import sys
import time
import glob
from pathlib import Path
from typing import Optional

# ── Data Sources ──────────────────────

OTEL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "otel_export"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def read_otel_spans() -> list:
    """读取最近 OTLP export 文件."""
    if not OTEL_DIR.exists():
        return []
    files = sorted(glob.glob(str(OTEL_DIR / "spans_*.json")), reverse=True)
    spans = []
    for f in files[:5]:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    spans.extend(data)
        except Exception:
            pass
    return spans


def read_delta_history() -> list:
    """从 delta_history.json 读取."""
    path = DATA_DIR / "delta_history.json"
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def compute_health_score(otel_spans: list, delta_hist: list) -> dict:
    """综合健康评分."""
    score = 100.0

    # 1. Error spans
    errors = [s for s in otel_spans if s.get("status", {}).get("code") == "ERROR"]
    error_rate = len(errors) / max(len(otel_spans), 1)
    score -= error_rate * 40

    # 2. Latency outliers (>5s)
    slow = [s for s in otel_spans if s.get("duration_ms", 0) > 5000]
    slow_rate = len(slow) / max(len(otel_spans), 1)
    score -= slow_rate * 20

    # 3. Delta trend (declining = worse health)
    delta_trend = 0.0
    if len(delta_hist) >= 5:
        recent = [h.get("delta", h.get("current_delta", 0.5))
                  for h in delta_hist[-10:] if isinstance(h, dict)]
        if len(recent) >= 5:
            slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
            delta_trend = slope
            if slope < 0:
                score += slope * 100  # declining delta = penalty

    # 4. Molting alerts
    molt_count = sum(1 for h in delta_hist if h.get("molting_alert", False))
    score -= molt_count * 5

    return {
        "health_score": max(0, min(100, round(score, 1))),
        "total_spans": len(otel_spans),
        "error_spans": len(errors),
        "slow_spans": len(slow),
        "delta_trend": round(delta_trend, 4),
        "molting_alerts": molt_count,
        "grade": _grade(score),
    }


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


def get_quick_health() -> dict:
    """快速健康检查 (可导入)."""
    spans = read_otel_spans()
    delta = read_delta_history()
    return compute_health_score(spans, delta)


# ── Terminal Output ──────────────────

def terminal_report():
    """彩色终端输出."""
    spans = read_otel_spans()
    delta = read_delta_history()
    health = compute_health_score(spans, delta)

    print()
    print("╔══════════════════════════════════════════╗")
    print("║       MSS Health Dashboard v1.0           ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Health Score: {health['health_score']:5.1f} / 100    Grade: {health['grade']}     ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  OTLP Spans:  {health['total_spans']:>5} total               ║")
    print(f"║  Errors:      {health['error_spans']:>5} ({health['error_spans']/max(health['total_spans'],1)*100:.1f}%)             ║")
    print(f"║  Slow (>5s):  {health['slow_spans']:>5} ({health['slow_spans']/max(health['total_spans'],1)*100:.1f}%)             ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Delta Trend: {health['delta_trend']:+.4f}                       ║")
    print(f"║  Molt Alerts: {health['molting_alerts']:>5}                      ║")
    print("╚══════════════════════════════════════════╝")
    print()


# ── Web Dashboard ─────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MSS Health Dashboard</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background:#0d1117; color:#c9d1d9; padding:20px; }
  .card { background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px; margin-bottom:16px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:12px; }
  .metric { text-align:center; }
  .metric .value { font-size:2em; font-weight:bold; }
  .metric .label { font-size:0.8em; color:#8b949e; }
  .grade { display:inline-block; padding:4px 12px; border-radius:4px; font-weight:bold; }
  .grade-A { background:#238636; color:#fff; }
  .grade-B { background:#1f6feb; color:#fff; }
  .grade-C { background:#d29922; color:#000; }
  .grade-D { background:#da3633; color:#fff; }
  .grade-F { background:#8b0000; color:#fff; }
  table { width:100%; border-collapse:collapse; }
  th, td { padding:8px 12px; text-align:left; border-bottom:1px solid #30363d; }
  th { color:#8b949e; font-weight:600; }
  .bar { height:8px; background:#30363d; border-radius:4px; overflow:hidden; }
  .bar-fill { height:100%; border-radius:4px; transition:width 0.5s; }
  .good { background:#238636; } .warn { background:#d29922; } .bad { background:#da3633; }
  .refresh { position:fixed; top:16px; right:16px; background:#238636; color:#fff; border:none; padding:8px 16px; border-radius:4px; cursor:pointer; }
</style>
</head>
<body>
<div class="card">
  <h1>MSS Health Dashboard</h1>
  <button class="refresh" onclick="location.reload()">Refresh</button>
</div>
<div class="grid" id="metrics"></div>
<div class="card">
  <h3>Recent Spans</h3>
  <table id="spans"><thead><tr><th>Name</th><th>Duration</th><th>Status</th></tr></thead><tbody></tbody></table>
</div>
<script>
const DATA = DATA_PLACEHOLDER;
document.getElementById('metrics').innerHTML = [
  {label:'Health Score', value:DATA.health_score + '/100', cls:'grade-' + (DATA.health_score>=90?'A':DATA.health_score>=75?'B':DATA.health_score>=60?'C':'D')},
  {label:'Total Spans', value:DATA.total_spans},
  {label:'Errors', value:DATA.error_spans, cls:DATA.error_spans>0?'bad':''},
  {label:'Slow (>5s)', value:DATA.slow_spans, cls:DATA.slow_spans>0?'warn':''},
  {label:'Delta Trend', value:DATA.delta_trend.toFixed(4)},
  {label:'Molting Alerts', value:DATA.molting_alerts, cls:DATA.molting_alerts>0?'bad':''},
].map(function(m){return '<div class="card metric"><div class="value '+(m.cls||'')+'">'+m.value+'</div><div class="label">'+m.label+'</div></div>'}).join('');

(function(){
var tbody = '';
DATA.recent_spans.slice(0,20).forEach(function(s){
  tbody += '<tr><td>'+s.name+'</td><td>'+(s.duration_ms||0)+'ms</td><td style="color:'+(s.status==='ERROR'?'#da3633':'#238636')+'">'+(s.status||'OK')+'</td></tr>';
});
document.querySelector('#spans tbody').innerHTML = tbody;
})();
</script>
</body>
</html>"""


def web_dashboard():
    """生成并打开 Web 面板."""
    spans = read_otel_spans()
    delta = read_delta_history()
    health = compute_health_score(spans, delta)

    recent = [{
        "name": s.get("name", "unknown"),
        "duration_ms": s.get("duration_ms", 0),
        "status": s.get("status", {}).get("code", "OK"),
    } for s in spans[:20]]

    data = {**health, "recent_spans": recent}
    html = DASHBOARD_HTML.replace("DATA_PLACEHOLDER", json.dumps(data))

    out_path = DATA_DIR / "dashboard.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard written to: {out_path}")
    try:
        os.startfile(str(out_path))
    except Exception:
        print(f"Open manually: {out_path}")


# ── CLI Entry ─────────────────────────

if __name__ == "__main__":
    if "--web" in sys.argv:
        web_dashboard()
    elif "--json" in sys.argv:
        print(json.dumps(get_quick_health(), indent=2))
    else:
        terminal_report()
