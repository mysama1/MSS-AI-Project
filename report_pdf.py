#!/usr/bin/env python3
"""
DEV-104: MSS Audit PDF Report Generator
Converts unified audit results → styled PDF using fpdf2
"""
import sys, os, json
from datetime import datetime
from typing import Dict, Any
from fpdf import FPDF

class AuditPDF(FPDF):
    """Styled PDF report for MSS audit results."""
    
    def __init__(self, title: str = "MSS Audit Report"):
        super().__init__('P', 'mm', 'A4')
        self.title = title.encode('ascii', errors='replace').decode('ascii')
        self.set_auto_page_break(True, 20)
        self._colors = {
            'pass': (0, 140, 70),
            'warn': (200, 150, 30),
            'reject': (180, 40, 40),
            'dark': (30, 30, 40),
            'gray': (120, 120, 130),
            'light': (240, 240, 245),
            'white': (255, 255, 255),
        }
    
    def header(self):
        if self.page_no() == 1:
            self.set_fill_color(*self._colors['dark'])
            self.rect(0, 0, 210, 35, 'F')
            self.set_text_color(*self._colors['white'])
            self.set_font('Helvetica', 'B', 18)
            self.ln(8)
            self.cell(0, 10, self._safe(self.title), ln=True, align='C')
            self.set_font('Helvetica', '', 9)
            ts = self._safe(datetime.now().strftime('%Y-%m-%d %H:%M'))
            self.cell(0, 6, f'Generated: {ts}  |  MSS VDP v2.4', ln=True, align='C')
            self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(*self._colors['gray'])
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')
    
    def section_title(self, text: str):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(*self._colors['dark'])
        self.set_fill_color(*self._colors['light'])
        self.cell(0, 8, f'  {text}', ln=True, fill=True)
        self.ln(3)
    
    def verdict_badge(self, verdict: str):
        color = self._colors.get(verdict, self._colors['gray'])
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(*color)
        self.cell(0, 12, verdict.upper(), ln=True, align='C')
        self.ln(4)
    
    def score_bar(self, score: float, label: str = "Composite Score"):
        x = self.get_x()
        y = self.get_y()
        w = 180
        
        # Label
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*self._colors['dark'])
        self.cell(50, 6, self._safe(label))
        
        # Background bar
        self.set_fill_color(230, 230, 235)
        self.rect(x + 50, y, w - 50, 6, 'F')
        
        # Score bar
        if score >= 95:
            color = self._colors['pass']
        elif score >= 70:
            color = self._colors['warn']
        else:
            color = self._colors['reject']
        self.set_fill_color(*color)
        bar_w = (w - 50) * min(score / 100, 1.0)
        self.rect(x + 50, y, bar_w, 6, 'F')
        
        # Score text
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*self._colors['white'] if score >= 70 else self._colors['dark'])
        self.set_xy(x + 52, y)
        self.cell(0, 6, f'{score:.1f}%', ln=True)
        self.ln(3)
    
    def info_row(self, pairs: list):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*self._colors['dark'])
        for label, value in pairs:
            self.cell(40, 6, f'{label}:')
            self.set_font('Helvetica', 'B', 10)
            self.cell(50, 6, str(value))
            self.set_font('Helvetica', '', 10)
        self.ln(8)
    
    def _safe(self, text: str) -> str:
        """Sanitize text for Helvetica font."""
        if isinstance(text, str):
            return text.encode('ascii', errors='replace').decode('ascii')
        return str(text)
    
    def violation_table(self, violations: list):
        if not violations:
            self.set_font('Helvetica', 'I', 10)
            self.set_text_color(*self._colors['pass'])
            self.cell(0, 6, '  No violations found', ln=True)
            self.ln(3)
            return
        
        # Header
        self.set_fill_color(*self._colors['dark'])
        self.set_text_color(*self._colors['white'])
        self.set_font('Helvetica', 'B', 8)
        cols = [('Sev', 15), ('Rule', 22), ('Layer', 22), ('Detail', 121)]
        for text, w in cols:
            self.cell(w, 6, text, fill=True)
        self.ln()
        
        # Rows
        for i, v in enumerate(violations):
            sev = self._safe(v.get('severity', v.get('severity', 'warn'))[:8])
            rule = self._safe(v.get('rule_id', v.get('check', '?'))[:14])
            layer = self._safe(v.get('layer', v.get('kind', '?'))[:14])
            detail = self._safe(v.get('detail', v.get('quote', '?'))[:75])
            
            if i % 2 == 0:
                self.set_fill_color(250, 250, 252)
            else:
                self.set_fill_color(*self._colors['white'])
            
            sev_color = self._colors.get(sev, self._colors['gray'])
            self.set_text_color(*sev_color)
            self.set_font('Helvetica', 'B', 7)
            self.cell(15, 5, sev.upper(), fill=True)
            
            self.set_text_color(*self._colors['dark'])
            self.set_font('Helvetica', '', 7)
            self.cell(22, 5, rule, fill=True)
            self.cell(22, 5, layer, fill=True)
            self.cell(121, 5, detail, fill=True)
            self.ln()
        self.ln(3)
    
    def layer_status(self, layers: dict):
        self.section_title("Defense Layers")
        for name, data in layers.items():
            status = data.get('status', '?')
            vc = data.get('violation_count', 0)
            
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(*self._colors['dark'])
            self.cell(40, 6, self._safe(name))
            
            color = self._colors.get(status.lower() if isinstance(status, str) else 'pass', 
                                    self._colors['pass'] if 'PASS' in str(status) else self._colors['warn'])
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(*color)
            self.cell(25, 6, str(status)[:6])
            
            self.set_font('Helvetica', '', 9)
            self.set_text_color(*self._colors['dark'])
            self.cell(0, 6, f'{vc} violations', ln=True)
        self.ln(3)


