from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from dojo.license_manager.models import ClientLicense


@admin.register(ClientLicense)
class ClientLicenseAdmin(admin.ModelAdmin):
    list_display  = ('client_name', 'product_type', 'status_badge', 'expires_at', 'days_remaining_display', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('client_name', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'status_badge', 'days_remaining_display')
    list_editable = ('is_active',)

    fieldsets = (
        ('Cliente', {
            'fields': ('client_name', 'product_type', 'notes'),
        }),
        ('Control de acceso', {
            'fields': ('is_active', 'expires_at'),
            'description': 'Desactivar "Activa" bloquea el acceso inmediatamente, '
                           'independientemente de la fecha de expiración.',
        }),
        ('Estado', {
            'fields': ('status_badge', 'days_remaining_display', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Estado')
    def status_badge(self, obj):
        if not obj.is_active:
            return format_html('<span style="color:#b91c1c;font-weight:600">&#9679; Bloqueada manualmente</span>')
        if obj.is_expired:
            return format_html('<span style="color:#b91c1c;font-weight:600">&#9679; Expirada</span>')
        if obj.days_remaining <= 7:
            return format_html('<span style="color:#b45309;font-weight:600">&#9679; Por vencer ({} días)</span>', obj.days_remaining)
        return format_html('<span style="color:#15803d;font-weight:600">&#9679; Activa</span>')

    @admin.display(description='Días restantes')
    def days_remaining_display(self, obj):
        d = obj.days_remaining
        if d == 0:
            return 'Expirada'
        return f'{d} días'
