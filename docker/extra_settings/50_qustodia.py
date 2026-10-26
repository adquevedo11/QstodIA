# QustodIA — configuración adicional inyectada vía extra_settings
# Este archivo se ejecuta en el contexto de settings.dist.py, por lo que
# MIDDLEWARE ya está definido y puede modificarse directamente.

MIDDLEWARE = list(MIDDLEWARE) + ["dojo.license_manager.middleware.LicenseMiddleware"]  # noqa: F821
