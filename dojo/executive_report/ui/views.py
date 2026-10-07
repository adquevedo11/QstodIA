"""
Informe Ejecutivo — Módulo SQA VMaaS 2.0
Genera informes ejecutivos de seguridad con métricas calculadas en tiempo real.
"""
import json
import logging
from collections import defaultdict
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dojo.authorization.roles_permissions import Permissions
from dojo.finding.queries import get_authorized_findings
from dojo.models import Engagement, ExecutiveReport, Product
from dojo.product.queries import get_authorized_products

logger = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────────────────────
SEVERITIES = ['Critical', 'High', 'Medium', 'Low', 'Info']

SEV_ES = {
    'Critical': 'Crítico',
    'High': 'Alto',
    'Medium': 'Medio',
    'Low': 'Bajo',
    'Info': 'Informativo',
}

SEV_COLORS = {
    'Critical': '#c0392b',
    'High': '#e67e22',
    'Medium': '#d4ac0d',
    'Low': '#2980b9',
    'Info': '#6c757d',
}

RISK_WEIGHT = {'Critical': 10, 'High': 5, 'Medium': 2, 'Low': 1, 'Info': 0}
SLA_DAYS = {'Critical': 7, 'High': 30, 'Medium': 90, 'Low': 180}

SECTION_LABELS = {
    'cover':                 'Portada',
    'executive_summary':     'Resumen Ejecutivo',
    'risk_posture':          'Postura de Riesgo',
    'kpis':                  'KPIs Principales',
    'severity_distribution': 'Distribución por Severidad',
    'monthly_trend':         'Tendencia Mensual',
    'sla_compliance':        'Cumplimiento de SLA',
    'top_findings':          'Top Hallazgos Críticos/Altos',
    'remediated_findings':   'Hallazgos Remediados',
    'by_tool':               'Hallazgos por Herramienta',
    'security_concepts':     'Conceptos de Seguridad Emitidos',
    'conclusion':            'Conclusión',
    'recommendations':       'Recomendaciones',
    'next_steps':            'Próximos Pasos',
}

DEFAULT_SECTIONS = [
    'cover', 'executive_summary', 'risk_posture', 'kpis',
    'severity_distribution', 'top_findings', 'conclusion', 'recommendations',
]


# ── Helpers internos ─────────────────────────────────────────────────────────

def _safe_pct(part, total):
    return round(part / total * 100, 1) if total else 0


def _risk_label(score):
    if score >= 100:
        return ('Crítico', '#c0392b')
    if score >= 50:
        return ('Alto', '#e67e22')
    if score >= 20:
        return ('Medio', '#d4ac0d')
    if score > 0:
        return ('Bajo', '#2980b9')
    return ('Aceptable', '#27ae60')


