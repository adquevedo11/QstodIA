from __future__ import annotations

import pytest
from app.domain.models import Finding
from app.domain.scoring import classify


def _finding(**kwargs) -> Finding:
    defaults = dict(
        id="T1", title="Test", severity="High",
        active=True, verified=True,
        false_positive=False, risk_accepted=False, tags=[],
    )
    defaults.update(kwargs)
    return Finding(**defaults)


def test_false_positive_is_informational():
    f = _finding(false_positive=True, severity="Critical")
    d = classify(f)
    assert d.category == "informational"


def test_risk_accepted_is_accepted():
    f = _finding(risk_accepted=True, severity="High")
    d = classify(f)
    assert d.category == "accepted"


def test_critical_verified_active_is_blocker():
    f = _finding(severity="Critical", active=True, verified=True)
    d = classify(f)
    assert d.category == "blocker"


def test_critical_unverified_active_is_blocker():
    f = _finding(severity="Critical", active=True, verified=False)
    d = classify(f)
    assert d.category == "blocker"


def test_high_with_payment_tag_is_blocker():
    f = _finding(severity="High", tags=["payment", "transfer"])
    d = classify(f)
    assert d.category == "blocker"


def test_high_with_mfa_tag_is_blocker():
    f = _finding(severity="High", tags=["mfa"])
    d = classify(f)
    assert d.category == "blocker"


def test_high_with_auth_tag_is_blocker():
    f = _finding(severity="High", tags=["auth"])
    d = classify(f)
    assert d.category == "blocker"


def test_high_without_blocker_tags_is_high_pre_golive():
    f = _finding(severity="High", tags=["xss"])
    d = classify(f)
    assert d.category == "high_pre_go_live"


def test_medium_with_security_gate_tag_is_high_pre_golive():
    f = _finding(severity="Medium", tags=["security-gate"])
    d = classify(f)
    assert d.category == "high_pre_go_live"


def test_medium_with_audit_tag_is_high_pre_golive():
    f = _finding(severity="Medium", tags=["audit", "logging"])
    d = classify(f)
    assert d.category == "high_pre_go_live"


def test_medium_without_critical_tags_is_post_golive():
    f = _finding(severity="Medium", tags=["informativo"])
    d = classify(f)
    assert d.category == "post_go_live"


def test_low_is_post_golive():
    f = _finding(severity="Low")
    d = classify(f)
    assert d.category == "post_go_live"


def test_inactive_finding_is_informational():
    f = _finding(severity="High", active=False, tags=["payment"])
    d = classify(f)
    assert d.category == "informational"


def test_high_critical_business_flow_is_blocker():
    f = _finding(severity="High", business_flow="high-value-transfer", tags=[])
    d = classify(f)
    assert d.category == "blocker"


def test_decision_has_rationale():
    f = _finding(severity="Critical", active=True, verified=True)
    d = classify(f)
    assert len(d.rationale) > 0


def test_decision_has_remediation_actions():
    f = _finding(severity="Critical", active=True, verified=True)
    d = classify(f)
    assert len(d.remediation_actions) > 0
