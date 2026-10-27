"""
Middleware que bloquea el acceso a clientes con licencia expirada o desactivada.

Flujo:
  1. Superuser (SQA SA) → siempre pasa.
  2. Usuario con Product_Type que tiene ClientLicense inválida → redirige a /license-expired/.
  3. Sin licencia configurada → pasa (sin restricción).

Rutas excluidas: login, logout, admin, static, media y la propia página de expiración.
"""
from django.utils import timezone


EXEMPT_PREFIXES = ('/login', '/logout', '/license-expired', '/admin', '/static', '/media', '/favicon')


def _is_exempt(path):
    return any(path.startswith(p) for p in EXEMPT_PREFIXES)


class LicenseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _is_exempt(request.path) and request.user.is_authenticated:
            if not request.user.is_superuser and self._license_blocked(request.user):
                from django.shortcuts import redirect  # noqa: PLC0415
                return redirect('/license-expired/')
        return self.get_response(request)

    @staticmethod
    def _license_blocked(user):
        try:
            from dojo.license_manager.models import ClientLicense  # noqa: PLC0415 -- lazy import

            # Autorizaciones a nivel Product → obtener el Product Type del producto
            pt_ids = set(
                user.authorization_set
                    .filter(product__isnull=False)
                    .values_list('product__product_type_id', flat=True)
            )
            # Autorizaciones a nivel Product Type directo
            pt_ids |= set(
                user.authorization_set
                    .filter(product_type__isnull=False, product__isnull=True)
                    .values_list('product_type_id', flat=True)
            )
            if not pt_ids:
                return False

            licenses = ClientLicense.objects.filter(product_type_id__in=pt_ids)
            if not licenses.exists():
                return False  # sin licencia configurada → acceso libre

            now = timezone.now()
            # Bloqueado si ninguna licencia activa+vigente cubre sus Product Types
            valid = licenses.filter(is_active=True, expires_at__gt=now)
            return not valid.exists()

        except Exception:
            return False  # ante cualquier error, no bloquear
