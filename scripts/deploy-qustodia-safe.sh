#!/usr/bin/env bash
# deploy-qustodia-safe.sh — Deploy QustodIA con backup, dry-run y health check
#
# Uso:
#   PROD_HOST=prod.sqasa.co PROD_USER=deploy ./scripts/deploy-qustodia-safe.sh
#
# Variables de entorno:
#   PROD_HOST   — hostname o IP del servidor  (requerida)
#   PROD_USER   — usuario SSH                 (default: deploy)
#   REMOTE_DIR  — directorio en el servidor   (default: /opt/qustodia)
#   BRANCH      — rama a desplegar            (default: qustodia/core-vnext)
#   HEALTH_URL  — URL de health check local   (default: http://localhost:8080/api/v2/)
#   SKIP_BACKUP — "true" para saltar backup   (no recomendado)
#   DRY_RUN     — "true" para solo planificar sin cambiar nada

set -euo pipefail

# ── Parámetros ────────────────────────────────────────────────────────────────
PROD_HOST="${PROD_HOST:?Falta PROD_HOST. Ejemplo: PROD_HOST=prod.sqasa.co ./scripts/deploy-qustodia-safe.sh}"
PROD_USER="${PROD_USER:-deploy}"
REMOTE_DIR="${REMOTE_DIR:-/opt/qustodia}"
BRANCH="${BRANCH:-qustodia/core-vnext}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8080/api/v2/}"
SKIP_BACKUP="${SKIP_BACKUP:-false}"
DRY_RUN="${DRY_RUN:-false}"

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.override.sqa.yml"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_qustodia_${TIMESTAMP}.sql.gz"

# ── Colores ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()   { error "$*"; exit 1; }

# ── Función rollback (se imprime al inicio, siempre disponible) ───────────────
print_rollback_instructions() {
  echo ""
  echo -e "${YELLOW}══════════════════════════════════════════════════════${NC}"
  echo -e "${YELLOW}  ROLLBACK MANUAL (si algo falla):${NC}"
  echo -e "${YELLOW}══════════════════════════════════════════════════════${NC}"
  echo "  1. Restaurar código anterior:"
  echo "     ssh ${PROD_USER}@${PROD_HOST} 'cd ${REMOTE_DIR} && git reset --hard HEAD@{1}'"
  echo ""
  echo "  2. Restaurar base de datos (si se creó backup):"
  echo "     ssh ${PROD_USER}@${PROD_HOST} 'cd ${REMOTE_DIR} && \\"
  echo "       gunzip -c backups/${BACKUP_FILE} | \\"
  echo "       docker compose ${COMPOSE_FILES} exec -T postgres \\"
  echo "         psql -U defectdojo defectdojo'"
  echo ""
  echo "  3. Reiniciar con imagen anterior:"
  echo "     ssh ${PROD_USER}@${PROD_HOST} 'cd ${REMOTE_DIR} && \\"
  echo "       docker compose ${COMPOSE_FILES} up -d --no-deps uwsgi celerybeat celeryworker nginx'"
  echo -e "${YELLOW}══════════════════════════════════════════════════════${NC}"
  echo ""
}

# ── Encabezado ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       QustodIA — Deploy Seguro               ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo "  Host    : ${PROD_USER}@${PROD_HOST}"
echo "  Dir     : ${REMOTE_DIR}"
echo "  Rama    : ${BRANCH}"
echo "  Backup  : ${SKIP_BACKUP}"
echo "  Dry-run : ${DRY_RUN}"
echo "  TS      : ${TIMESTAMP}"
echo ""

print_rollback_instructions

if [[ "${DRY_RUN}" == "true" ]]; then
  warn "DRY_RUN=true — se mostrará el plan pero NO se realizarán cambios."
  echo ""
fi

# ── Step 0: Verificar conectividad SSH ───────────────────────────────────────
info "0/7  Verificando conectividad SSH a ${PROD_HOST}..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" "echo connected" > /dev/null \
  || die "No se puede conectar a ${PROD_USER}@${PROD_HOST}. Revisa SSH y credenciales."
ok "Conexión SSH OK"

# ── Step 1: Verificar estado del servidor remoto ─────────────────────────────
info "1/7  Verificando estado del servidor remoto..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << 'REMOTE_CHECK'
set -euo pipefail

# Disco disponible (mínimo 2 GB)
AVAIL_KB=$(df /opt --output=avail | tail -1)
AVAIL_GB=$(( AVAIL_KB / 1024 / 1024 ))
if (( AVAIL_GB < 2 )); then
  echo "ERROR: Disco insuficiente (${AVAIL_GB} GB disponibles, mínimo 2 GB)" >&2
  exit 1
fi
echo "  Disco disponible : ${AVAIL_GB} GB"

# Docker corriendo
docker info > /dev/null 2>&1 || { echo "ERROR: Docker no está corriendo" >&2; exit 1; }
echo "  Docker           : OK"

# Stack levantado
cd /opt/qustodia
RUNNING=$(docker compose -f docker-compose.yml -f docker-compose.override.sqa.yml ps --status running --format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo 0)
echo "  Contenedores activos : ${RUNNING}"
REMOTE_CHECK
ok "Servidor remoto OK"

# ── Step 2: Backup de la base de datos ───────────────────────────────────────
if [[ "${SKIP_BACKUP}" == "true" ]]; then
  warn "2/7  Backup OMITIDO (SKIP_BACKUP=true) — riesgo alto si las migraciones fallan."
elif [[ "${DRY_RUN}" == "true" ]]; then
  info "2/7  [DRY-RUN] Se crearía backup: backups/${BACKUP_FILE}"
else
  info "2/7  Creando backup de la base de datos en el servidor..."
  ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_BACKUP
