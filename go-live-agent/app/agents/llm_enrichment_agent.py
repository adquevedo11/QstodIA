from __future__ import annotations

import json
from abc import ABC, abstractmethod

from app.domain.models import Finding, ReadinessDecision, LLMEnrichment

SYSTEM_PROMPT = """Eres un asistente de Go-Live Security Readiness para equipos AppSec.

Tu tarea es enriquecer hallazgos de seguridad ya clasificados por un motor determinístico.

Reglas:
- NO cambies la severidad.
- NO cambies la categoría de decisión.
- NO apruebes riesgos.
- NO marques hallazgos como cerrados.
- NO inventes evidencia.
- Si falta evidencia, dilo explícitamente.
- Recomienda acciones técnicas verificables.
- Redacta en español profesional.
- Prioriza impacto de negocio, explotabilidad, evidencia, controles compensatorios y fecha de salida a producción.
- Devuelve ÚNICAMENTE JSON válido sin texto adicional."""

USER_TEMPLATE = """Enriquece el siguiente hallazgo de seguridad:

Hallazgo: {title}
Severidad: {severity}
Categoría de decisión: {category}
Justificación: {rationale}
Descripción: {description}
Tags: {tags}
Evidencia disponible: {evidence}

Devuelve JSON con esta estructura exacta:
{{
  "executive_risk_explanation": "...",
  "remediation_guidance": "...",
  "acceptance_criteria": "...",
  "negative_tests": ["...", "..."],
  "compensating_controls": ["...", "..."]
}}"""


class BaseLLMBackend(ABC):
    @abstractmethod
    def enrich(self, finding: Finding, decision: ReadinessDecision) -> LLMEnrichment:
        ...


class OpenAIBackend(BaseLLMBackend):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, max_retries=0)
        self._model = model

    def enrich(self, finding: Finding, decision: ReadinessDecision) -> LLMEnrichment:
        user_msg = USER_TEMPLATE.format(
            title=finding.title,
            severity=finding.severity,
            category=decision.category,
            rationale=decision.rationale,
            description=finding.description or "No disponible",
            tags=", ".join(finding.tags) if finding.tags else "Ninguno",
            evidence=finding.evidence or "Sin evidencia",
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return LLMEnrichment(**json.loads(raw))


class GroqBackend(BaseLLMBackend):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        from openai import OpenAI
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self._model = model

    def enrich(self, finding: Finding, decision: ReadinessDecision) -> LLMEnrichment:
        user_msg = USER_TEMPLATE.format(
            title=finding.title,
            severity=finding.severity,
            category=decision.category,
            rationale=decision.rationale,
            description=finding.description or "No disponible",
            tags=", ".join(finding.tags) if finding.tags else "Ninguno",
            evidence=finding.evidence or "Sin evidencia",
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return LLMEnrichment(**json.loads(raw))


class FakeLLMBackend(BaseLLMBackend):
    """Backend para tests — no llama a ninguna API."""

    def enrich(self, finding: Finding, decision: ReadinessDecision) -> LLMEnrichment:
        return LLMEnrichment(
            executive_risk_explanation=f"[FAKE] Riesgo ejecutivo para {finding.title}.",
            remediation_guidance=f"[FAKE] Guía de remediación para {finding.severity}.",
            acceptance_criteria="[FAKE] Criterio de aceptación de prueba.",
            negative_tests=["[FAKE] Prueba negativa 1", "[FAKE] Prueba negativa 2"],
            compensating_controls=["[FAKE] Control compensatorio temporal"],
        )


class LLMEnrichmentAgent:

    def __init__(self, backend: BaseLLMBackend | None = None):
        self._backend = backend

    @classmethod
    def from_settings(cls) -> "LLMEnrichmentAgent":
        from app.config import settings
        if not settings.llm_enabled:
            return cls(backend=None)
        provider = settings.llm_provider.lower()
        if provider == "groq" and settings.groq_api_key:
            backend = GroqBackend(api_key=settings.groq_api_key, model=settings.llm_model)
        elif provider == "openai" and settings.openai_api_key:
            backend = OpenAIBackend(api_key=settings.openai_api_key, model=settings.llm_model)
        elif provider == "fake":
            backend = FakeLLMBackend()
        else:
            backend = None
        return cls(backend=backend)

    def enrich(self, finding: Finding, decision: ReadinessDecision) -> ReadinessDecision:
        if self._backend is None:
            return decision
        try:
            enrichment = self._backend.enrich(finding, decision)
            return decision.model_copy(update={"llm_enrichment": enrichment})
        except Exception as e:
            import traceback
            print(f"[LLM] Error al enriquecer finding_id={finding.id} título='{finding.title}': {e}")
            traceback.print_exc()
            return decision
