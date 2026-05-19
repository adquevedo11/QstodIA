from __future__ import annotations

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

PAYLOAD = {
    "product_name": "Banco Demo",
    "engagement_name": "Go-Live Mayo",
    "target_go_live_date": "2026-06-15",
    "findings": [
        {
            "id": "T1",
            "title": "Critical Blocker",
            "severity": "Critical",
            "active": True,
            "verified": True,
            "false_positive": False,
            "risk_accepted": False,
            "tags": [],
        },
        {
            "id": "T2",
            "title": "Low finding",
            "severity": "Low",
            "active": True,
            "verified": False,
            "false_positive": False,
            "risk_accepted": False,
            "tags": [],
        },
    ],
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_returns_report():
    r = client.post("/readiness/analyze", json=PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    assert data["overall_recommendation"] == "No-Go"
    assert len(data["blockers"]) == 1


def test_analyze_empty_findings_returns_400():
    payload = {**PAYLOAD, "findings": []}
    r = client.post("/readiness/analyze", json=payload)
    assert r.status_code == 400


def test_markdown_report():
    r = client.post("/readiness/report/markdown", json=PAYLOAD)
    assert r.status_code == 200
    text = r.text
    assert "Go-Live Security Readiness Report" in text
    assert "No-Go" in text
    assert "Bloqueantes" in text


def test_markdown_contains_sections():
    r = client.post("/readiness/report/markdown", json=PAYLOAD)
    text = r.text
    for section in ["Resumen Ejecutivo", "Resumen Técnico", "Plan de Remediación"]:
        assert section in text, f"Falta sección: {section}"
