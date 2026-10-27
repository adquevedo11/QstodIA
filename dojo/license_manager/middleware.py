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

            # Productos a los que el usuario tiene acceso
            product_ids = set(user.authorized_products.values_list('id', flat=True))
            if not product_ids:
                return False  # sin productos → acceso libre

            licenses = ClientLicense.objects.filter(product_id__in=product_ids)
            if not licenses.exists():
                return False  # ningún producto tiene licencia → acceso libre

            now = timezone.now()
            valid = licenses.filter(is_active=True, expires_at__gt=now)
            return not valid.exists()

        except Exception:
            return False  # ante cualquier error, no bloquear
