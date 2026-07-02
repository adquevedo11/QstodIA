"""
Métricas SQA — Panel ejecutivo para CISO y administradores.
"""
import json
import logging
from collections import defaultdict
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from dojo.authorization.roles_permissions import Permissions
from dojo.finding.queries import get_authorized_findings
from dojo.models import Finding
from dojo.product.queries import get_authorized_products

logger = logging.getLogger(__name__)

# ── Constantes ──────────────────────────────────────────────────────────────
SEVERITIES = ["Critical", "High", "Medium", "Low", "Info"]

SEV_ES = {
    "Critical": "Crítico",
    "High": "Alto",
    "Medium": "Medio",
    "Low": "Bajo",
    "Info": "Informativo",
}

SEV_COLORS = {
    "Critical": "#c0392b",
    "High":     "#e67e22",
    "Medium":   "#d4ac0d",
    "Low":      "#2980b9",
    "Info":     "#6c757d",
}

# SLA en días por severidad
SLA_DAYS = {"Critical": 7, "High": 30, "Medium": 90, "Low": 180}

# Peso para score de riesgo
RISK_WEIGHT = {"Critical": 10, "High": 5, "Medium": 2, "Low": 1, "Info": 0}

PERIOD_OPTIONS = [
    ("1m",  "Último mes"),
    ("3m",  "Últimos 3 meses"),
    ("6m",  "Últimos 6 meses"),
    ("12m", "Último año"),
    ("all", "Todo el tiempo"),
]


def _date_from(period: str) -> date | None:
    today = date.today()
    mapping = {"1m": 30, "3m": 90, "6m": 180, "12m": 365}
    if period in mapping:
        return today - timedelta(days=mapping[period])
    return None  # "all"


def _safe_pct(part, total):
    return round(part / total * 100, 1) if total else 0


def _risk_label(score):
    if score >= 100:
        return ("Crítico", "#c0392b")
    if score >= 50:
        return ("Alto", "#e67e22")
    if score >= 20:
        return ("Medio", "#d4ac0d")
    if score > 0:
        return ("Bajo", "#2980b9")
    return ("Aceptable", "#27ae60")


