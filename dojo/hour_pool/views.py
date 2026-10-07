import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from dojo.models import Product, HourPool, TimeEntry, ActivityType, PentestProject
from dojo.hour_pool.forms import HourPoolForm, TimeEntryForm, ActivityTypeForm

logger = logging.getLogger(__name__)


@login_required
def hour_pool_list(request):
    pools = HourPool.objects.select_related('product', 'created_by').all()
    return render(request, 'dojo/hour_pool_list.html', {'pools': pools})


@login_required
def hour_pool_new(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == 'POST':
        form = HourPoolForm(request.POST)
        if form.is_valid():
            pool = form.save(commit=False)
            pool.product = product
            pool.created_by = request.user
            pool.save()
            messages.success(request, f'Bolsa "{pool.name}" creada.')
            return redirect('hour_pool_detail', pk=pool.pk)
    else:
        form = HourPoolForm(initial={'valid_from': date.today()})
    return render(request, 'dojo/hour_pool_form.html', {'form': form, 'product': product, 'action': 'Nueva'})


@login_required
def hour_pool_detail(request, pk):
    pool = get_object_or_404(HourPool.objects.select_related('product'), pk=pk)
    entries = pool.time_entries.select_related('analyst', 'activity_type', 'pentest_project').all()
    pentest_projects = PentestProject.objects.filter(engagement__product=pool.product)
    form = TimeEntryForm(initial={'analyst': request.user, 'date': date.today()})
    form.fields['pentest_project'].queryset = pentest_projects
    # Truncar labels del select para evitar que el dropdown rompa el layout
    return render(request, 'dojo/hour_pool_detail.html', {
        'pool': pool,
        'entries': entries,
        'form': form,
        'pentest_projects': pentest_projects,
    })


@login_required
def hour_pool_edit(request, pk):
    pool = get_object_or_404(HourPool, pk=pk)
    if request.method == 'POST':
        form = HourPoolForm(request.POST, instance=pool)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bolsa actualizada.')
            return redirect('hour_pool_detail', pk=pool.pk)
    else:
        form = HourPoolForm(instance=pool)
    return render(request, 'dojo/hour_pool_form.html', {'form': form, 'product': pool.product, 'pool': pool, 'action': 'Editar'})


@login_required
def hour_pool_delete(request, pk):
    pool = get_object_or_404(HourPool, pk=pk)
    product_id = pool.product_id
    if request.method == 'POST':
        pool.delete()
        messages.success(request, 'Bolsa eliminada.')
        return redirect('view_product', product_id)
    return render(request, 'dojo/hour_pool_confirm_delete.html', {'pool': pool})


@login_required
def time_entry_add(request, pool_id):
    pool = get_object_or_404(HourPool, pk=pool_id)
    pentest_projects = PentestProject.objects.filter(engagement__product=pool.product)
    if request.method == 'POST':
        form = TimeEntryForm(request.POST)
        form.fields['pentest_project'].queryset = pentest_projects
        if form.is_valid():
            hours = form.cleaned_data['hours']
            if hours > pool.remaining_hours:
                messages.error(request, f'No hay suficientes horas. Disponibles: {pool.remaining_hours}h.')
            else:
                entry = form.save(commit=False)
                entry.pool = pool
                entry.save()
                if pool.remaining_hours == 0:
                    pool.status = 'depleted'
                    pool.save()
                messages.success(request, f'{hours}h registradas correctamente.')
    return redirect('hour_pool_detail', pk=pool_id)


@login_required
def time_entry_delete(request, pk):
    entry = get_object_or_404(TimeEntry, pk=pk)
    pool_id = entry.pool_id
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Registro eliminado.')
        return redirect('hour_pool_detail', pk=pool_id)
    return render(request, 'dojo/time_entry_confirm_delete.html', {'entry': entry})


@login_required
def hour_pool_report_pdf(request, pk):
    pool = get_object_or_404(HourPool.objects.select_related('product'), pk=pk)
    entries = pool.time_entries.select_related('analyst', 'activity_type', 'pentest_project').all()

    from django.db.models import Sum
    by_activity = pool.time_entries.values('activity_type__name').annotate(total=Sum('hours')).order_by('-total')
    by_analyst = pool.time_entries.values('analyst__username').annotate(total=Sum('hours')).order_by('-total')

    return render(request, 'dojo/hour_pool_report_pdf.html', {
        'pool': pool,
        'entries': entries,
        'by_activity': by_activity,
        'by_analyst': by_analyst,
        'today': date.today(),
    })


@login_required
def activity_type_list(request):
    types = ActivityType.objects.all()
    form = ActivityTypeForm()
    if request.method == 'POST':
        form = ActivityTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de actividad creado.')
            return redirect('activity_type_list')
    return render(request, 'dojo/activity_type_list.html', {'activity_types': types, 'form': form})


@login_required
def activity_type_delete(request, pk):
    at = get_object_or_404(ActivityType, pk=pk)
    if request.method == 'POST':
        at.delete()
        messages.success(request, 'Tipo de actividad eliminado.')
    return redirect('activity_type_list')
