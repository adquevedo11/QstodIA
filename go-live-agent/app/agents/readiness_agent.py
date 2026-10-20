from __future__ import annotations

from datetime import date

from app.domain.models import Finding, ReadinessDecision, ReadinessReport
from app.domain.scoring import classify


class ReadinessAgent:

    def generate_report(
        self,
        product_name: str,
        engagement_name: str,
        target_go_live_date: date,
        findings: list[Finding],
    ) -> ReadinessReport:
        decisions: list[ReadinessDecision] = [classify(f) for f in findings]

        blockers = [d for d in decisions if d.category == "blocker"]
        high_pre = [d for d in decisions if d.category == "high_pre_go_live"]
        post = [d for d in decisions if d.category == "post_go_live"]
        accepted = [d for d in decisions if d.category == "accepted"]
        mitigated = [d for d in decisions if d.category == "mitigated"]
        informational = [d for d in decisions if d.category == "informational"]

        recommendation = self._recommendation(blockers, high_pre)
        missing_evidence = self._missing_evidence(findings, blockers + high_pre)
        executive_summary = self._executive_summary(
            product_name, recommendation, blockers, high_pre, target_go_live_date
        )
        technical_summary = self._technical_summary(decisions)

        return ReadinessReport(
            product_name=product_name,
            engagement_name=engagement_name,
            target_go_live_date=target_go_live_date,
            overall_recommendation=recommendation,
            blockers=blockers,
            high_pre_go_live=high_pre,
            post_go_live=post,
            accepted_risks=accepted,
            mitigated=mitigated,
            informational=informational,
            missing_evidence=missing_evidence,
            executive_summary=executive_summary,
            technical_summary=technical_summary,
            total_findings=len(findings),
        )

    def _recommendation(
        self,
        blockers: list[ReadinessDecision],
        high_pre: list[ReadinessDecision],
    ) -> str:
        if blockers:
            return "No-Go"
        if high_pre:
            return "Go condicionado"
        return "Go"

    def _missing_evidence(
        self,
        findings: list[Finding],
        critical_decisions: list[ReadinessDecision],
    ) -> list[str]:
        missing = []
        findings_by_id = {f.id: f for f in findings}
        for d in critical_decisions:
            f = findings_by_id.get(d.finding_id)
            if f and not f.evidence:
                missing.append(
                    f"[{d.finding_id}] {d.title}: falta evidencia de remediación o validación"
                )
        return missing

    def _executive_summary(
        self,
        product_name: str,
        recommendation: str,
        blockers: list[ReadinessDecision],
        high_pre: list[ReadinessDecision],
        go_live_date: date,
    ) -> str:
        n_blockers = len(blockers)
        n_high = len(high_pre)
        date_str = go_live_date.strftime("%d/%m/%Y")

        if recommendation == "No-Go":
            return (
                f"El producto **{product_name}** NO está listo para salir a producción el {date_str}. "
                f"Se identificaron **{n_blockers} hallazgo(s) bloqueante(s)** que representan riesgo "
                f"crítico para la operación. Es mandatorio remediar estos hallazgos y obtener "
                f"evidencia de corrección antes de aprobar el Go-Live."
            )
        if recommendation == "Go condicionado":
            return (
                f"El producto **{product_name}** puede salir a producción el {date_str} "
                f"bajo condiciones. No existen bloqueantes críticos, pero hay "
                f"**{n_high} hallazgo(s) de alta prioridad** que deben remediarse antes del Go-Live "
                f"o contar con un plan formal de mitigación aprobado."
            )
        return (
            f"El producto **{product_name}** está listo para salir a producción el {date_str}. "
            f"No se identificaron hallazgos bloqueantes ni de alta prioridad pendientes."
        )

    def _technical_summary(self, decisions: list[ReadinessDecision]) -> str:
        counts = {"blocker": 0, "high_pre_go_live": 0, "post_go_live": 0,
                  "accepted": 0, "mitigated": 0, "informational": 0}
        for d in decisions:
            counts[d.category] += 1

        lines = [
            f"- Bloqueantes: {counts['blocker']}",
            f"- Alta prioridad (pre Go-Live): {counts['high_pre_go_live']}",
            f"- Post Go-Live: {counts['post_go_live']}",
            f"- Riesgo aceptado: {counts['accepted']}",
            f"- Mitigados: {counts['mitigated']}",
            f"- Falsos positivos: {counts['informational']}",
            f"- Total analizado: {len(decisions)}",
        ]
        return "\n".join(lines)
