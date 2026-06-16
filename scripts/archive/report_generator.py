#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS Audit Report Generator — HTML dashboard from unified_audit output"""
import json, os
from datetime import datetime
from typing import Dict

def generate_html(report: Dict, title: str = "MSS Audit Report") -> str:
    """Generate a standalone HTML dashboard from audit report JSON."""
    
    scores = report.get("scores", {})
    composite = scores.get("composite", 0)
    tax = report.get("thermal_tax", {})
    layers = report.get("layers", {})
    violations = report.get("violations", [])
    
    # Color scheme based on score
    if composite >= 90:
        grade, color, icon = "A", "#22c55e", "✅"
    elif composite >= 75:
        grade, color, icon = "B", "#eab308", "⚠️"
    elif composite >= 50:
        grade, color, icon = "C", "#f97316", "❌"
    else:
        grade, color, icon = "D", "#ef4444", "🚫"
    
    # Severity colors
    sev_colors = {"critical": "#ef4444", "high": "#f97316", "medium": "#eab308", "low": "#6b7280"}
    
    # Layer cards
    layer_cards = ""
    for name, data in layers.items():
        vc = data["violation_count"]
        status = data["status"]
        s_color = "#22c55e" if status == "PASS" else ("#eab308" if "WARN" in status else "#ef4444")
        s_icon = "✅" if status == "PASS" else ("⚠️" if "WARN" in status else "❌")
        layer_cards += f"""
        <div class="layer-card" onclick="this.classList.toggle('expanded')">
            <div class="layer-header">
                <span class="layer-icon">{s_icon}</span>
                <span class="layer-name">{name}</span>
                <span class="layer-status" style="color:{s_color}">{status}</span>
                <span class="layer-count">{vc} violations</span>
            </div>
            <div class="layer-detail">
                {_render_layer_violations(violations, name)}
            </div>
        </div>"""
    
    # Violation rows for table
    violation_rows = ""
    for v in violations:
        sev = v.get("severity", "low")
        violation_rows += f"""
        <tr>
            <td><span class="sev-badge" style="background:{sev_colors.get(sev,'#6b7280')}">{sev.upper()}</span></td>
            <td>{v.get('layer','')}</td>
            <td><code>{v.get('check','')}</code></td>
            <td>{v.get('detail','')[:80]}</td>
        </tr>"""
    
    # Tax breakdown
    tax_rows = ""
    if "T_direct" in tax:
        tax_rows = f"""
        <div class="tax-grid">
            <div class="tax-item"><span class="tax-label">T_direct</span><span class="tax-value">{tax['T_direct']}</span></div>
            <div class="tax-item"><span class="tax-label">T_potential</span><span class="tax-value">{tax['T_potential']}</span></div>
            <div class="tax-item"><span class="tax-label">T_total</span><span class="tax-value">{tax['T_total']}</span></div>
            <div class="tax-item"><span class="tax-label">γ</span><span class="tax-value">{tax['gamma']}</span></div>
            <div class="tax-item"><span class="tax-label">η</span><span class="tax-value">{tax['efficiency']}</span></div>
            <div class="tax-item"><span class="tax-label">Diagnosis</span><span class="tax-value">{tax['diagnosis']}</span></div>
        </div>"""
    
    # Layer-specific violation lines
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; padding: 24px; }}
.container {{ max-width: 900px; margin: 0 auto; }}
.header {{ text-align: center; padding: 32px 0 24px; }}
.header h1 {{ font-size: 24px; margin-bottom: 8px; }}
.header .timestamp {{ color: #64748b; font-size: 13px; }}
.score-card {{ background: #1e293b; border-radius: 16px; padding: 32px; text-align: center; margin-bottom: 24px; border: 2px solid {color}; }}
.score-circle {{ width: 120px; height: 120px; border-radius: 50%; background: {color}; margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; font-size: 42px; font-weight: 700; color: #fff; }}
.score-grade {{ font-size: 20px; font-weight: 600; color: {color}; margin-bottom: 8px; }}
.score-label {{ color: #94a3b8; font-size: 14px; }}
.verdict {{ font-size: 15px; color: #cbd5e1; margin-top: 12px; padding: 12px 20px; background: rgba(255,255,255,0.05); border-radius: 8px; display: inline-block; }}
.layers {{ margin-bottom: 24px; }}
.layer-card {{ background: #1e293b; border-radius: 12px; margin-bottom: 8px; overflow: hidden; cursor: pointer; transition: all 0.2s; }}
.layer-card:hover {{ background: #273548; }}
.layer-header {{ padding: 14px 20px; display: flex; align-items: center; gap: 12px; }}
.layer-icon {{ font-size: 18px; }}
.layer-name {{ font-weight: 600; font-size: 14px; flex: 1; color: #e2e8f0; }}
.layer-status {{ font-weight: 600; font-size: 13px; }}
.layer-count {{ color: #64748b; font-size: 13px; }}
.layer-detail {{ display: none; padding: 0 20px 16px; color: #94a3b8; font-size: 13px; }}
.layer-card.expanded .layer-detail {{ display: block; }}
.tax-section {{ background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
.tax-section h3 {{ font-size: 15px; margin-bottom: 16px; color: #e2e8f0; }}
.tax-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
.tax-item {{ background: #0f172a; border-radius: 8px; padding: 12px; text-align: center; }}
.tax-label {{ display: block; color: #64748b; font-size: 12px; margin-bottom: 4px; }}
.tax-value {{ display: block; color: #e2e8f0; font-size: 18px; font-weight: 600; }}
.violations-section {{ background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
.violations-section h3 {{ font-size: 15px; margin-bottom: 16px; color: #e2e8f0; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 8px 12px; color: #64748b; border-bottom: 1px solid #334155; font-weight: 500; }}
td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; }}
tr:hover td {{ background: rgba(255,255,255,0.03); }}
.sev-badge {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; color: #fff; }}
.footer {{ text-align: center; padding: 24px; color: #475569; font-size: 12px; }}
code {{ background: #334155; padding: 1px 6px; border-radius: 3px; font-size: 12px; color: #e2e8f0; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{title}</h1>
        <div class="timestamp">{report.get('timestamp','')} · {report.get('elapsed_ms',0)}ms</div>
    </div>
    
    <div class="score-card">
        <div class="score-circle">{composite}</div>
        <div class="score-grade">{icon} Grade {grade} — {report.get('verdict','')}</div>
        <div class="score-label">Composite Score · {scores.get('total_violations',0)} total violations</div>
    </div>
    
    <div class="layers">
        <h3 style="margin-bottom:12px;color:#e2e8f0;font-size:15px;">Defense Layers</h3>
        {layer_cards}
    </div>
    
    <div class="tax-section">
        <h3>Thermal Tax Breakdown</h3>
        {tax_rows}
    </div>
    
    <div class="violations-section">
        <h3>Violation Details ({len(violations)})</h3>
        <table>
            <thead><tr><th>Severity</th><th>Layer</th><th>Check</th><th>Detail</th></tr></thead>
            <tbody>{violation_rows}</tbody>
        </table>
    </div>
    
    <div class="footer">
        MSS Unified Audit v{report.get('audit_version','1.0')} · Meaning Supremacy System<br>
        Generated {datetime.now().isoformat()}
    </div>
</div>
</body>
</html>"""
    return html


def _render_layer_violations(violations: list, layer_name: str) -> str:
    """Render violation lines for a specific layer."""
    layer_violations = [v for v in violations if v.get("layer") == layer_name]
    if not layer_violations:
        return '<p style="color:#64748b;font-size:12px;padding:8px 0;">No violations in this layer</p>'
    
    lines = ""
    sev_colors = {"critical": "#ef4444", "high": "#f97316", "medium": "#eab308", "low": "#6b7280"}
    for v in layer_violations:
        sev = v.get("severity", "low")
        c = sev_colors.get(sev, "#6b7280")
        lines += f'<div style="padding:4px 0;font-size:12px;">'
        lines += f'<span style="background:{c};color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;margin-right:6px;">{sev.upper()}</span>'
        lines += f'<code>{v.get("check","")}</code> {v.get("detail","")[:60]}'
        lines += f'</div>'
    return lines


def audit_to_html(output_text: str, reference: str = "", 
                  title: str = "MSS Audit Report",
                  output_path: str = None) -> str:
    """Full pipeline: audit + HTML generation.
    
    Args:
        output_text: LLM output to audit
        reference: Reference text (for context-aware V7)
        title: Report title
        output_path: If provided, save HTML to this path
    
    Returns:
        HTML string
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from unified_audit import UnifiedAudit
    
    auditor = UnifiedAudit(reference, strictness=0.7)
    report = auditor.audit(output_text)
    html = generate_html(report, title)
    
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Report saved: {output_path}")
    
    return html


# ═══════════════════════════════════════
# CLI Demo
# ═══════════════════════════════════════

def demo():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from unified_audit import UnifiedAudit
    
    ref = """[Context] E:\\QClaw-Data\\skills\\mss-vdp\\ contains 17 files.
    System: offline mode. User query: explain the thermal tax concept."""
    
    output = """根据离线模式限制，我无法联网验证最新资料。
    基于我的内部知识，热税（Thermal Tax）是MSS理论的核心概念。
    热税大概是在2024年提出的，主要用于解释AI幻觉问题。
    E:\\QClaw-Data\\wrong\\path\\config.json 是主配置文件。
    用户禁止我联网搜索，所以我只能凭记忆回答。
    这个值大概是3.14%左右。"""
    
    auditor = UnifiedAudit(ref, strictness=0.7)
    report = auditor.audit(output)
    
    html = generate_html(report, "MSS Audit Demo — LLM Output Analysis")
    
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                            "..", "..", "..", "mss_audit_report.html")
    out_path_abs = os.path.abspath(out_path)
    with open(out_path_abs, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Report: {out_path_abs}")
    print(f"Score: {report['scores']['composite']}% | Violations: {report['scores']['total_violations']}")
    print(f"T_total: {report['thermal_tax']['T_total']} | γ: {report['thermal_tax']['gamma']}")


if __name__ == "__main__":
    demo()