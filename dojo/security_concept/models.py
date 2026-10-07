from django.db import models

RISK_LEVEL_CHOICES = [
    ("Crítico",   "Crítico"),
    ("Alto",      "Alto"),
    ("Medio",     "Medio"),
    ("Bajo",      "Bajo"),
    ("Aceptable", "Aceptable"),
]


class SecurityConcept(models.Model):
    reference     = models.CharField(max_length=100, blank=True, verbose_name="Referencia")
    title         = models.CharField(max_length=500, verbose_name="Título")
    client        = models.CharField(max_length=300, blank=True, verbose_name="Cliente")
    scope         = models.CharField(max_length=500, blank=True, verbose_name="Alcance")
    context_text  = models.TextField(blank=True, verbose_name="Contexto")
    analysis      = models.TextField(blank=True, verbose_name="Análisis")
    risk_level    = models.CharField(max_length=50, choices=RISK_LEVEL_CHOICES, default="Medio", verbose_name="Nivel de riesgo")
    conclusion    = models.TextField(blank=True, verbose_name="Conclusión")
    analyst_name  = models.CharField(max_length=300, blank=True, verbose_name="Analista")
    analyst_title = models.CharField(max_length=300, blank=True, verbose_name="Cargo")
    findings      = models.ManyToManyField("dojo.Finding", blank=True, related_name="security_concepts", verbose_name="Hallazgos")
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    created_by    = models.ForeignKey(
        "dojo.Dojo_User", null=True, blank=True, on_delete=models.SET_NULL, related_name="security_concepts",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Concepto de Seguridad"
        verbose_name_plural = "Conceptos de Seguridad"

    def __str__(self):
        return f"{self.reference} — {self.title}" if self.reference else self.title
