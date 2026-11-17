from django.contrib import admin
from django.forms import PasswordInput
from django.utils.html import format_html

from dojo.llm_config.models import LLMConfig, LLMProvider


@admin.register(LLMConfig)
class LLMConfigAdmin(admin.ModelAdmin):
    list_display  = ("name", "provider_badge", "model_name", "status_badge", "is_active", "updated_at")
    list_filter   = ("provider", "is_active")
    search_fields = ("name", "model_name", "notes")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at", "status_badge")

    fieldsets = (
        ("Identificación", {
            "fields": ("name", "is_active", "notes"),
        }),
        ("Proveedor y modelo", {
            "fields": ("provider", "model_name"),
            "description": (
                "Seleccione el proveedor y escriba el nombre exacto del modelo. "
                "Ejemplos — OpenAI: <code>gpt-4o</code> · "
                "Anthropic: <code>claude-sonnet-5-5</code> · "
                "Gemini: <code>gemini-1.5-pro</code>"
            ),
        }),
        ("Credenciales", {
            "fields": ("api_key",),
            "description": "La API Key se almacena en la base de datos. Dejar vacío para Ollama.",
            "classes": ("collapse",),
        }),
        ("Parámetros avanzados (Azure / Ollama)", {
            "fields": ("base_url", "api_version", "deployment_name"),
            "description": (
                "<b>Azure OpenAI:</b> completar los tres campos. "
                "<b>Ollama:</b> solo URL base (ej: http://localhost:11434). "
                "Dejar vacío para los demás proveedores."
            ),
            "classes": ("collapse",),
        }),
        ("Auditoría", {
            "fields": ("status_badge", "created_at", "updated_at"),
        }),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "api_key":
            kwargs["widget"] = PasswordInput(render_value=True)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.display(description="Proveedor")
    def provider_badge(self, obj):
        colors = {
            LLMProvider.OPENAI:       ("#10a37f", "OpenAI"),
            LLMProvider.AZURE_OPENAI: ("#0078d4", "Azure OpenAI"),
            LLMProvider.ANTHROPIC:    ("#c47a3c", "Anthropic"),
            LLMProvider.GEMINI:       ("#4285f4", "Gemini"),
            LLMProvider.OLLAMA:       ("#555", "Ollama"),
        }
        color, label = colors.get(obj.provider, ("#888", obj.provider))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{}</span>',
            color, label,
        )

    @admin.display(description="Estado")
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#15803d;font-weight:600">&#9679; Activo</span>')
        return format_html('<span style="color:#9ca3af;font-weight:600">&#9675; Inactivo</span>')