def _compute_metrics(authorized_findings, product, engagement_ids, period_start, period_end):
    """
    Calcula todas las métricas ejecutivas para el producto/período indicado.
    Retorna un dict con todas las series de datos.
    """
    base_qs = authorized_findings.filter(test__engagement__product=product)
    if engagement_ids:
        base_qs = base_qs.filter(test__engagement_id__in=engagement_ids)

    active_qs = base_qs.filter(active=True, is_mitigated=False, false_p=False, duplicate=False)
    closed_qs = base_qs.filter(
        is_mitigated=True,
        mitigated__date__gte=period_start,
        mitigated__date__lte=period_end,
    )
    period_new_qs = base_qs.filter(date__gte=period_start, date__lte=period_end)

    total_active = active_qs.count()
    critical_count = active_qs.filter(severity='Critical').count()
    high_count = active_qs.filter(severity='High').count()
    medium_count = active_qs.filter(severity='Medium').count()
    low_count = active_qs.filter(severity='Low').count()
    closed_count = closed_qs.count()
    new_count = period_new_qs.count()
    remediation_rate = _safe_pct(closed_count, new_count + closed_count)

    # Score y etiqueta de riesgo
    risk_score = sum(
        active_qs.filter(severity=s).count() * w
        for s, w in RISK_WEIGHT.items()
    )
    risk_label, risk_color = _risk_label(risk_score)

    # ── Distribución por severidad ──
    sev_dist = {s: active_qs.filter(severity=s).count() for s in SEVERITIES}
    sev_chart = {
        'labels': [SEV_ES[s] for s in SEVERITIES],
        'data':   [sev_dist[s] for s in SEVERITIES],
        'colors': [SEV_COLORS[s] for s in SEVERITIES],
    }

    # ── Tendencia mensual (período seleccionado) ──
    monthly_new = (
        base_qs.filter(date__gte=period_start, date__lte=period_end)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    monthly_closed = (
        base_qs.filter(is_mitigated=True, mitigated__date__gte=period_start, mitigated__date__lte=period_end)
        .annotate(month=TruncMonth('mitigated'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    months_labels = []
    cur = period_start.replace(day=1)
    while cur <= period_end:
        months_labels.append(cur)
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    new_by_month = {
        (r['month'].date() if hasattr(r['month'], 'date') else r['month']): r['count']
        for r in monthly_new
    }
    closed_by_month = {
        (r['month'].date() if hasattr(r['month'], 'date') else r['month']): r['count']
        for r in monthly_closed
    }

    trend_chart = {
        'labels': [m.strftime('%b %Y') for m in months_labels],
        'new':    [new_by_month.get(m, 0) for m in months_labels],
        'closed': [closed_by_month.get(m, 0) for m in months_labels],
    }

    # ── MTTR y SLA ──
    mitigated_qs = base_qs.filter(
        is_mitigated=True,
        mitigated__isnull=False,
        mitigated__date__gte=period_start,
        mitigated__date__lte=period_end,
    )

    mttr_by_sev = {}
    for sev in ['Critical', 'High', 'Medium', 'Low']:
        subset = list(mitigated_qs.filter(severity=sev).values('date', 'mitigated')[:500])
        days_list = []
        for f in subset:
            if f['mitigated'] and f['date']:
                mit_date = f['mitigated'].date() if hasattr(f['mitigated'], 'date') else f['mitigated']
                diff = (mit_date - f['date']).days
                if diff >= 0:
                    days_list.append(diff)
        mttr_by_sev[sev] = round(sum(days_list) / len(days_list), 1) if days_list else 0

    sla_data = []
    for sev, threshold in SLA_DAYS.items():
        subset = list(mitigated_qs.filter(severity=sev).values('date', 'mitigated')[:1000])
        total = len(subset)
        within = 0
        for f in subset:
            if f['mitigated'] and f['date']:
                mit_date = f['mitigated'].date() if hasattr(f['mitigated'], 'date') else f['mitigated']
                if (mit_date - f['date']).days <= threshold:
                    within += 1
        sla_data.append({
            'severity':  SEV_ES[sev],
            'color':     SEV_COLORS[sev],
            'threshold': threshold,
            'pct':       _safe_pct(within, total),
            'within':    within,
            'total':     total,
        })

    # ── Top hallazgos críticos/altos ──
    top_findings_qs = (
        active_qs.filter(severity__in=['Critical', 'High'])
        .select_related('test__engagement')
        .order_by('severity', '-date')[:20]
    )
    today = date.today()
    top_findings_data = []
    for f in top_findings_qs:
        days_open = (today - f.date).days if f.date else 0
        top_findings_data.append({
            'id':        f.id,
            'title':     f.title,
            'severity':  f.severity,
            'sev_es':    SEV_ES.get(f.severity, f.severity),
            'sev_color': SEV_COLORS.get(f.severity, '#324458'),
            'date':      f.date,
            'days_open': days_open,
        })

    # ── Hallazgos remediados en el período ──
    remediated_data = []
    for f in closed_qs.select_related('test__engagement').order_by('-mitigated')[:20]:
        mitigated_date = f.mitigated.date() if f.mitigated and hasattr(f.mitigated, 'date') else f.mitigated
        remediated_data.append({
            'id':            f.id,
            'title':         f.title,
            'severity':      f.severity,
            'sev_es':        SEV_ES.get(f.severity, f.severity),
            'sev_color':     SEV_COLORS.get(f.severity, '#324458'),
            'date':          f.date,
            'mitigated':     mitigated_date,
        })

    # ── Por herramienta/scanner ──
    tool_qs = (
        base_qs.filter(date__gte=period_start, date__lte=period_end)
        .values('test__test_type__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    by_tool_data = [
        {'tool': r['test__test_type__name'] or 'Sin tipo', 'count': r['count']}
        for r in tool_qs
    ]

    return {
        'total_active':      total_active,
        'critical_count':    critical_count,
        'high_count':        high_count,
        'medium_count':      medium_count,
        'low_count':         low_count,
        'closed_count':      closed_count,
        'new_count':         new_count,
        'remediation_rate':  remediation_rate,
        'risk_score':        risk_score,
        'risk_label':        risk_label,
        'risk_color':        risk_color,
        'sev_dist':          sev_dist,
        'sev_chart':         sev_chart,
        'trend_chart':       trend_chart,
        'mttr_by_sev':       mttr_by_sev,
        'sla_data':          sla_data,
        'top_findings_data': top_findings_data,
        'remediated_data':   remediated_data,
        'by_tool_data':      by_tool_data,
    }


# ── Vistas ───────────────────────────────────────────────────────────────────

@login_required
def executive_report_list(request):
    """Lista todos los informes ejecutivos."""
    reports = (
        ExecutiveReport.objects
        .select_related('product', 'created_by')
        .prefetch_related('engagements')
        .order_by('-created_at')
    )
    return render(request, 'dojo/executive_report_list.html', {'reports': reports})


@login_required
def executive_report_new(request):
    """Formulario para crear un nuevo informe ejecutivo."""
    authorized_findings = get_authorized_findings(Permissions.Finding_View)
    products = get_authorized_products(Permissions.Product_View).order_by('name')

    if request.method == 'POST':
        product_id = request.POST.get('product_id', '')
        engagement_ids = [int(x) for x in request.POST.getlist('engagement_ids') if x.isdigit()]
        period_start_str = request.POST.get('period_start', '')
        period_end_str = request.POST.get('period_end', '')
        selected_sections = request.POST.getlist('sections')

        # Validaciones básicas
        if not product_id or not period_start_str or not period_end_str:
            messages.error(request, 'Producto y período son obligatorios.')
            return render(request, 'dojo/executive_report_form.html', {
                'products': products,
                'section_labels': SECTION_LABELS,
                'default_sections': DEFAULT_SECTIONS,
            })

        try:
            product = products.get(id=int(product_id))
            from datetime import datetime
            period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
            period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
        except (Product.DoesNotExist, ValueError):
            messages.error(request, 'Producto o fechas inválidos.')
            return render(request, 'dojo/executive_report_form.html', {
                'products': products,
                'section_labels': SECTION_LABELS,
                'default_sections': DEFAULT_SECTIONS,
            })

        if not selected_sections:
            selected_sections = DEFAULT_SECTIONS

        report = ExecutiveReport.objects.create(
            product=product,
            title=request.POST.get('title', f'Informe Ejecutivo — {product.name}'),
            period_start=period_start,
            period_end=period_end,
            classification=request.POST.get('classification', 'Confidencial'),
            analyst_name=request.POST.get('analyst_name', request.user.get_full_name() or request.user.username),
            analyst_title=request.POST.get('analyst_title', ''),
            executive_summary=request.POST.get('executive_summary', ''),
            recommendations=request.POST.get('recommendations', ''),
            next_steps=request.POST.get('next_steps', ''),
            conclusion=request.POST.get('conclusion', ''),
            sections={'active': selected_sections},
            created_by=request.user,
        )

        if engagement_ids:
            engagements = Engagement.objects.filter(id__in=engagement_ids, product=product)
            report.engagements.set(engagements)

        return redirect('executive_report_view', pk=report.pk)

    context = {
        'products': products,
        'section_labels': SECTION_LABELS,
        'default_sections': DEFAULT_SECTIONS,
        'analyst_name': request.user.get_full_name() or request.user.username,
        'classifications': [c[0] for c in [('Confidencial', ''), ('Interno', ''), ('Público', '')]],
    }
    return render(request, 'dojo/executive_report_form.html', context)


@login_required
def executive_report_view(request, pk):
    """Renderiza el PDF del informe ejecutivo guardado."""
    report = get_object_or_404(ExecutiveReport, pk=pk)
    authorized_findings = get_authorized_findings(Permissions.Finding_View)

    engagement_ids = list(report.engagements.values_list('id', flat=True))
    metrics = _compute_metrics(
        authorized_findings,
        report.product,
        engagement_ids,
        report.period_start,
        report.period_end,
    )

    # Conceptos de seguridad del producto
    try:
        from dojo.models import SecurityConcept
        security_concepts = SecurityConcept.objects.filter(
            findings__test__engagement__product=report.product
        ).distinct().order_by('-created_at')[:10]
    except Exception:
        security_concepts = []

    sections = report.sections.get('active', DEFAULT_SECTIONS) if report.sections else DEFAULT_SECTIONS

    context = {
        'report': report,
        'sections': sections,
        'section_labels': SECTION_LABELS,
        'generated_date': report.created_at,
        # KPIs
        'total_active':     metrics['total_active'],
        'critical_count':   metrics['critical_count'],
        'high_count':       metrics['high_count'],
        'medium_count':     metrics['medium_count'],
        'low_count':        metrics['low_count'],
        'closed_count':     metrics['closed_count'],
        'new_count':        metrics['new_count'],
        'remediation_rate': metrics['remediation_rate'],
        # Postura
        'risk_score':  metrics['risk_score'],
        'risk_label':  metrics['risk_label'],
        'risk_color':  metrics['risk_color'],
        # Gráficas JSON
        'sev_chart_json':   json.dumps(metrics['sev_chart']),
        'trend_chart_json': json.dumps(metrics['trend_chart']),
        # Tablas
        'sla_data':          metrics['sla_data'],
        'top_findings_data': metrics['top_findings_data'],
        'remediated_data':   metrics['remediated_data'],
        'by_tool_data':      metrics['by_tool_data'],
        'mttr_by_sev':       metrics['mttr_by_sev'],
        'security_concepts': security_concepts,
        # Lista pre-procesada por severidad (Django no soporta dict[variable] en templates)
        'sev_table': [
            {
                'key':   s,
                'label': SEV_ES[s],
                'color': SEV_COLORS[s],
                'count': metrics['sev_dist'].get(s, 0),
                'pct':   _safe_pct(metrics['sev_dist'].get(s, 0), metrics['total_active']),
            }
            for s in SEVERITIES
        ],
        'sla_days':    SLA_DAYS,
    }
    return render(request, 'dojo/executive_report_pdf.html', context)


@login_required
def executive_report_delete(request, pk):
    """Elimina un informe ejecutivo."""
    report = get_object_or_404(ExecutiveReport, pk=pk)
    if request.method == 'POST':
        report.delete()
        messages.success(request, 'Informe ejecutivo eliminado correctamente.')
    return redirect('executive_report_list')


@login_required
def executive_report_engagements(request):
    """AJAX: retorna los engagements de un producto."""
    product_id = request.GET.get('product_id', '')
    if not product_id:
        return JsonResponse({'engagements': []})

    try:
        products = get_authorized_products(Permissions.Product_View)
        product = products.get(id=int(product_id))
    except (Product.DoesNotExist, ValueError):
        return JsonResponse({'engagements': []})

    engagements = (
        Engagement.objects
        .filter(product=product)
        .order_by('-target_start')
        .values('id', 'name', 'target_start', 'target_end', 'status')
    )
    data = [
        {
            'id': e['id'],
            'name': e['name'] or f"Engagement #{e['id']}",
            'start': str(e['target_start']) if e['target_start'] else '',
            'end': str(e['target_end']) if e['target_end'] else '',
            'status': e['status'] or '',
        }
        for e in engagements
    ]
    return JsonResponse({'engagements': data})


@login_required
def executive_report_generate_summary(request):
    """AJAX POST: genera resumen ejecutivo automático en español."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    product_id = request.POST.get('product_id', '')
    engagement_ids = [int(x) for x in request.POST.getlist('engagement_ids[]') if x.isdigit()]
    period_start_str = request.POST.get('period_start', '')
    period_end_str = request.POST.get('period_end', '')

    if not product_id or not period_start_str or not period_end_str:
        return JsonResponse({'error': 'Faltan parámetros obligatorios.'}, status=400)

    try:
        products = get_authorized_products(Permissions.Product_View)
        product = products.get(id=int(product_id))
        from datetime import datetime
        period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
        period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
    except (Product.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Producto o fechas inválidos.'}, status=400)

    authorized_findings = get_authorized_findings(Permissions.Finding_View)
    metrics = _compute_metrics(authorized_findings, product, engagement_ids, period_start, period_end)

    start_fmt = period_start.strftime('%d de %B de %Y')
    end_fmt = period_end.strftime('%d de %B de %Y')
    total_active = metrics['total_active']
    critical = metrics['critical_count']
    high = metrics['high_count']
    rate = metrics['remediation_rate']
    risk_label = metrics['risk_label']
    risk_score = metrics['risk_score']
    mttr_critical = metrics['mttr_by_sev'].get('Critical', 0)

    critical_note = (
        'Se requiere atención inmediata sobre los hallazgos críticos identificados.'
        if critical > 0
        else 'No se registran hallazgos críticos activos en el período evaluado.'
    )

    summary = (
        f"Durante el período comprendido entre el {start_fmt} y el {end_fmt}, se realizó la evaluación "
        f"de seguridad del producto {product.name}. Se identificaron {total_active} hallazgos activos, "
        f"de los cuales {critical} corresponden a severidad Crítica y {high} a severidad Alta, "
        f"representando los riesgos más prioritarios para la organización.\n\n"
        f"La tasa de remediación del período alcanzó el {rate}%, con un tiempo medio de remediación "
        f"(MTTR) de {mttr_critical} días para hallazgos críticos. La postura de riesgo global se "
        f"clasifica como {risk_label}, con un score ponderado de {risk_score} puntos.\n\n"
        f"{critical_note}"
    )

    return JsonResponse({'summary': summary})


@login_required
def executive_report_generate_ia(request):
    """AJAX POST: auto-genera recomendaciones, próximos pasos o conclusión basándose en métricas."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    section = request.POST.get('section', '')
    if section not in ('recommendations', 'next_steps', 'conclusion'):
        return JsonResponse({'error': 'Sección no válida.'}, status=400)

    product_id = request.POST.get('product_id', '')
    engagement_ids = [int(x) for x in request.POST.getlist('engagement_ids[]') if x.isdigit()]
    period_start_str = request.POST.get('period_start', '')
    period_end_str = request.POST.get('period_end', '')

    if not product_id or not period_start_str or not period_end_str:
        return JsonResponse({'error': 'Faltan parámetros obligatorios.'}, status=400)

    try:
        products = get_authorized_products(Permissions.Product_View)
        product = products.get(id=int(product_id))
        from datetime import datetime
        period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
        period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
    except (Product.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Producto o fechas inválidos.'}, status=400)

    authorized_findings = get_authorized_findings(Permissions.Finding_View)
    m = _compute_metrics(authorized_findings, product, engagement_ids, period_start, period_end)

    critical = m['critical_count']
    high = m['high_count']
    medium = m['medium_count']
    low = m['low_count']
    total_active = m['total_active']
    closed_count = m['closed_count']
    new_count = m['new_count']
    rate = m['remediation_rate']
    risk_label = m['risk_label']
    risk_score = m['risk_score']
    mttr_c = m['mttr_by_sev'].get('Critical', 0)
    mttr_h = m['mttr_by_sev'].get('High', 0)
    mttr_m = m['mttr_by_sev'].get('Medium', 0)
    start_fmt = period_start.strftime('%d de %B de %Y')
    end_fmt = period_end.strftime('%d de %B de %Y')

    # SLA: porcentaje de cumplimiento por severidad
    sla_by_sev = {d['severity']: d['pct'] for d in m['sla_data']}
    sla_critico = sla_by_sev.get('Crítico', 0)
    sla_alto = sla_by_sev.get('Alto', 0)

    # Top hallazgo más antiguo
    oldest_days = m['top_findings_data'][0]['days_open'] if m['top_findings_data'] else 0
    oldest_title = m['top_findings_data'][0]['title'] if m['top_findings_data'] else ''

    if section == 'recommendations':
        lines = []
        if critical > 0:
            lines.append(
                f"- Priorizar la remediación inmediata de los {critical} hallazgo(s) de severidad Crítica "
                f"activos, cuyo MTTR actual es de {mttr_c} días frente al SLA de 7 días establecido."
            )
        if high > 0:
            lines.append(
                f"- Gestionar los {high} hallazgo(s) de severidad Alta dentro del plazo SLA de 30 días "
                f"(MTTR actual: {mttr_h} días). Asignar responsables y fechas de entrega concretas."
            )
        if medium > 0:
            lines.append(
                f"- Planificar la remediación de los {medium} hallazgo(s) de severidad Media en un plan "
                f"de trabajo de corto a mediano plazo, respetando el SLA de 90 días."
            )
        if rate < 50:
            lines.append(
                f"- Fortalecer el proceso de remediación: la tasa actual del {rate}% indica que más de la "
                f"mitad de los hallazgos nuevos no se están cerrando en el período. Se recomienda revisar "
                f"la capacidad del equipo y los flujos de trabajo."
            )
        if sla_critico < 80 and critical > 0:
            lines.append(
                f"- Revisar y reforzar el proceso de atención de incidentes críticos: solo el {sla_critico}% "
                f"de los hallazgos críticos se remedió dentro del SLA. Implementar alertas automáticas y "
                f"escalamiento temprano."
            )
        lines.append(
            "- Mantener una cadencia de revisión periódica de hallazgos con los equipos responsables, "
            "garantizando trazabilidad y seguimiento efectivo del plan de remediación."
        )
        text = '\n'.join(lines)

    elif section == 'next_steps':
        steps = []
        if critical > 0:
            steps.append(
                f"- [Inmediato — Equipo de Seguridad] Iniciar plan de remediación urgente para los "
                f"{critical} hallazgo(s) críticos activos. Definir responsable, fecha límite y plan de "
                f"mitigación provisional si la corrección definitiva requiere más tiempo."
            )
        if high > 0:
            steps.append(
                f"- [Corto plazo — Área de TI y Seguridad] Planificar la remediación de los {high} "
                f"hallazgo(s) altos dentro de los próximos 30 días, alineados al SLA definido."
            )
        steps.append(
            f"- [Corto plazo — Equipo de Seguridad] Revisar los hallazgos con mayor tiempo de exposición "
            + (f"(el más antiguo lleva {oldest_days} días abierto) " if oldest_days > 30 else "")
            + "y escalar aquellos que superen el SLA correspondiente."
        )
        steps.append(
            "- [Mediano plazo — Gerencia de TI] Establecer un comité de seguimiento quincenal de "
            "vulnerabilidades que incluya reporte de avance, bloqueos y fechas comprometidas de cierre."
        )
        steps.append(
            f"- [Mediano plazo — Equipo de Seguridad] Mantener la cobertura de escaneo continuo sobre "
            f"los activos del producto {product.name} y documentar los resultados en el próximo ciclo."
        )
        steps.append(
            "- [Largo plazo — Dirección] Evaluar la incorporación de métricas de seguridad en los "
            "indicadores de desempeño del área de TI para reforzar la cultura de seguridad organizacional."
        )
        text = '\n'.join(steps)

    else:  # conclusion
        if risk_score == 0:
            postura_frase = (
                f"La postura de seguridad del producto {product.name} se encuentra en un nivel Aceptable "
                f"durante el período evaluado, sin hallazgos activos que representen riesgo significativo."
            )
        else:
            postura_frase = (
                f"La postura de seguridad del producto {product.name} se clasifica como {risk_label} "
                f"(score ponderado: {risk_score}) durante el período comprendido entre el {start_fmt} "
                f"y el {end_fmt}."
            )

        if closed_count > 0 and rate >= 50:
            logro_frase = (
                f"Se destaca positivamente la remediación de {closed_count} hallazgo(s) en el período, "
                f"alcanzando una tasa de remediación del {rate}%, lo que refleja un esfuerzo sostenido "
                f"del equipo responsable."
            )
        elif closed_count > 0:
            logro_frase = (
                f"Se cerraron {closed_count} hallazgo(s) durante el período, con una tasa de remediación "
                f"del {rate}%. Este indicador requiere atención para alcanzar niveles óptimos de gestión."
            )
        else:
            logro_frase = (
                "No se registraron cierres de hallazgos en el período evaluado, lo que representa una "
                "oportunidad de mejora urgente en la gestión del ciclo de vida de vulnerabilidades."
            )

        if critical > 0 or high > 0:
            riesgo_frase = (
                f"Persisten {critical + high} hallazgo(s) de severidad Crítica o Alta sin remediar, "
                f"los cuales representan el mayor riesgo residual para la organización y requieren "
                f"atención prioritaria en el próximo ciclo."
            )
        else:
            riesgo_frase = (
                "No se registran hallazgos de severidad Crítica o Alta activos, lo que indica una "
                "gestión adecuada de los riesgos de mayor impacto."
            )

        text = f"{postura_frase}\n\n{logro_frase}\n\n{riesgo_frase}"

    return JsonResponse({'text': text})
