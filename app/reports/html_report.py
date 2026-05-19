from __future__ import annotations

import base64
import html
from pathlib import Path

from app.domain.models import ReadinessReport, ReadinessDecision

def _logo_b64() -> str:
    logo_path = Path(__file__).parent.parent / "static" / "sqa_logo.png"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return ""

REC_STYLE = {
    "Go":             {"bg": "#27ae60", "light": "#d4edda", "icon": "✅"},
    "No-Go":          {"bg": "#c0392b", "light": "#fdecea", "icon": "🚫"},
    "Go condicionado": {"bg": "#d68910", "light": "#fef9e7", "icon": "⚠️"},
}
SEV_COLOR = {
    "Critical": "#c0392b",
    "High":     "#e67e22",
    "Medium":   "#d4ac0d",
    "Low":      "#27ae60",
    "Info":     "#2980b9",
}

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; color: #3a3a3a; background: #fff; }

.cover {
    background: linear-gradient(135deg, #324458 0%, #1e2d3a 100%);
    color: #fff; padding: 50px 40px 40px;
}
.cover-brand {
    font-size: 8pt; text-transform: uppercase; letter-spacing: 3px;
    color: #ffb323; margin-bottom: 16px;
}
.cover h1 { font-size: 20pt; font-weight: 700; margin-bottom: 8px; }
.cover-product { font-size: 13pt; color: #b8c8d8; margin-bottom: 28px; }
.cover-meta td { padding: 5px 12px 5px 0; font-size: 9.5pt; color: #d0dce8; }
.cover-meta td:first-child { font-weight: 600; color: #ffb323; width: 200px; }

.rec-bar {
    text-align: center; padding: 18px;
    border-bottom: 3px solid;
    border-top: 0; margin: 0;
}
.rec-badge {
    display: inline-block; padding: 10px 30px; border-radius: 30px;
    font-size: 13pt; font-weight: 700; color: #fff;
}

.body { padding: 0 40px 30px; }

.summary-box {
    background: #f4f6f9; border-left: 4px solid #324458;
    padding: 14px 18px; margin-bottom: 8px;
    font-size: 10pt; line-height: 1.65; border-radius: 0 4px 4px 0;
}
.tech-stats { margin-bottom: 14px; line-height: 2.2; }
.stat-pill {
    display: inline-block;
    background: #eef1f5; border: 1px solid #d0d9e3;
    border-radius: 20px; padding: 4px 14px; font-size: 9pt; font-weight: 600;
    margin-right: 6px; margin-bottom: 6px;
}
.stat-pill.danger  { background: #fdecea; border-color: #e8b0ad; color: #c0392b; }
.stat-pill.warning { background: #fef5e7; border-color: #f0d08a; color: #b7770d; }

.section { margin: 26px 0; }
.section-title {
    font-size: 12pt; font-weight: 700; color: #324458;
    border-bottom: 2px solid #ffb323; padding-bottom: 6px; margin-bottom: 14px;
}
.section-note { font-style: italic; color: #666; font-size: 9pt; margin-bottom: 14px; }

.card { border: 1px solid #dde3ea; border-radius: 6px; margin-bottom: 14px; page-break-inside: avoid; }
.card-header {
    background: #324458; color: #fff; padding: 9px 14px;
    border-radius: 6px 6px 0 0;
    overflow: hidden;
}
.card-title { font-weight: 600; font-size: 9.5pt; display: block; padding-right: 80px; }
.sev { float: right; margin-top: -18px; }
.sev { padding: 3px 10px; border-radius: 4px; font-size: 8.5pt; font-weight: 700; color: #fff; white-space: nowrap; }
.card-body { padding: 12px 14px; }

.field-label { font-weight: 700; color: #324458; font-size: 8.5pt; margin-top: 10px; margin-bottom: 3px; }
.field-value { font-size: 9.5pt; line-height: 1.55; }
.items { padding-left: 16px; margin: 3px 0; }
.items li { font-size: 9.5pt; margin-bottom: 2px; }

.llm-box {
    background: #f0f6ff; border-left: 3px solid #324458;
    padding: 10px 14px; margin-top: 12px;
    border-radius: 0 4px 4px 0;
}
.llm-box .field-label { color: #1e2d3a; }
.llm-tag {
    display: inline-block; background: #ffb323; color: #1e2d3a;
    font-size: 7.5pt; font-weight: 700; padding: 1px 7px; border-radius: 10px;
    text-transform: uppercase; letter-spacing: 1px; vertical-align: middle; margin-left: 6px;
}

table.plan { width: 100%; border-collapse: collapse; font-size: 9pt; }
table.plan th { background: #324458; color: #fff; padding: 8px 10px; text-align: left; }
table.plan td { padding: 7px 10px; border-bottom: 1px solid #dde3ea; vertical-align: top; }
table.plan tr:nth-child(even) td { background: #f9fafb; }

.footer {
    margin-top: 36px; text-align: center; font-size: 8pt; color: #999;
    border-top: 1px solid #dde3ea; padding-top: 12px;
}
"""


def _e(text: str) -> str:
    return html.escape(str(text)) if text else ""


def _sev_color(s: str) -> str:
    return SEV_COLOR.get(s, "#888")


def _card(d: ReadinessDecision) -> str:
    sev_color = _sev_color(d.severity)

    actions_html = ""
    if d.remediation_actions:
        items = "".join(f"<li>{_e(a)}</li>" for a in d.remediation_actions)
        actions_html = f'<div class="field-label">Acciones de remediación</div><ul class="items">{items}</ul>'

    evidence_html = ""
    if d.required_evidence:
        items = "".join(f"<li>{_e(e)}</li>" for e in d.required_evidence)
        evidence_html = f'<div class="field-label">Evidencia requerida</div><ul class="items">{items}</ul>'

    llm_html = ""
    if d.llm_enrichment:
        enr = d.llm_enrichment
        tag = '<span class="llm-tag">IA</span>'
        parts = []
        if enr.executive_risk_explanation:
            parts.append(f'<div class="field-label">Impacto ejecutivo {tag}</div><div class="field-value">{_e(enr.executive_risk_explanation)}</div>')
        if enr.remediation_guidance:
            parts.append(f'<div class="field-label">Guía de remediación {tag}</div><div class="field-value">{_e(enr.remediation_guidance)}</div>')
        if enr.negative_tests:
            items = "".join(f"<li>{_e(t)}</li>" for t in enr.negative_tests)
            parts.append(f'<div class="field-label">Pruebas negativas sugeridas {tag}</div><ul class="items">{items}</ul>')
        if enr.compensating_controls:
            items = "".join(f"<li>{_e(c)}</li>" for c in enr.compensating_controls)
            parts.append(f'<div class="field-label">Controles compensatorios {tag}</div><ul class="items">{items}</ul>')
        if parts:
            llm_html = f'<div class="llm-box">{"".join(parts)}</div>'

    owner = _e(d.owner_suggestion or "—")
    title = _e(d.title)
    fid = _e(str(d.finding_id))
    rationale = _e(d.rationale)

    return f"""
<div class="card">
  <div class="card-header">
    <span class="card-title">[{fid}] {title}</span>
    <span class="sev" style="background:{sev_color}">{_e(d.severity)}</span>
  </div>
  <div class="card-body">
    <div style="display:flex;gap:16px;margin-bottom:8px;">
      <div style="flex:1"><div class="field-label">Categoría</div><div class="field-value">{_e(d.category)}</div></div>
      <div style="flex:1"><div class="field-label">Owner sugerido</div><div class="field-value">{owner}</div></div>
    </div>
    <div class="field-label">Justificación</div>
    <div class="field-value">{rationale}</div>
    {actions_html}
    {evidence_html}
    {llm_html}
  </div>
</div>"""


def _section(decisions: list, title: str, note: str) -> str:
    if not decisions:
        return f'<div class="section"><div class="section-title">{title}</div><p class="section-note">Sin hallazgos en esta categoría.</p></div>'
    cards = "".join(_card(d) for d in decisions)
    return f"""
<div class="section">
  <div class="section-title">{title}</div>
  <p class="section-note">{note}</p>
  {cards}
</div>"""


def _plan(report: ReadinessReport) -> str:
    critical = report.blockers + report.high_pre_go_live
    if not critical:
        return ""
    rows = ""
    for i, d in enumerate(critical, 1):
        title = _e(d.title)
        if len(d.title) > 65:
            title = _e(d.title[:65]) + "…"
        rows += f"<tr><td>{i}</td><td>{_e(str(d.finding_id))}</td><td>{title}</td><td>{_e(d.owner_suggestion or '—')}</td><td>{_e(d.category)}</td></tr>"
    return f"""
<div class="section">
  <div class="section-title">Plan de Remediación Recomendado</div>
  <table class="plan">
    <tr><th>#</th><th>ID</th><th>Hallazgo</th><th>Owner</th><th>Categoría</th></tr>
    {rows}
  </table>
</div>"""


def generate(report: ReadinessReport) -> str:
    rec = report.overall_recommendation
    style = REC_STYLE.get(rec, {"bg": "#666", "light": "#eee", "icon": ""})
    logo_b64 = _logo_b64()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:40px;margin-bottom:12px" alt="SQA SA"/><br>' if logo_b64 else ""

    stats_html = f"""
<div class="tech-stats">
  <span class="stat-pill danger">🚫 {len(report.blockers)} bloqueantes</span>
  <span class="stat-pill warning">⚠️ {len(report.high_pre_go_live)} alta prioridad</span>
  <span class="stat-pill">📋 {len(report.post_go_live)} post Go-Live</span>
  <span class="stat-pill">✅ {len(report.accepted_risks)} aceptados</span>
  <span class="stat-pill">🛡️ {len(report.mitigated)} mitigados</span>
  <span class="stat-pill">📊 {report.total_findings} total</span>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Go-Live Readiness Report — {_e(report.product_name)}</title>
<style>{CSS}</style>
</head>
<body>

<div class="cover">
  {logo_html}<div class="cover-brand">SQA SA · Security Quality Assurance</div>
  <h1>Go-Live Security Readiness Report</h1>
  <div class="cover-product">{_e(report.product_name)}</div>
  <table class="cover-meta">
    <tr><td>Engagement</td><td>{_e(report.engagement_name)}</td></tr>
    <tr><td>Fecha objetivo Go-Live</td><td>{report.target_go_live_date.strftime('%d/%m/%Y')}</td></tr>
    <tr><td>Total hallazgos analizados</td><td>{report.total_findings}</td></tr>
  </table>
</div>

<div class="rec-bar" style="background:{style['light']};border-color:{style['bg']}">
  <span class="rec-badge" style="background:{style['bg']}">
    {style['icon']} Recomendación: {_e(rec)}
  </span>
</div>

<div class="body">

<div class="section">
  <div class="section-title">Resumen Ejecutivo</div>
  <div class="summary-box">{_e(report.executive_summary)}</div>
</div>

<div class="section">
  <div class="section-title">Resumen Técnico</div>
  {stats_html}
  <div class="summary-box">{_e(report.technical_summary)}</div>
</div>

{_section(report.blockers, "🚫 Hallazgos Bloqueantes", "Estos hallazgos deben ser remediados antes del Go-Live.")}
{_section(report.high_pre_go_live, "⚠️ Alta Prioridad — Antes del Go-Live", "Deben remediarse antes del Go-Live o contar con plan de mitigación aprobado.")}
{_section(report.post_go_live, "📋 Post Go-Live", "Pueden remediarse después del Go-Live con seguimiento formal.")}
{_section(report.accepted_risks, "✅ Riesgos Aceptados", "Riesgos formalmente aceptados por el equipo.")}
{_section(report.mitigated, "🛡️ Mitigados", "Hallazgos resueltos o inactivos al momento del análisis.")}

{_plan(report)}

<div class="footer">
  Reporte generado automáticamente por Go-Live Readiness Agent &nbsp;·&nbsp;
  SQA SA &nbsp;·&nbsp; Confidencial &nbsp;·&nbsp;
  {report.target_go_live_date.strftime('%d/%m/%Y')}
</div>

</div>
</body>
</html>"""
