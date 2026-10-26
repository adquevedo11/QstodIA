from django.db import models
from django.utils import timezone


class ClientLicense(models.Model):
    """
    Controla el acceso de un cliente al sistema QustodIA.
    Gestionado desde /admin/ por el superadmin de SQA SA.
    """
    client_name  = models.CharField(max_length=200, verbose_name="Nombre del cliente")
    product_type = models.OneToOneField(
        'dojo.Product_Type',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='license',
        verbose_name="Product Type asociado",
        help_text="Si se asigna, solo los usuarios de ese Product Type son afectados por esta licencia.",
    )
    is_active    = models.BooleanField(default=True, verbose_name="Activa",
                                       help_text="Desactivar bloquea inmediatamente el acceso del cliente.")
    expires_at   = models.DateTimeField(verbose_name="Expira el",
                                        help_text="Fecha y hora de expiración del PoC.")
    notes        = models.TextField(blank=True, verbose_name="Notas internas")
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "license_manager"
        db_table = "dojo_clientlicense"
        ordering = ["expires_at"]
        verbose_name = "Licencia de cliente"
        verbose_name_plural = "Licencias de clientes"

    def __str__(self):
        status = "ACTIVA" if self.is_active and not self.is_expired else "BLOQUEADA"
        return f"{self.client_name} [{status}] — expira {self.expires_at.strftime('%Y-%m-%d')}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired

    @property
    def days_remaining(self):
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
