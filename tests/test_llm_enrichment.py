from __future__ import annotations

from app.domain.models import Finding, ReadinessDecision
from app.agents.llm_enrichment_agent import FakeLLMBackend, LLMEnrichmentAgent


def _make_finding() -> Finding:
    return Finding(
        id="T1", title="Auth bypass crítico", severity="Critical",
        active=True, verified=True, tags=["auth", "mfa"],
    )


def _make_decision() -> ReadinessDecision:
    return ReadinessDecision(
        finding_id="T1", title="Auth bypass crítico",
        severity="Critical", category="blocker",
        rationale="Hallazgo Crítico activo.",
    )


def test_fake_backend_returns_enrichment():
    backend = FakeLLMBackend()
    finding = _make_finding()
    decision = _make_decision()
    enrichment = backend.enrich(finding, decision)
    assert len(enrichment.executive_risk_explanation) > 0
    assert len(enrichment.negative_tests) > 0
    assert len(enrichment.compensating_controls) > 0


def test_agent_with_fake_backend_enriches_decision():
    agent = LLMEnrichmentAgent(backend=FakeLLMBackend())
    finding = _make_finding()
    decision = _make_decision()
    enriched = agent.enrich(finding, decision)
    assert enriched.llm_enrichment is not None
    assert "[FAKE]" in enriched.llm_enrichment.executive_risk_explanation


def test_agent_without_backend_returns_unchanged():
    agent = LLMEnrichmentAgent(backend=None)
    finding = _make_finding()
    decision = _make_decision()
    result = agent.enrich(finding, decision)
    assert result.llm_enrichment is None


def test_category_not_changed_by_llm():
    agent = LLMEnrichmentAgent(backend=FakeLLMBackend())
    finding = _make_finding()
    decision = _make_decision()
    enriched = agent.enrich(finding, decision)
    assert enriched.category == "blocker"
