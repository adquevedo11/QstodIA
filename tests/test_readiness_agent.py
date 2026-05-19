from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from app.domain.models import Finding
from app.agents.readiness_agent import ReadinessAgent

AGENT = ReadinessAgent()
GO_LIVE = date(2026, 6, 15)


def _make(id: str, severity: str, tags: list[str] = [], **kwargs) -> Finding:
    return Finding(
        id=id, title=f"Hallazgo {id}", severity=severity,
        active=True, verified=True,
        false_positive=False, risk_accepted=False,
        tags=tags, **kwargs,
    )


def test_no_go_when_blockers_exist():
    findings = [_make("F1", "Critical")]
    report = AGENT.generate_report("Producto", "Eng", GO_LIVE, findings)
    assert report.overall_recommendation == "No-Go"
    assert len(report.blockers) == 1


def test_go_condicionado_when_high_pre_golive():
    findings = [_make("F1", "High", tags=["xss"])]
    report = AGENT.generate_report("Producto", "Eng", GO_LIVE, findings)
    assert report.overall_recommendation == "Go condicionado"
    assert len(report.high_pre_go_live) == 1


def test_go_when_only_post_golive():
    findings = [_make("F1", "Low"), _make("F2", "Medium", tags=[])]
    report = AGENT.generate_report("Producto", "Eng", GO_LIVE, findings)
    assert report.overall_recommendation == "Go"


def test_missing_evidence_detected_for_blockers():
    findings = [_make("F1", "Critical", evidence=None)]
    report = AGENT.generate_report("Producto", "Eng", GO_LIVE, findings)
    assert len(report.missing_evidence) == 1
    assert "F1" in report.missing_evidence[0]


def test_no_missing_evidence_when_evidence_present():
    findings = [_make("F1", "Critical", evidence="Reporte de pentest adjunto")]
    report = AGENT.generate_report("Producto", "Eng", GO_LIVE, findings)
    assert len(report.missing_evidence) == 0


def test_report_has_summaries():
    findings = [_make("F1", "Critical")]
    report = AGENT.generate_report("Banco Demo", "Eng", GO_LIVE, findings)
    assert len(report.executive_summary) > 0
    assert len(report.technical_summary) > 0


def test_total_findings_count():
    findings = [_make(f"F{i}", "Low") for i in range(5)]
    report = AGENT.generate_report("P", "E", GO_LIVE, findings)
    assert report.total_findings == 5


def test_sample_findings_json():
    """Carga el JSON de demo y genera reporte."""
    path = Path(__file__).parent.parent / "examples" / "sample_findings.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    findings = [Finding(**f) for f in raw]
    report = AGENT.generate_report(
        "Banco Demo – API Transferencias Alto Valor",
        "Go-Live Readiness – Release Mayo",
        GO_LIVE,
        findings,
    )
    assert report.overall_recommendation in ("No-Go", "Go condicionado", "Go")
    assert report.total_findings == len(findings)
    assert len(report.blockers) >= 1
