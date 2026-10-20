from __future__ import annotations

from app.domain.models import Finding, ReadinessDecision
from app.domain.rules import (
    BLOCKER_TAGS,
    HIGH_PRE_GOLIVE_TAGS,
    BLOCKER_BUSINESS_FLOWS,
    EVIDENCE_TEMPLATES,
    REMEDIATION_TEMPLATES,
)


def classify(finding: Finding) -> ReadinessDecision:
    tags_lower = {t.lower() for t in finding.tags}
    flow_lower = (finding.business_flow or "").lower()

    # Regla 1: False positive → informational
    if finding.false_positive:
        return _decision(finding, "informational",
                         "Hallazgo marcado como falso positivo, no requiere acción.")

    # Regla 2: Risk accepted → accepted
    if finding.risk_accepted:
        return _decision(finding, "accepted",
                         "Riesgo aceptado formalmente por el equipo.")

    # Regla 3: Critical + active + verified → blocker
    if finding.severity == "Critical" and finding.active and finding.verified:
        return _decision(finding, "blocker",
                         "Hallazgo Crítico activo y verificado: bloquea el Go-Live.",
                         category_for_evidence="blocker")

    # Regla 4: Critical + active (sin verificar) → blocker igual (requiere verificación)
    if finding.severity == "Critical" and finding.active:
        return _decision(finding, "blocker",
                         "Hallazgo Crítico activo sin verificar: debe verificarse y remediarse antes del Go-Live.",
                         category_for_evidence="blocker")

    # Regla 5: High + tags de alto impacto o flujo crítico → blocker
    if finding.severity == "High" and finding.active:
        if tags_lower & BLOCKER_TAGS or flow_lower in BLOCKER_BUSINESS_FLOWS:
            return _decision(finding, "blocker",
                             f"Hallazgo High en flujo/componente crítico ({', '.join(tags_lower & BLOCKER_TAGS or {flow_lower})}): bloquea el Go-Live.",
                             category_for_evidence="blocker")

    # Regla 6: High sin tags blocker → high_pre_go_live
    if finding.severity == "High" and finding.active:
        return _decision(finding, "high_pre_go_live",
                         "Hallazgo High debe remediarse antes del Go-Live.",
                         category_for_evidence="high_pre_go_live")

    # Regla 7: Medium con tags de control crítico → high_pre_go_live
    if finding.severity == "Medium" and finding.active:
        if tags_lower & HIGH_PRE_GOLIVE_TAGS:
            return _decision(finding, "high_pre_go_live",
                             f"Hallazgo Medium afecta controles críticos ({', '.join(tags_lower & HIGH_PRE_GOLIVE_TAGS)}): requiere atención antes del Go-Live.",
                             category_for_evidence="high_pre_go_live")

    # Regla 8: No activo → mitigated
    if not finding.active:
        return _decision(finding, "mitigated",
                         "Hallazgo mitigado o resuelto.")

    # Resto → post_go_live
    return _decision(finding, "post_go_live",
                     f"Hallazgo {finding.severity} a remediar después del Go-Live.")


def _decision(
    finding: Finding,
    category: str,
    rationale: str,
    category_for_evidence: str | None = None,
) -> ReadinessDecision:
    evidence_key = category_for_evidence or category
    required_evidence = EVIDENCE_TEMPLATES.get(evidence_key, [])
    remediation_actions = REMEDIATION_TEMPLATES.get(finding.severity, [])

    owner = _suggest_owner(finding)

    return ReadinessDecision(
        finding_id=finding.id,
        title=finding.title,
        severity=finding.severity,
        category=category,
        rationale=rationale,
        required_evidence=required_evidence,
        remediation_actions=remediation_actions,
        owner_suggestion=owner,
    )


_CWE_OWNER: dict[str, str] = {
    # Autenticación / Identidad
    "287": "Equipo de Identidad", "306": "Equipo de Identidad", "307": "Equipo de Identidad",
    "308": "Equipo de Identidad", "521": "Equipo de Identidad", "522": "Equipo de Identidad",
    "620": "Equipo de Identidad", "798": "Equipo de Identidad", "259": "Equipo de Identidad",
    # Inyección / Desarrollo
    "89": "Equipo de Desarrollo",  "79": "Equipo de Desarrollo",  "77": "Equipo de Desarrollo",
    "78": "Equipo de Desarrollo",  "94": "Equipo de Desarrollo",  "917": "Equipo de Desarrollo",
    "611": "Equipo de Desarrollo", "918": "Equipo de Desarrollo",
    # Control de acceso
    "284": "Equipo de Desarrollo", "285": "Equipo de Desarrollo", "639": "Equipo de Desarrollo",
    "862": "Equipo de Desarrollo", "863": "Equipo de Desarrollo",
    # Criptografía / Infraestructura
    "261": "Equipo de Infraestructura", "295": "Equipo de Infraestructura",
    "310": "Equipo de Infraestructura", "326": "Equipo de Infraestructura",
    "327": "Equipo de Infraestructura", "338": "Equipo de Infraestructura",
    "757": "Equipo de Infraestructura",
    # Logging / Operaciones
    "117": "Equipo de Operaciones / SIEM", "778": "Equipo de Operaciones / SIEM",
    "779": "Equipo de Operaciones / SIEM",
}

_TITLE_KEYWORDS: list[tuple[list[str], str]] = [
    (["pago", "payment", "transfer", "transacci"], "Equipo de Pagos"),
    (["autenticaci", "authentication", "login", "contraseña", "password", "mfa", "2fa", "sso", "oauth", "identity", "identidad"], "Equipo de Identidad"),
    (["sql", "inyecci", "injection", "xss", "cross-site", "csrf", "xxe", "ssrf", "rce", "command"], "Equipo de Desarrollo"),
    (["ssl", "tls", "certificado", "certificate", "cifrado", "crypto", "clave privada", "private key"], "Equipo de Infraestructura"),
    (["log", "audit", "siem", "monitoreo", "monitoring", "alerta", "alert"], "Equipo de Operaciones / SIEM"),
    (["firewall", "waf", "network", "red", "firewall", "vpn", "exposici"], "Equipo de Infraestructura"),
    (["api", "endpoint", "cors", "csp", "header", "cabecera"], "Equipo de Desarrollo"),
]


def _suggest_owner(finding: Finding) -> str:
    tags_lower = {t.lower() for t in finding.tags}

    # 1. Tags explícitos
    if "payment" in tags_lower or "transfer" in tags_lower or "transferencia" in tags_lower:
        return "Equipo de Pagos"
    if "auth" in tags_lower or "mfa" in tags_lower or "identity" in tags_lower:
        return "Equipo de Identidad"
    if "logging" in tags_lower or "audit" in tags_lower or "monitoring" in tags_lower:
        return "Equipo de Operaciones / SIEM"

    # 2. Componente explícito
    if finding.component:
        return f"Equipo responsable de {finding.component}"

    # 3. CWE
    if finding.cwe:
        cwe_num = str(finding.cwe).replace("CWE-", "").strip()
        if cwe_num in _CWE_OWNER:
            return _CWE_OWNER[cwe_num]

    # 4. Palabras clave en el título
    title_lower = finding.title.lower()
    for keywords, owner in _TITLE_KEYWORDS:
        if any(kw in title_lower for kw in keywords):
            return owner

    # 5. Fallback por severidad
    if finding.severity in ("Critical", "High"):
        return "Equipo de Desarrollo"
    return "Equipo de Desarrollo"
