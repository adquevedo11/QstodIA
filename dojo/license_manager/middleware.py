"""
Middleware que bloquea el acceso a clientes con licencia expirada o desactivada.

Flujo:
  1. Superuser (SQA SA) → siempre pasa.
  2. Usuario con Product que tiene ClientLicense inválida → redirige a /license-expired/.
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
            from dojo.models import Product  # noqa: PLC0415
            from django.db.models import Q  # noqa: PLC0415

            # user.pk fuerza la evaluación del SimpleLazyObject de Django
            user_pk = user.pk
            if not user_pk:
                return False

            # Productos a los que el usuario tiene acceso (mismo criterio que get_authorized_products)
            product_ids = set(
                Product.objects.filter(
                    Q(authorized_users__id=user_pk) | Q(prod_type__authorized_users__id=user_pk)
                ).values_list('id', flat=True)
            )
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
