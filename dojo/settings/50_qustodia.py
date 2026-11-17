# QustodIA — overrides aplicados sobre settings.dist.py
# Este archivo se carga después de settings.dist.py (split_settings optional).

# Sesión expira a las 8 horas de inactividad y al cerrar el navegador.
# El default de DefectDojo es 14 días sin caducidad, lo cual es inapropiado
# para una herramienta de gestión de vulnerabilidades en cliente.
SESSION_COOKIE_AGE = 28800          # 8 horas en segundos
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
