#!/usr/bin/env bash
# deploy-poc.sh — Despliegue QustodIA en servidor cliente (HTTP, sin VPN)
# Uso: sudo bash deploy-poc.sh [IP_PUBLICA_CLIENTE]
# Ejemplo: sudo bash deploy-poc.sh 150.238.99.178
set -euo pipefail

APP=/opt/qustodia/app
IP_EXTRA="${1:-}"          # IP pública adicional para CSRF (opcional)
SERVER_IP=$(hostname -I | awk '{print $1}')

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [1/9] Permisos y directorio de trabajo..."
chown -R "$(logname 2>/dev/null || echo "$SUDO_USER")" "$APP" 2>/dev/null || true
cd "$APP"

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [2/9] Actualizando código..."
git pull origin qustodia/core-vnext

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [3/9] Activando overlay QustodIA SQA SA..."
cp docker-compose.override.sqa.yml docker-compose.override.yml

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [4/9] Configurando settings locales (HTTP, CSRF)..."
mkdir -p docker/extra_settings

# Construir lista de orígenes CSRF
CSRF_ORIGINS="\"http://${SERVER_IP}:8080\", \"http://${SERVER_IP}\""
if [ -n "$IP_EXTRA" ]; then
  CSRF_ORIGINS="${CSRF_ORIGINS}, \"http://${IP_EXTRA}:8080\", \"http://${IP_EXTRA}\""
fi

cat > docker/extra_settings/local_settings.py << EOF
# Configuración local QustodIA PoC (HTTP sin HTTPS)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = [${CSRF_ORIGINS}]
EOF
echo "   local_settings.py generado para IP: ${SERVER_IP} ${IP_EXTRA}"

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [5/9] Verificando red Docker..."
docker network create qustodia-net 2>/dev/null || echo "   Red qustodia-net ya existe"

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [6/9] Levantando contenedores con diseño SQA SA..."
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d
echo "   Esperando que uwsgi esté listo (90 seg)..."
sleep 90

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [7/9] Aplicando migraciones de módulos QustodIA..."
# makemigrations como root porque el directorio de migraciones puede ser de root
docker compose exec -T -u root uwsgi python manage.py makemigrations --name qustodia_models 2>/dev/null || true
docker compose exec -T uwsgi python manage.py migrate

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [8/9] Creando usuario qustodia (si no existe)..."
docker compose exec -T uwsgi python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='qustodia').exists():
    u = User.objects.create_superuser('qustodia', 'qustodia@sqasa.co', 'Qustodia2024x')
    print('Usuario qustodia creado')
else:
    print('Usuario qustodia ya existe')
" 2>/dev/null | tail -1

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [9/9] Iniciando Go-Live Agent (Release Manager)..."
cd "$APP/go-live-agent"
TOKEN=$(docker compose -f ../docker-compose.yml exec -T uwsgi python manage.py shell -c \
  "from rest_framework.authtoken.models import Token; from django.contrib.auth import get_user_model; u=get_user_model().objects.get(username='admin'); t,_=Token.objects.get_or_create(user=u); print(t.key)" \
  2>/dev/null | tail -1)
if [ -n "$TOKEN" ]; then
  printf "DEFECTDOJO_BASE_URL=http://nginx:8080\nDEFECTDOJO_API_TOKEN=%s\nLLM_ENABLED=false\nLLM_PROVIDER=groq\n" "$TOKEN" > .env
  echo "   Token obtenido correctamente"
else
  echo "   AVISO: no se pudo obtener el token — el agente inicia sin conexión a DefectDojo"
  printf "DEFECTDOJO_BASE_URL=http://nginx:8080\nDEFECTDOJO_API_TOKEN=change-me\nLLM_ENABLED=false\nLLM_PROVIDER=groq\n" > .env
fi
docker compose up -d --build

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✓  QustodIA desplegado correctamente                       ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  URL:       http://${SERVER_IP}:8080"
echo "║  Usuario:   qustodia"
echo "║  Contraseña: Qustodia2024x"
echo "║"
echo "║  Módulos: Pentest · Bolsa de Horas · Concepto de Seguridad  ║"
echo "║           Informe Ejecutivo · Métricas SQA · Release Manager ║"
echo "╚══════════════════════════════════════════════════════════════╝"
