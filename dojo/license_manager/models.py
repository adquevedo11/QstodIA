from django.db import models
from django.utils import timezone


class ClientLicense(models.Model):
    """
    Controla el acceso de un cliente al sistema QustodIA.
    Gestionado desde /admin/ por el superadmin de SQA SA.
    """
    client_name = models.CharField(max_length=200, verbose_name="Nombre del cliente")
    product     = models.OneToOneField(
        'dojo.Product',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='license',
        verbose_name="Producto (activo) asociado",
        help_text="Producto/activo del cliente. Solo los usuarios con acceso a este producto son afectados.",
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
        expiry = self.expires_at.strftime('%Y-%m-%d') if self.expires_at else "sin fecha"
        return f"{self.client_name} [{status}] — expira {expiry}"

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired

    @property
    def days_remaining(self):
        if not self.expires_at:
            return 0
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