def generate_pdf(report: Dict, output_path: str = None, title: str = "MSS Audit Report") -> str:
    """Generate styled PDF from unified audit report."""
    if output_path is None:
        output_path = f"mss_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Deep sanitize: replace all non-ASCII for fpdf Helvetica compatibility
    def deep_ascii(obj):
        if isinstance(obj, str):
            return obj.encode('ascii', errors='replace').decode('ascii')
        elif isinstance(obj, dict):
            return {deep_ascii(k): deep_ascii(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [deep_ascii(i) for i in obj]
        return obj
    report = deep_ascii(report)
    title = title.encode('ascii', errors='replace').decode('ascii')
    
    pdf = AuditPDF(title)
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Verdict
    verdict = report.get('verdict', 'pass')
    pdf.verdict_badge(verdict)
    
    # Scores
    scores = report.get('scores', {})
    pdf.score_bar(scores.get('composite', 0), 'Composite Score')
    
    # Info
    pdf.info_row([
        ('Timestamp', report.get('timestamp', '?')),
        ('Violations', str(scores.get('total_violations', 0))),
        ('T_total', str(report.get('thermal_tax', {}).get('T_total', '?'))),
        ('Gamma', str(report.get('thermal_tax', {}).get('gamma', '?'))),
    ])
    
    # Heat tax
    tt = report.get('thermal_tax', {})
    if tt:
        pdf.section_title("Thermal Tax Breakdown")
        pdf.info_row([
            ('T_direct', str(tt.get('T_direct', '?'))),
            ('T_potential', str(tt.get('T_potential', '?'))),
            ('T_total', str(tt.get('T_total', '?'))),
            ('Efficiency', str(tt.get('efficiency', '?'))),
        ])
    
    # Layers
    layers = report.get('layers', {})
    if layers:
        pdf.layer_status(layers)
    
    # Violations
    violations = report.get('violations', [])
    pdf.section_title(f"Violations ({len(violations)})")
    pdf.violation_table(violations)
    
    # Summary
    pdf.section_title("Summary")
    summary = report.get('summary', report.get('scores', {}))
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*pdf._colors['dark'])
    pdf.multi_cell(0, 5, json.dumps(summary, indent=2, ensure_ascii=True))
    
    pdf.output(output_path)
    return output_path


def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS Audit PDF Generator')
    ap.add_argument('input', help='JSON audit report file')
    ap.add_argument('--output', '-o', help='Output PDF path')
    ap.add_argument('--title', default='MSS Audit Report', help='Report title')
    args = ap.parse_args()
    
    with open(args.input, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    path = generate_pdf(report, args.output, args.title)
    print(f'PDF generated: {path}')
    print(f'Size: {os.path.getsize(path):,} bytes')


if __name__ == '__main__':
    main()
