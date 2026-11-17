from django.db import models


class LLMProvider(models.TextChoices):
    OPENAI       = "openai",       "OpenAI (GPT-4o, GPT-4, etc.)"
    AZURE_OPENAI = "azure_openai", "Azure OpenAI"
    ANTHROPIC    = "anthropic",    "Anthropic (Claude)"
    GEMINI       = "gemini",       "Google Gemini"
    OLLAMA       = "ollama",       "Ollama (auto-hospedado)"


class LLMConfig(models.Model):
    """
    Credenciales y parámetros para la integración con un proveedor LLM.
    Se gestiona desde /admin/ — solo un registro puede estar activo a la vez.
    """
    name     = models.CharField(max_length=100, verbose_name="Nombre",
                                help_text="Ej: OpenAI Producción, Azure Heinsohn")
    provider = models.CharField(max_length=20, choices=LLMProvider.choices,
                                verbose_name="Proveedor")
    api_key  = models.CharField(max_length=500, blank=True, verbose_name="API Key",
                                help_text="Dejar vacío para Ollama.")

    # Modelo / deployment
    model_name = models.CharField(max_length=200, verbose_name="Modelo",
                                  help_text=(
                                      "OpenAI: gpt-4o, gpt-4-turbo  |  "
                                      "Anthropic: claude-opus-5-5, claude-sonnet-5-5  |  "
                                      "Gemini: gemini-1.5-pro  |  "
                                      "Azure/Ollama: nombre del deployment o modelo local"
                                  ))

    # Campos opcionales según proveedor
    base_url        = models.CharField(max_length=500, blank=True, verbose_name="URL base / Endpoint",
                                       help_text="Azure: https://<resource>.openai.azure.com/  |  Ollama: http://localhost:11434")
    api_version     = models.CharField(max_length=50, blank=True, verbose_name="Versión API",
                                       help_text="Solo Azure OpenAI. Ej: 2024-02-01")
    deployment_name = models.CharField(max_length=200, blank=True, verbose_name="Nombre de deployment",
                                       help_text="Solo Azure OpenAI.")

    # Control
    is_active  = models.BooleanField(default=False, verbose_name="Activo",
                                     help_text="Solo puede haber un proveedor activo a la vez.")
    notes      = models.TextField(blank=True, verbose_name="Notas internas")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "llm_config"
        db_table  = "dojo_llmconfig"
        ordering  = ["-is_active", "name"]
        verbose_name = "Configuración LLM"
        verbose_name_plural = "Configuraciones LLM"

    def __str__(self):
        status = "ACTIVO" if self.is_active else "inactivo"
        return f"{self.name} [{self.get_provider_display()}] — {status}"

    def save(self, *args, **kwargs):
        # Solo un registro activo a la vez
        if self.is_active:
            LLMConfig.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()