# ── Vista principal ──────────────────────────────────────────────────────────
@login_required
def sqa_metrics(request):
    period = request.GET.get("period", "3m")
    product_id = request.GET.get("product_id", "")
    d_from = _date_from(period)

    # Base querysets — respeta permisos
    all_findings = get_authorized_findings(Permissions.Finding_View)
    products = get_authorized_products(Permissions.Product_View).order_by("name")

    if product_id:
        all_findings = all_findings.filter(
            test__engagement__product_id=product_id
        )

    # Rango temporal
    if d_from:
        period_findings = all_findings.filter(date__gte=d_from)
    else:
        period_findings = all_findings

    # ── KPIs ────────────────────────────────────────────────────────────────
    active_qs = period_findings.filter(active=True, is_mitigated=False, false_p=False, duplicate=False)
    total_active = active_qs.count()
    critical_count = active_qs.filter(severity="Critical").count()
    high_count = active_qs.filter(severity="High").count()

    if d_from:
        closed_qs = all_findings.filter(
            is_mitigated=True,
            mitigated__date__gte=d_from
        )
        new_qs = all_findings.filter(date__gte=d_from)
    else:
        closed_qs = all_findings.filter(is_mitigated=True)
        new_qs = all_findings

    closed_count = closed_qs.count()
    new_count = new_qs.count()
    remediation_rate = _safe_pct(closed_count, new_count + closed_count)

    # ── Score de postura de riesgo ───────────────────────────────────────────
    risk_score = sum(
        active_qs.filter(severity=s).count() * w
        for s, w in RISK_WEIGHT.items()
    )
    risk_label, risk_color = _risk_label(risk_score)

    # ── Distribución por severidad ───────────────────────────────────────────
    sev_dist = {}
    for s in SEVERITIES:
        sev_dist[s] = active_qs.filter(severity=s).count()

    sev_chart = {
        "labels": [SEV_ES[s] for s in SEVERITIES],
        "data":   [sev_dist[s] for s in SEVERITIES],
        "colors": [SEV_COLORS[s] for s in SEVERITIES],
    }

    # ── Tendencia mensual (últimos 6 meses siempre) ──────────────────────────
    six_months_ago = date.today() - timedelta(days=180)
    monthly_base = all_findings.filter(date__gte=six_months_ago)
    if product_id:
        monthly_base = monthly_base.filter(test__engagement__product_id=product_id)

    monthly_new = (
        monthly_base
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    monthly_closed = (
        all_findings
        .filter(is_mitigated=True, mitigated__date__gte=six_months_ago)
        .annotate(month=TruncMonth("mitigated"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    if product_id:
        monthly_closed = monthly_closed.filter(test__engagement__product_id=product_id)

    # Construir meses del eje X
    months_labels = []
    cur = six_months_ago.replace(day=1)
    while cur <= date.today():
        months_labels.append(cur)
        # siguiente mes
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    new_by_month = {r["month"].date() if hasattr(r["month"], "date") else r["month"]: r["count"]
                    for r in monthly_new}
    closed_by_month = {r["month"].date() if hasattr(r["month"], "date") else r["month"]: r["count"]
                       for r in monthly_closed}

    trend_chart = {
        "labels":  [m.strftime("%b %Y") for m in months_labels],
        "new":     [new_by_month.get(m, 0) for m in months_labels],
        "closed":  [closed_by_month.get(m, 0) for m in months_labels],
    }

    # ── MTTR por severidad ───────────────────────────────────────────────────
    mttr_chart_labels = []
    mttr_chart_data = []
    mttr_chart_colors = []

    mitigated_qs = all_findings.filter(is_mitigated=True, mitigated__isnull=False)
    if d_from:
        mitigated_qs = mitigated_qs.filter(date__gte=d_from)
    if product_id:
        mitigated_qs = mitigated_qs.filter(test__engagement__product_id=product_id)

    for sev in ["Critical", "High", "Medium", "Low"]:
        subset = list(
            mitigated_qs.filter(severity=sev).values("date", "mitigated")[:500]
        )
        days_list = []
        for f in subset:
            if f["mitigated"] and f["date"]:
                mit_date = f["mitigated"].date() if hasattr(f["mitigated"], "date") else f["mitigated"]
                disc_date = f["date"]
                diff = (mit_date - disc_date).days
                if diff >= 0:
                    days_list.append(diff)
        avg = round(sum(days_list) / len(days_list), 1) if days_list else 0
        mttr_chart_labels.append(SEV_ES[sev])
        mttr_chart_data.append(avg)
        mttr_chart_colors.append(SEV_COLORS[sev])

    mttr_chart = {
        "labels": mttr_chart_labels,
        "data":   mttr_chart_data,
        "colors": mttr_chart_colors,
        "sla":    [SLA_DAYS["Critical"], SLA_DAYS["High"], SLA_DAYS["Medium"], SLA_DAYS["Low"]],
    }

    # ── Cumplimiento de SLA ──────────────────────────────────────────────────
    sla_data = []
    for sev, threshold in SLA_DAYS.items():
        subset = list(
            mitigated_qs.filter(severity=sev).values("date", "mitigated")[:1000]
        )
        total = len(subset)
        within = 0
        for f in subset:
            if f["mitigated"] and f["date"]:
                mit_date = f["mitigated"].date() if hasattr(f["mitigated"], "date") else f["mitigated"]
                if (mit_date - f["date"]).days <= threshold:
                    within += 1
        pct = _safe_pct(within, total)
        sla_data.append({
            "severity":  SEV_ES[sev],
            "color":     SEV_COLORS[sev],
            "threshold": threshold,
            "pct":       pct,
            "within":    within,
            "total":     total,
        })

    # ── Top 5 productos por riesgo ───────────────────────────────────────────
    top_products = []
    for p in products[:50]:
        pf = active_qs.filter(test__engagement__product=p)
        score = sum(pf.filter(severity=s).count() * w for s, w in RISK_WEIGHT.items())
        if score == 0:
            continue
        counts = {s: pf.filter(severity=s).count() for s in SEVERITIES}
        top_products.append({
            "name":     p.name,
            "score":    score,
            "counts":   counts,
            "total":    pf.count(),
            "label":    _risk_label(score)[0],
            "color":    _risk_label(score)[1],
        })
    top_products.sort(key=lambda x: x["score"], reverse=True)
    top_products = top_products[:8]

    top_products_chart = {
        "labels": [p["name"][:30] for p in top_products],
        "scores": [p["score"] for p in top_products],
        "colors": [p["color"] for p in top_products],
    }

    # ── Hallazgos por herramienta/scanner ───────────────────────────────────
    tool_qs = (
        period_findings
        .values("test__test_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    tool_chart = {
        "labels": [r["test__test_type__name"] or "Sin tipo" for r in tool_qs],
        "data":   [r["count"] for r in tool_qs],
        "colors": ["#324458"] * len(list(tool_qs)),
    }
    # Re-query because tool_qs is consumed
    tool_qs2 = (
        period_findings
        .values("test__test_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    tool_chart = {
        "labels": [r["test__test_type__name"] or "Sin tipo" for r in tool_qs2],
        "data":   [r["count"] for r in tool_qs2],
    }

    # ── Reaberturas ─────────────────────────────────────────────────────────
    # DefectDojo tracks duplicates; reopened approximated by mitigated=False + was_mitigated
    reopened_count = period_findings.filter(
        active=True, is_mitigated=False,
        mitigated__isnull=False  # had a mitigated date but active again
    ).count()

    context = {
        # Filtros
        "period":          period,
        "period_options":  PERIOD_OPTIONS,
        "products":        products,
        "selected_product_id": product_id,
        # KPIs
        "total_active":      total_active,
        "critical_count":    critical_count,
        "high_count":        high_count,
        "closed_count":      closed_count,
        "new_count":         new_count,
        "remediation_rate":  remediation_rate,
        "reopened_count":    reopened_count,
        # Postura
        "risk_score":  risk_score,
        "risk_label":  risk_label,
        "risk_color":  risk_color,
        # Gráficas (JSON para Chart.js)
        "sev_chart_json":          json.dumps(sev_chart),
        "trend_chart_json":        json.dumps(trend_chart),
        "mttr_chart_json":         json.dumps(mttr_chart),
        "top_products_chart_json": json.dumps(top_products_chart),
        "tool_chart_json":         json.dumps(tool_chart),
        # Tablas
        "sla_data":     sla_data,
        "top_products": top_products,
        # Lista pre-procesada para el template (Django no soporta dict[variable])
        "sev_postura": [
            {"label": SEV_ES[s], "color": SEV_COLORS[s], "count": sev_dist[s]}
            for s in SEVERITIES
            if sev_dist[s] > 0
        ],
        "d_from":       d_from,
    }
    return render(request, "dojo/sqa_metrics.html", context)
