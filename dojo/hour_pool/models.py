from django.db import models


class ActivityType(models.Model):
    name        = models.CharField(max_length=100, unique=True, verbose_name="Actividad")
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Tipo de Actividad"
        verbose_name_plural = "Tipos de Actividad"

    def __str__(self):
        return self.name


class HourPool(models.Model):
    STATUS_CHOICES = [
        ('active',    'Activa'),
        ('depleted',  'Agotada'),
        ('expired',   'Vencida'),
        ('cancelled', 'Cancelada'),
    ]

    product             = models.ForeignKey('dojo.Product', on_delete=models.CASCADE, related_name='hour_pools')
    name                = models.CharField(max_length=200, verbose_name="Nombre de la bolsa")
    total_hours         = models.PositiveIntegerField(verbose_name="Horas totales")
    alert_threshold_pct = models.PositiveIntegerField(default=20, verbose_name="Alerta al % restante")
    valid_from          = models.DateField(verbose_name="Válida desde")
    valid_until         = models.DateField(null=True, blank=True, verbose_name="Válida hasta")
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Estado")
    notes               = models.TextField(blank=True, verbose_name="Notas")
    created_by          = models.ForeignKey('dojo.Dojo_User', on_delete=models.SET_NULL, null=True, related_name='created_hour_pools')
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Bolsa de Horas"
        verbose_name_plural = "Bolsas de Horas"

    def __str__(self):
        return f"{self.name} — {self.product.name}"

    @property
    def used_hours(self):
        from django.db.models import Sum  # noqa: PLC0415 -- lazy import, avoids circular dependency
        result = self.time_entries.aggregate(total=Sum('hours'))['total']
        return result or 0

    @property
    def remaining_hours(self):
        return self.total_hours - self.used_hours

    @property
    def consumption_pct(self):
        if self.total_hours == 0:
            return 0
        return round((self.used_hours / self.total_hours) * 100, 1)

    @property
    def is_alert(self):
        threshold = self.total_hours * self.alert_threshold_pct / 100
        return self.remaining_hours <= threshold

    @property
    def status_color(self):
        if self.status == 'active':
            return '#27ae60' if not self.is_alert else '#e67e22'
        return {'depleted': '#c0392b', 'expired': '#7f8c8d', 'cancelled': '#bdc3c7'}.get(self.status, '#7f8c8d')


class TimeEntry(models.Model):
    pool            = models.ForeignKey("HourPool", on_delete=models.CASCADE, related_name='time_entries')
    pentest_project = models.ForeignKey('dojo.PentestProject', on_delete=models.SET_NULL, null=True, blank=True, related_name='time_entries')
    analyst         = models.ForeignKey('dojo.Dojo_User', on_delete=models.SET_NULL, null=True, related_name='time_entries')
    date            = models.DateField(verbose_name="Fecha")
    hours           = models.PositiveIntegerField(verbose_name="Horas")
    activity_type   = models.ForeignKey("ActivityType", on_delete=models.SET_NULL, null=True, verbose_name="Actividad")
    description     = models.TextField(blank=True, verbose_name="Descripción")
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Registro de Horas"
        verbose_name_plural = "Registros de Horas"

    def __str__(self):
        return f"{self.analyst} — {self.hours}h — {self.date}"
