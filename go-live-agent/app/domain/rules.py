from __future__ import annotations

BLOCKER_TAGS = {
    "auth", "mfa", "payment", "transfer", "replay",
    "authorization", "privilege-escalation", "autorizacion",
    "transferencia", "pago",
}

HIGH_PRE_GOLIVE_TAGS = {
    "security-gate", "logging", "audit", "monitoring",
    "auditoria", "monitoreo",
}

BLOCKER_BUSINESS_FLOWS = {
    "high-value-transfer", "beneficiary-registration",
    "payment-processing", "authentication",
}

EVIDENCE_TEMPLATES = {
    "blocker": [
        "Reporte de prueba de penetración con hallazgo validado",
        "Evidencia de remediación aplicada y re-testeada",
        "Aprobación del equipo de seguridad",
    ],
    "high_pre_go_live": [
        "Evidencia de corrección implementada",
        "Resultado de re-escaneo limpio",
    ],
}

REMEDIATION_TEMPLATES = {
    "Critical": [
        "Remediar de inmediato antes del Go-Live",
        "Escalar al líder técnico y CISO",
        "Documentar plan de remediación con fecha compromiso",
    ],
    "High": [
        "Planificar remediación urgente",
        "Implementar control compensatorio temporal si aplica",
        "Validar corrección con prueba negativa",
    ],
    "Medium": [
        "Incluir en sprint actual o siguiente",
        "Documentar riesgo residual si no se puede remediar antes del Go-Live",
    ],
    "Low": ["Incluir en backlog de seguridad"],
    "Info": ["Revisar y documentar si aplica"],
}
