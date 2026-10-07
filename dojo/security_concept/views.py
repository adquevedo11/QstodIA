import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from dojo.authorization.roles_permissions import Permissions
from dojo.finding.queries import get_authorized_findings
from dojo.models import SecurityConcept

logger = logging.getLogger(__name__)

RISK_COLORS = {
    "Crítico":   "#c0392b",
    "Alto":      "#e67e22",
    "Medio":     "#d4ac0d",
    "Bajo":      "#2980b9",
    "Aceptable": "#27ae60",
}


def _build_report_context(data, findings_qs):
    risk_level = data.get("risk_level", "Medio")
    title = data.get("title", "Concepto de Seguridad")
    return {
        "report_name": f"Concepto de Seguridad — {title}",
        "reference":     data.get("reference", ""),
        "title":         title,
        "client":        data.get("client", ""),
        "scope":         data.get("scope", ""),
        "context_text":  data.get("context_text", ""),
        "analysis":      data.get("analysis", ""),
        "risk_level":    risk_level,
        "risk_color":    RISK_COLORS.get(risk_level, "#324458"),
        "conclusion":    data.get("conclusion", ""),
        "analyst_name":  data.get("analyst_name", ""),
        "analyst_title": data.get("analyst_title", ""),
        "findings":      findings_qs,
        "generated_date": datetime.now(),
    }


@login_required
def security_concept(request):
    """Formulario para crear un nuevo concepto de seguridad."""
    authorized_findings = (
        get_authorized_findings(Permissions.Finding_View)
        .select_related("test__engagement__product")
        .order_by("severity", "title")
    )

    if request.method == "POST":
        finding_ids = request.POST.getlist("findings")
        selected_findings = (
            authorized_findings.filter(id__in=finding_ids)
            if finding_ids
            else authorized_findings.none()
        )

        # Guardar en base de datos
        concept = SecurityConcept.objects.create(
            reference=request.POST.get("reference", ""),
            title=request.POST.get("title", "Sin título"),
            client=request.POST.get("client", ""),
            scope=request.POST.get("scope", ""),
            context_text=request.POST.get("context_text", ""),
            analysis=request.POST.get("analysis", ""),
            risk_level=request.POST.get("risk_level", "Medio"),
            conclusion=request.POST.get("conclusion", ""),
            analyst_name=request.POST.get(
                "analyst_name",
                request.user.get_full_name() or request.user.username,
            ),
            analyst_title=request.POST.get("analyst_title", ""),
            created_by=request.user,
        )
        concept.findings.set(selected_findings)

        context = _build_report_context(request.POST, selected_findings)
        context["concept_id"] = concept.id
        return render(request, "dojo/security_concept_report.html", context)

    context = {
        "findings": authorized_findings,
        "analyst_name": request.user.get_full_name() or request.user.username,
        "risk_levels": list(RISK_COLORS.keys()),
    }
    return render(request, "dojo/security_concept_form.html", context)


@login_required
def security_concept_list(request):
    """Historial de conceptos de seguridad emitidos."""
    concepts = SecurityConcept.objects.select_related("created_by").prefetch_related("findings")
    return render(request, "dojo/security_concept_list.html", {"concepts": concepts})


@login_required
def security_concept_view(request, pk):
    """Ver / re-generar el PDF de un concepto guardado."""
    concept = get_object_or_404(SecurityConcept, pk=pk)
    findings_qs = concept.findings.select_related("test__engagement__product").order_by("severity", "title")

    data = {
        "reference":     concept.reference,
        "title":         concept.title,
        "client":        concept.client,
        "scope":         concept.scope,
        "context_text":  concept.context_text,
        "analysis":      concept.analysis,
        "risk_level":    concept.risk_level,
        "conclusion":    concept.conclusion,
        "analyst_name":  concept.analyst_name,
        "analyst_title": concept.analyst_title,
    }
    context = _build_report_context(data, findings_qs)
    context["concept_id"] = concept.id
    context["generated_date"] = concept.created_at
    return render(request, "dojo/security_concept_report.html", context)


@login_required
def security_concept_delete(request, pk):
    """Eliminar un concepto del historial."""
    concept = get_object_or_404(SecurityConcept, pk=pk)
    if request.method == "POST":
        concept.delete()
        messages.success(request, "Concepto eliminado correctamente.")
    return redirect("security_concept_list")
