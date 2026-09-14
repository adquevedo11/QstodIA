from __future__ import annotations

import os
from datetime import date, timedelta

import requests
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render

from dojo.models import Engagement

AGENT_URL = os.environ.get("GOLIVE_AGENT_URL", "http://localhost:8001")


def _go_live_date(eng: Engagement) -> str:
    if eng.target_end:
        return eng.target_end.isoformat()
    return (date.today() + timedelta(days=60)).isoformat()


@login_required
def go_live_readiness_view(request: HttpRequest, eid: int) -> HttpResponse:
    """Carga instantánea — solo muestra el spinner y el encabezado."""
    eng = get_object_or_404(Engagement, pk=eid)
    return render(request, "dojo/go_live_readiness.html", {
        "eng": eng,
        "product": eng.product,
    })


@login_required
def go_live_readiness_data(request: HttpRequest, eid: int) -> HttpResponse:
    """Llamada asíncrona que genera el reporte completo y devuelve HTML."""
    eng = get_object_or_404(Engagement, pk=eid)

    # Si se pide refresco forzado, invalidar caché del agente primero
    if request.GET.get("refresh") == "1":
        try:
            requests.delete(f"{AGENT_URL}/cache/{eng.id}", timeout=5)
        except Exception:
            pass

    payload = {
        "product_id": eng.product.id,
        "engagement_id": eng.id,
        "target_go_live_date": _go_live_date(eng),
    }

    error = None
    report = None

    try:
        resp = requests.post(
            f"{AGENT_URL}/readiness/analyze/defectdojo",
            json=payload,
            timeout=600,
        )
        resp.raise_for_status()
        report = resp.json()
    except requests.exceptions.ConnectionError:
        error = f"No se pudo conectar con el agente Go-Live Readiness en {AGENT_URL}."
    except requests.exceptions.Timeout:
        error = "El agente tardó demasiado en responder. Intenta de nuevo."
    except Exception as e:
        error = f"Error al generar el reporte: {e}"

    rec = (report or {}).get("overall_recommendation", "")
    rec_class = {
        "Go": "success",
        "No-Go": "danger",
        "Go condicionado": "warning",
    }.get(rec, "default")

    return render(request, "dojo/go_live_readiness_content.html", {
        "eng": eng,
        "product": eng.product,
        "report": report,
        "error": error,
        "rec_class": rec_class,
        "agent_url": AGENT_URL,
    })


@login_required
def go_live_readiness_pdf(request: HttpRequest, eid: int) -> HttpResponse:
    eng = get_object_or_404(Engagement, pk=eid)

    payload = {
        "product_id": eng.product.id,
        "engagement_id": eng.id,
        "target_go_live_date": _go_live_date(eng),
    }

    try:
        resp = requests.post(
            f"{AGENT_URL}/readiness/report/defectdojo/pdf",
            json=payload,
            timeout=600,
        )
        resp.raise_for_status()
        filename = f"go-live-readiness-eng{eng.id}.pdf"
        response = HttpResponse(resp.content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar el PDF: {e}", status=502)
