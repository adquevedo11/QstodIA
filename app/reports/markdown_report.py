from __future__ import annotations

from app.domain.models import ReadinessReport, ReadinessDecision

RECOMMENDATION_EMOJI = {
    "Go": "✅",
    "No-Go": "🚫",
    "Go condicionado": "⚠️",
}


def generate(report: ReadinessReport) -> str:
    emoji = RECOMMENDATION_EMOJI.get(report.overall_recommendation, "")
    lines: list[str] = []

    lines += [
        f"# Go-Live Security Readiness Report",
        f"",
        f"| Campo | Valor |",
        f"|-------|-------|",
        f"| **Producto** | {report.product_name} |",
        f"| **Engagement** | {report.engagement_name} |",
        f"| **Fecha objetivo Go-Live** | {report.target_go_live_date.strftime('%d/%m/%Y')} |",
        f"| **Total hallazgos analizados** | {report.total_findings} |",
        f"",
        f"---",
        f"",
        f"## {emoji} Recomendación General: {report.overall_recommendation}",
        f"",
        f"## Resumen Ejecutivo",
        f"",
        report.executive_summary,
        f"",
        f"## Resumen Técnico",
        f"",
        report.technical_summary,
        f"",
        f"---",
        f"",
    ]

    lines += _section_table(
        "🚫 Hallazgos Bloqueantes",
        report.blockers,
        "Estos hallazgos **deben ser remediados** antes del Go-Live.",
    )

    lines += _section_table(
        "⚠️ Alta Prioridad — Antes del Go-Live",
        report.high_pre_go_live,
        "Deben remediarse antes del Go-Live o contar con plan de mitigación aprobado.",
    )

    lines += _section_table(
        "📋 Post Go-Live",
        report.post_go_live,
        "Pueden remediarse después del Go-Live con seguimiento formal.",
    )

    lines += _section_table(
        "✅ Riesgos Aceptados",
        report.accepted_risks,
        "Riesgos formalmente aceptados por el equipo.",
    )

    if report.missing_evidence:
        lines += [
            f"## ❌ Evidencia Faltante",
            f"",
            f"Los siguientes hallazgos críticos no cuentan con evidencia de remediación:",
            f"",
        ]
        for item in report.missing_evidence:
            lines.append(f"- {item}")
        lines.append("")

    lines += _remediation_plan(report)

    lines += [
        f"---",
        f"",
        f"*Reporte generado automáticamente por Go-Live Readiness Agent — SQA SA*",
    ]

    return "\n".join(lines)


def _section_table(title: str, decisions: list[ReadinessDecision], note: str) -> list[str]:
    if not decisions:
        return [f"## {title}", f"", f"_Sin hallazgos en esta categoría._", f"", f"---", f""]

    lines = [f"## {title}", f"", f"_{note}_", f""]
    lines += [
        "| ID | Hallazgo | Severidad | Componente | Owner |",
        "|----|----------|-----------|------------|-------|",
    ]
    for d in decisions:
        owner = d.owner_suggestion or "—"
        lines.append(f"| {d.finding_id} | {d.title} | {d.severity} | — | {owner} |")

    lines += [""]

    for d in decisions:
        lines += [
            f"### [{d.finding_id}] {d.title}",
            f"",
            f"**Severidad:** {d.severity}  ",
            f"**Categoría:** {d.category}  ",
            f"**Justificación:** {d.rationale}",
            f"",
        ]
        if d.remediation_actions:
            lines.append("**Acciones de remediación:**")
            for a in d.remediation_actions:
                lines.append(f"- {a}")
            lines.append("")
        if d.required_evidence:
            lines.append("**Evidencia requerida:**")
            for e in d.required_evidence:
                lines.append(f"- {e}")
            lines.append("")
        if d.llm_enrichment:
            enr = d.llm_enrichment
            if enr.executive_risk_explanation:
                lines += [f"**Impacto ejecutivo:** {enr.executive_risk_explanation}", ""]
            if enr.remediation_guidance:
                lines += [f"**Guía de remediación (IA):** {enr.remediation_guidance}", ""]
            if enr.negative_tests:
                lines.append("**Pruebas negativas sugeridas:**")
                for t in enr.negative_tests:
                    lines.append(f"- {t}")
                lines.append("")
            if enr.compensating_controls:
                lines.append("**Controles compensatorios:**")
                for c in enr.compensating_controls:
                    lines.append(f"- {c}")
                lines.append("")

    lines += ["---", ""]
    return lines


def _remediation_plan(report: ReadinessReport) -> list[str]:
    critical = report.blockers + report.high_pre_go_live
    if not critical:
        return []

    lines = [
        f"## Plan de Remediación Recomendado",
        f"",
        f"| Prioridad | ID | Hallazgo | Owner | Categoría |",
        f"|-----------|-----|----------|-------|-----------|",
    ]
    for i, d in enumerate(critical, 1):
        owner = d.owner_suggestion or "—"
        lines.append(f"| {i} | {d.finding_id} | {d.title} | {owner} | {d.category} |")

    lines += ["", "---", ""]
    return lines
