from django.db import models

EXEC_REPORT_CLASSIFICATION = [
    ('Confidencial', 'Confidencial'),
    ('Interno', 'Interno'),
    ('Público', 'Público'),
]


class ExecutiveReport(models.Model):
    product           = models.ForeignKey('dojo.Product', on_delete=models.CASCADE, related_name='executive_reports')
    engagements       = models.ManyToManyField('dojo.Engagement', blank=True, related_name='executive_reports')
    title             = models.CharField(max_length=500)
    period_start      = models.DateField()
    period_end        = models.DateField()
    classification    = models.CharField(max_length=50, choices=EXEC_REPORT_CLASSIFICATION, default='Confidencial')
    analyst_name      = models.CharField(max_length=300, blank=True)
    analyst_title     = models.CharField(max_length=300, blank=True)
    executive_summary = models.TextField(blank=True)
    recommendations   = models.TextField(blank=True)
    next_steps        = models.TextField(blank=True)
    conclusion        = models.TextField(blank=True)
    sections          = models.JSONField(default=dict)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)
    created_by        = models.ForeignKey(
        "dojo.Dojo_User", null=True, blank=True, on_delete=models.SET_NULL, related_name='executive_reports',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Informe Ejecutivo'
        verbose_name_plural = 'Informes Ejecutivos'

    def __str__(self):
        return f"{self.title} — {self.product.name}"
