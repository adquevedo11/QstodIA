#!/usr/bin/env bash
# ================================================================
#  QustodIA — Actualización PoC Heinsohn
#  Ejecutar desde máquina local CON VPN activa:
#    bash deploy-poc-update.sh
# ================================================================

set -euo pipefail

HEINSOHN_HOST="150.238.99.178"
SSH_KEY="${HOME}/.ssh/devops.pem"
SSH_USER="azureuser"
APP_DIR="/opt/qustodia/app"
PROJECT_NAME="qustodia"

R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' C='\033[0;36m' B='\033[1m' N='\033[0m'
step() { echo -e "\n${Y}[$(date +%H:%M:%S)]${N} ${B}$*${N}"; }
ok()   { echo -e "  ${G}✓${N} $*"; }
info() { echo -e "  ${C}ℹ${N} $*"; }
die()  { echo -e "\n${R}ERROR: $*${N}\n" >&2; exit 1; }

SSH="ssh -i ${SSH_KEY} -o ConnectTimeout=10 -o StrictHostKeyChecking=no ${SSH_USER}@${HEINSOHN_HOST}"
SCP="scp -i ${SSH_KEY} -o StrictHostKeyChecking=no"

# ── 1. Verificar conectividad ──────────────────────────────────
step "Verificando conexión a Heinsohn (${HEINSOHN_HOST})"
if ! ${SSH} "echo ok" >/dev/null 2>&1; then
  die "No se puede conectar a ${HEINSOHN_HOST}. ¿Está la VPN activa?"
fi
ok "Conexión SSH establecida"

# ── 2. Detectar directorio de instalación ─────────────────────
step "Detectando directorio de instalación"
REMOTE_APP_DIR=$(${SSH} "
  for d in /opt/qustodia/app /home/azureuser/defectdojo-sqa /home/azureuser/app; do
    if [ -f \"\$d/manage.py\" ]; then echo \"\$d\"; break; fi
  done
")
if [ -z "${REMOTE_APP_DIR}" ]; then
  die "No se encontró manage.py en ningún directorio conocido"
fi
ok "Directorio: ${REMOTE_APP_DIR}"
APP_DIR="${REMOTE_APP_DIR}"

# ── 3. Transferir archivos actualizados ───────────────────────
step "Transfiriendo archivos actualizados"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Crear directorios remotos necesarios
${SSH} "mkdir -p ${APP_DIR}/dojo/license_manager/migrations ${APP_DIR}/docker/extra_settings"

# Archivos individuales
files_to_copy=(
  "dojo/settings/settings.py"
  "dojo/apps.py"
  "docker/extra_settings/50_qustodia.py"
  "docker-compose.override.sqa.yml"
  "dojo/license_manager/__init__.py"
  "dojo/license_manager/apps.py"
  "dojo/license_manager/models.py"
  "dojo/license_manager/admin.py"
  "dojo/license_manager/middleware.py"
  "dojo/license_manager/migrations/__init__.py"
  "dojo/license_manager/migrations/0001_initial.py"
)

for f in "${files_to_copy[@]}"; do
  src="${SCRIPT_DIR}/${f}"
  if [ -f "${src}" ]; then
    ${SCP} "${src}" "${SSH_USER}@${HEINSOHN_HOST}:${APP_DIR}/${f}"
    ok "${f}"
  else
    echo -e "  ${Y}⚠${N} No encontrado localmente: ${f}"
  fi
done

# ── 4. Reiniciar uwsgi para aplicar nuevos bind mounts ────────
step "Recreando contenedor uwsgi (aplica nuevos bind mounts)"
${SSH} "cd ${APP_DIR} && docker compose --project-name ${PROJECT_NAME} up -d --force-recreate --no-deps uwsgi"
ok "uwsgi recreado"

# Esperar a que uwsgi responda
info "Esperando que Django arranque..."
for i in $(seq 1 24); do
  if ${SSH} "docker exec ${PROJECT_NAME}-uwsgi-1 python manage.py check --deploy --verbosity=0 >/dev/null 2>&1"; then
    break
  fi
  printf "."
  sleep 5
done
echo ""
ok "Django listo"

# ── 5. Aplicar migraciones ─────────────────────────────────────
step "Aplicando migraciones"

# license_manager.0001_initial (SeparateDatabaseAndState — no toca la BD)
${SSH} "docker exec -u root ${PROJECT_NAME}-uwsgi-1 python manage.py migrate license_manager --verbosity=1 2>&1"
ok "license_manager migrada"

# Verificar si hay migraciones dojo pendientes (pentest, bolsa de horas, etc.)
PENDING=$(${SSH} "docker exec -u root ${PROJECT_NAME}-uwsgi-1 python manage.py showmigrations dojo --plan 2>/dev/null | grep '^\[ \]' | wc -l" || echo "0")
if [ "${PENDING}" -gt 0 ]; then
  info "${PENDING} migraciones dojo pendientes — generando y aplicando"
  ${SSH} "docker exec -u root ${PROJECT_NAME}-uwsgi-1 python manage.py makemigrations --name qustodia_v2 2>&1 || true"
  ${SSH} "docker exec -u root ${PROJECT_NAME}-uwsgi-1 python manage.py migrate 2>&1"
  ok "Todas las migraciones aplicadas"
else
  ok "No hay migraciones dojo pendientes"
fi

# ── 6. Verificar que el admin carga ────────────────────────────
step "Verificando admin de licencias"
ADMIN_STATUS=$(${SSH} "curl -sf -o /dev/null -w '%{http_code}' http://localhost:8080/admin/license_manager/clientlicense/ 2>/dev/null || echo '000'")
if [[ "${ADMIN_STATUS}" == "302" || "${ADMIN_STATUS}" == "200" ]]; then
  ok "Admin responde (HTTP ${ADMIN_STATUS}) → /admin/license_manager/clientlicense/"
else
  echo -e "  ${Y}⚠${N} Admin responde HTTP ${ADMIN_STATUS} — verificar manualmente"
fi

# ── 7. Resumen ────────────────────────────────────────────────
echo ""
echo -e "${Y}${B}════════════════════════════════════════════════════════${N}"
echo -e "${G}${B}  ✓  HEINSOHN ACTUALIZADO${N}"
echo -e "${Y}${B}════════════════════════════════════════════════════════${N}"
echo ""
echo -e "  ${B}Próximos pasos en la sesión con Heinsohn:${N}"
echo -e "  1. Abrir: ${Y}http://${HEINSOHN_HOST}/admin/license_manager/clientlicense/${N}"
echo -e "  2. Login como admin → Añadir licencia de cliente"
echo -e "  3. Cliente: Heinsohn · Fecha: [fecha fin del PoC]"
echo -e "  4. Verificar que el middleware bloquea usuarios sin licencia activa"
echo ""
echo -e "  ${B}Comandos útiles en el servidor:${N}"
echo -e "  • Logs uwsgi: ${C}docker logs ${PROJECT_NAME}-uwsgi-1 --tail=30${N}"
echo -e "  • Shell Django: ${C}docker exec -it ${PROJECT_NAME}-uwsgi-1 python manage.py shell${N}"
echo ""
