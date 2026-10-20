from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class Finding(BaseModel):
    id: str
    title: str
    severity: Literal["Info", "Low", "Medium", "High", "Critical"]
    status: str = "Active"
    component: str | None = None
    business_flow: str | None = None
    cwe: str | None = None
    cvss_score: float | None = None
    description: str | None = None
    mitigation: str | None = None
    evidence: str | None = None
    active: bool = True
    verified: bool = False
    false_positive: bool = False
    risk_accepted: bool = False
    tags: list[str] = Field(default_factory=list)


class ReadinessDecision(BaseModel):
    finding_id: str
    title: str
    severity: str
    category: Literal[
        "blocker",
        "high_pre_go_live",
        "post_go_live",
        "accepted",
        "mitigated",
        "informational",
    ]
    rationale: str
    required_evidence: list[str] = Field(default_factory=list)
    remediation_actions: list[str] = Field(default_factory=list)
    owner_suggestion: str | None = None
    llm_enrichment: LLMEnrichment | None = None


class LLMEnrichment(BaseModel):
    executive_risk_explanation: str = ""
    remediation_guidance: str = ""
    acceptance_criteria: str = ""
    negative_tests: list[str] = Field(default_factory=list)
    compensating_controls: list[str] = Field(default_factory=list)


class ReadinessReport(BaseModel):
    product_name: str
    engagement_name: str
    target_go_live_date: date
    overall_recommendation: Literal["Go", "No-Go", "Go condicionado"]
    blockers: list[ReadinessDecision] = Field(default_factory=list)
    high_pre_go_live: list[ReadinessDecision] = Field(default_factory=list)
    post_go_live: list[ReadinessDecision] = Field(default_factory=list)
    accepted_risks: list[ReadinessDecision] = Field(default_factory=list)
    mitigated: list[ReadinessDecision] = Field(default_factory=list)
    informational: list[ReadinessDecision] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    executive_summary: str = ""
    technical_summary: str = ""
    total_findings: int = 0