set -euo pipefail
cd "${REMOTE_DIR}"
mkdir -p backups

echo "  Volcando base de datos..."
docker compose ${COMPOSE_FILES} exec -T postgres \
  pg_dump -U defectdojo defectdojo \
  | gzip > "backups/${BACKUP_FILE}"

SIZE=\$(du -sh "backups/${BACKUP_FILE}" | cut -f1)
echo "  Backup creado: backups/${BACKUP_FILE} (\${SIZE})"

# Mantener solo los últimos 5 backups
ls -t backups/backup_qustodia_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r rm --
REMOTE_BACKUP
  ok "Backup creado: backups/${BACKUP_FILE}"
fi

# ── Step 3: Actualizar código ─────────────────────────────────────────────────
if [[ "${DRY_RUN}" == "true" ]]; then
  info "3/7  [DRY-RUN] Se ejecutaría: git fetch + git reset --hard origin/${BRANCH}"
else
  info "3/7  Actualizando código en el servidor (rama: ${BRANCH})..."
  ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_CODE
set -euo pipefail
cd "${REMOTE_DIR}"
git fetch --all --quiet
git checkout "${BRANCH}" --quiet
git reset --hard "origin/${BRANCH}"
echo "  HEAD: \$(git log --oneline -1)"
REMOTE_CODE
  ok "Código actualizado"
fi

# ── Step 4: Plan de migraciones (siempre, incluso en dry-run) ─────────────────
info "4/7  Verificando plan de migraciones..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_MIGRATE_PLAN
set -euo pipefail
cd "${REMOTE_DIR}"
echo "  Migraciones pendientes:"
docker compose ${COMPOSE_FILES} run --rm --no-deps uwsgi \
  python manage.py migrate --plan --no-input 2>&1 \
  | grep -E "^  (Run|Unapply|No migrations)" || echo "  (ninguna pendiente)"
REMOTE_MIGRATE_PLAN

if [[ "${DRY_RUN}" == "true" ]]; then
  warn "DRY_RUN=true — deteniendo aquí. No se construyó imagen ni se aplicaron cambios."
  exit 0
fi

# ── Step 5: Construir imagen ──────────────────────────────────────────────────
info "5/7  Construyendo imagen Docker (puede tardar varios minutos)..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_BUILD
set -euo pipefail
cd "${REMOTE_DIR}"
docker compose ${COMPOSE_FILES} build uwsgi 2>&1 | tail -5
echo "  Build OK"
REMOTE_BUILD
ok "Imagen construida"

# ── Step 6: Aplicar migraciones y reiniciar ───────────────────────────────────
info "6/7  Aplicando migraciones y reiniciando servicios..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_DEPLOY
set -euo pipefail
cd "${REMOTE_DIR}"

echo "  Aplicando migraciones..."
docker compose ${COMPOSE_FILES} run --rm --no-deps uwsgi \
  python manage.py migrate --noinput

echo "  Colectando archivos estáticos..."
docker compose ${COMPOSE_FILES} run --rm --no-deps uwsgi \
  python manage.py collectstatic --noinput --clear 2>&1 | tail -3

echo "  Deteniendo workers Celery para reinicio limpio..."
docker compose ${COMPOSE_FILES} stop celerybeat celeryworker

echo "  Reiniciando uwsgi..."
docker compose ${COMPOSE_FILES} up -d --no-deps uwsgi

echo "  Esperando 10s para que uwsgi arranque..."
sleep 10

echo "  Reiniciando Celery..."
docker compose ${COMPOSE_FILES} up -d --no-deps celerybeat celeryworker

echo "  Reiniciando nginx..."
docker compose ${COMPOSE_FILES} up -d --no-deps nginx
REMOTE_DEPLOY
ok "Servicios reiniciados"

# ── Step 7: Health check ──────────────────────────────────────────────────────
info "7/7  Verificando que la aplicación responde (health check)..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_HEALTH
set -euo pipefail
cd "${REMOTE_DIR}"

MAX_RETRIES=12  # 60 segundos en total
RETRY_WAIT=5
HTTP_CODE=""

for i in \$(seq 1 \${MAX_RETRIES}); do
  HTTP_CODE=\$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${HEALTH_URL}" 2>/dev/null || echo "000")
  if [[ "\${HTTP_CODE}" == "200" ]] || [[ "\${HTTP_CODE}" == "401" ]]; then
    echo "  Health check OK (HTTP \${HTTP_CODE}) tras \${i} intento(s)"
    break
  fi
  echo "  Intento \${i}/\${MAX_RETRIES}: HTTP \${HTTP_CODE} — esperando \${RETRY_WAIT}s..."
  sleep \${RETRY_WAIT}
done

if [[ "\${HTTP_CODE}" != "200" ]] && [[ "\${HTTP_CODE}" != "401" ]]; then
  echo "ERROR: La aplicación no responde tras \$(( MAX_RETRIES * RETRY_WAIT ))s (último HTTP: \${HTTP_CODE})" >&2
  echo "Estado de contenedores:" >&2
  docker compose ${COMPOSE_FILES} ps >&2
  echo "Últimas líneas de log uwsgi:" >&2
  docker compose ${COMPOSE_FILES} logs --tail=30 uwsgi >&2
  exit 1
fi

echo ""
echo "  Estado de contenedores:"
docker compose ${COMPOSE_FILES} ps
REMOTE_HEALTH

# ── Resumen final ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Deploy completado con éxito ✓          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo "  Rama    : ${BRANCH}"
echo "  Backup  : backups/${BACKUP_FILE}"
echo "  URL     : ${HEALTH_URL}"
echo ""
echo "  Conserva el nombre del backup por si necesitas rollback:"
echo -e "  ${YELLOW}${BACKUP_FILE}${NC}"
echo ""
