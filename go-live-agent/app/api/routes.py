from __future__ import annotations

from datetime import date
from fastapi import APIRouter, HTTPException
from fastapi import Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.domain.models import Finding, ReadinessReport
from app.agents.readiness_agent import ReadinessAgent
from app.reports import markdown_report, html_report

router = APIRouter()
_agent = ReadinessAgent()


class AnalyzeRequest(BaseModel):
    product_name: str
    engagement_name: str
    target_go_live_date: date
    findings: list[Finding]


class DefectDojoRequest(BaseModel):
    product_id: int
    engagement_id: int
    target_go_live_date: date


@router.get("/health")
def health():
    from app.config import settings
    return {
        "status": "ok",
        "service": "go-live-readiness-agent",
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider if settings.llm_enabled else None,
        "llm_model": settings.llm_model if settings.llm_enabled else None,
    }


@router.delete("/cache/{engagement_id}")
def invalidate_cache(engagement_id: int):
    from app import cache
    cache.invalidate(engagement_id)
    return {"status": "ok", "engagement_id": engagement_id, "message": "Caché invalidada"}


@router.post("/readiness/analyze", response_model=ReadinessReport)
def analyze(request: AnalyzeRequest) -> ReadinessReport:
    if not request.findings:
        raise HTTPException(status_code=400, detail="Se requiere al menos un finding.")
    return _agent.generate_report(
        product_name=request.product_name,
        engagement_name=request.engagement_name,
        target_go_live_date=request.target_go_live_date,
        findings=request.findings,
    )


@router.post("/readiness/report/markdown", response_class=PlainTextResponse)
def report_markdown(request: AnalyzeRequest) -> str:
    if not request.findings:
        raise HTTPException(status_code=400, detail="Se requiere al menos un finding.")
    report = _agent.generate_report(
        product_name=request.product_name,
        engagement_name=request.engagement_name,
        target_go_live_date=request.target_go_live_date,
        findings=request.findings,
    )
    return markdown_report.generate(report)


def _build_defectdojo_report(request: DefectDojoRequest) -> ReadinessReport:
    from app.clients.defectdojo_client import DefectDojoClient
    from app.agents.llm_enrichment_agent import LLMEnrichmentAgent
    from app.config import settings
    from app import cache

    client = DefectDojoClient(
        base_url=settings.defectdojo_base_url,
        api_token=settings.defectdojo_api_token,
    )
    try:
        product = client.get_product(request.product_id)
        engagement = client.get_engagement(request.engagement_id)
        findings = client.list_findings(request.engagement_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al conectar con DefectDojo: {e}")

    # Verificar caché antes de generar
    fhash = cache.findings_hash(findings)
    cached = cache.get(request.engagement_id, fhash)
    if cached:
        print(f"[CACHE] Hit para engagement {request.engagement_id}")
        return ReadinessReport(**cached)

    report = _agent.generate_report(
        product_name=product.get("name", f"Producto #{request.product_id}"),
        engagement_name=engagement.get("name", f"Engagement #{request.engagement_id}"),
        target_go_live_date=request.target_go_live_date,
        findings=findings,
    )

    llm = LLMEnrichmentAgent.from_settings()
    findings_by_id = {f.id: f for f in findings}

    ENRICH_SEVERITIES = {"Critical", "High", "Medium"}

    def _enrich_list(decisions):
        import time
        enriched = []
        for d in decisions:
            if d.finding_id in findings_by_id and d.severity in ENRICH_SEVERITIES:
                enriched.append(llm.enrich(findings_by_id[d.finding_id], d))
                time.sleep(2)
            else:
                enriched.append(d)
        return enriched

    enriched_blockers = _enrich_list(report.blockers)
    enriched_high = _enrich_list(report.high_pre_go_live)
    enriched_post = _enrich_list(report.post_go_live)

    final_report = report.model_copy(update={
        "blockers": enriched_blockers,
        "high_pre_go_live": enriched_high,
        "post_go_live": enriched_post,
    })

    # Guardar en caché
    cache.set(request.engagement_id, fhash, final_report.model_dump(mode="json"))

    return final_report


@router.post("/readiness/analyze/defectdojo", response_model=ReadinessReport)
def analyze_from_defectdojo(request: DefectDojoRequest) -> ReadinessReport:
    return _build_defectdojo_report(request)


@router.post("/readiness/report/defectdojo/markdown", response_class=PlainTextResponse)
def report_defectdojo_markdown(request: DefectDojoRequest) -> str:
    report = _build_defectdojo_report(request)
    return markdown_report.generate(report)


@router.post("/readiness/report/defectdojo/html", response_class=PlainTextResponse)
def report_defectdojo_html(request: DefectDojoRequest) -> str:
    report = _build_defectdojo_report(request)
    return html_report.generate(report)


@router.post("/readiness/report/defectdojo/pdf")
def report_defectdojo_pdf(request: DefectDojoRequest) -> Response:
    from weasyprint import HTML
    report = _build_defectdojo_report(request)
    html_content = html_report.generate(report)
    pdf_bytes = HTML(string=html_content).write_pdf()
    filename = f"go-live-readiness-eng{request.engagement_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Pentest AI Endpoints ──────────────────────────────────────────────────────

from typing import Optional as Opt

class EnrichFindingRequest(BaseModel):
    title: str
    severity: Opt[str] = None
    cvss_score: Opt[float] = None
    cvss_vector: Opt[str] = None
    affected_component: Opt[str] = None
    industry: Opt[str] = None
    project_title: str = ""

class GenerateSummaryRequest(BaseModel):
    project_title: str
    industry: Opt[str] = None
    pentest_type: Opt[str] = None
    scope: Opt[str] = None
    objectives: Opt[str] = None
    findings: list[dict] = []

class GenerateConclusionsRequest(BaseModel):
    project_title: str
    industry: Opt[str] = None
    pentest_type: Opt[str] = None
    findings: list[dict] = []


@router.post("/api/pentest/enrich-finding")
def enrich_finding(req: EnrichFindingRequest):
    from app.agents.pentest_agent import enrich_finding as _enrich
    result = _enrich(
        title=req.title,
        severity=req.severity,
        cvss_score=req.cvss_score,
        cvss_vector=req.cvss_vector,
        component=req.affected_component,
        industry=req.industry,
        project_title=req.project_title,
    )
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.post("/api/pentest/generate-summary")
def generate_summary(req: GenerateSummaryRequest):
    from app.agents.pentest_agent import generate_executive_summary as _gen
    result = _gen(
        project_title=req.project_title,
        industry=req.industry,
        pentest_type=req.pentest_type,
        scope=req.scope,
        objectives=req.objectives,
        findings=req.findings,
    )
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.post("/api/pentest/generate-conclusions")
def generate_conclusions(req: GenerateConclusionsRequest):
    from app.agents.pentest_agent import generate_conclusions as _gen
    result = _gen(
        project_title=req.project_title,
        industry=req.industry,
        pentest_type=req.pentest_type,
        findings=req.findings,
    )
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result
