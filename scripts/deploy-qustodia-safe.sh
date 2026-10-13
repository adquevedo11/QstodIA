#!/usr/bin/env bash
# deploy-qustodia-safe.sh — Deploy QustodIA con backup, dry-run y health check
#
# Uso:
#   PROD_HOST=172.208.11.6 bash scripts/deploy-qustodia-safe.sh
#
# Variables de entorno:
#   PROD_HOST   — hostname o IP del servidor  (requerida)
#   PROD_USER   — usuario SSH                 (default: azureuser)
#   REMOTE_DIR  — directorio en el servidor   (default: /home/azureuser/defectdojo-sqa)
#   BRANCH      — rama local a desplegar      (default: qustodia/core-vnext)
#   HEALTH_URL  — URL de health check         (default: http://localhost:8080/api/v2/)
#   SKIP_BACKUP — "true" para saltar backup   (no recomendado)
#   DRY_RUN     — "true" para solo planificar sin cambiar nada
#   SSH_KEY     — ruta a la llave privada SSH  (default: ~/.ssh/devops.pem)

set -euo pipefail

# ── Parámetros ────────────────────────────────────────────────────────────────
PROD_HOST="${PROD_HOST:?Falta PROD_HOST. Ejemplo: PROD_HOST=172.208.11.6 bash scripts/deploy-qustodia-safe.sh}"
PROD_USER="${PROD_USER:-azureuser}"
REMOTE_DIR="${REMOTE_DIR:-/home/azureuser/defectdojo-sqa}"
BRANCH="${BRANCH:-qustodia/core-vnext}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8080/api/v2/}"
SKIP_BACKUP="${SKIP_BACKUP:-false}"
DRY_RUN="${DRY_RUN:-false}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/devops.pem}"

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.override.sqa.yml"
SSH_OPTS="-i ${SSH_KEY} -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_qustodia_${TIMESTAMP}.sql.gz"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Colores ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()   { error "$*"; exit 1; }

# ── Rollback ─────────────────────────────────────────────────────────────────
print_rollback_instructions() {
  echo ""
  echo -e "${YELLOW}══════════════════════════════════════════════════════${NC}"
  echo -e "${YELLOW}  ROLLBACK MANUAL (si algo falla):${NC}"
  echo -e "${YELLOW}══════════════════════════════════════════════════════${NC}"
  echo "  1. Restaurar código — volver a correr el script con la rama anterior"
  echo ""
  echo "  2. Restaurar base de datos:"
  echo "     ssh -i ${SSH_KEY} ${PROD_USER}@${PROD_HOST} 'cd ${REMOTE_DIR} && \\"
  echo "       gunzip -c backups/${BACKUP_FILE} | \\"
  echo "       docker compose ${COMPOSE_FILES} exec -T postgres \\"
  echo "         psql -U defectdojo defectdojo'"
  echo ""
  echo "  3. Reiniciar servicios:"
  echo "     ssh -i ${SSH_KEY} ${PROD_USER}@${PROD_HOST} 'cd ${REMOTE_DIR} && \\"
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

# ── Step 0: Verificar SSH ─────────────────────────────────────────────────────
info "0/8  Verificando conectividad SSH a ${PROD_HOST}..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" "echo connected" > /dev/null \
  || die "No se puede conectar a ${PROD_USER}@${PROD_HOST}."
ok "Conexión SSH OK"

# ── Step 1: Verificar servidor ────────────────────────────────────────────────
info "1/8  Verificando estado del servidor remoto..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_CHECK
set -euo pipefail
AVAIL_KB=\$(df "${REMOTE_DIR}" --output=avail 2>/dev/null | tail -1 || df / --output=avail | tail -1)
AVAIL_GB=\$(( AVAIL_KB / 1024 / 1024 ))
if (( AVAIL_GB < 2 )); then
  echo "ERROR: Disco insuficiente (\${AVAIL_GB} GB)" >&2; exit 1
fi
echo "  Disco disponible : \${AVAIL_GB} GB"
docker info > /dev/null 2>&1 || { echo "ERROR: Docker no está corriendo" >&2; exit 1; }
echo "  Docker           : OK"
cd "${REMOTE_DIR}"
RUNNING=\$(docker compose ${COMPOSE_FILES} ps --status running --format json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo 0)
echo "  Contenedores activos : \${RUNNING}"
REMOTE_CHECK
ok "Servidor remoto OK"

# ── Step 2: Backup ───────────────────────────────────────────────────────────
if [[ "${SKIP_BACKUP}" == "true" ]]; then
  warn "2/8  Backup OMITIDO (SKIP_BACKUP=true)"
elif [[ "${DRY_RUN}" == "true" ]]; then
  info "2/8  [DRY-RUN] Se crearía backup: backups/${BACKUP_FILE}"
else
  info "2/8  Creando backup de la base de datos..."
  ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_BACKUP
set -euo pipefail
cd "${REMOTE_DIR}"
mkdir -p backups
echo "  Volcando base de datos..."
docker compose ${COMPOSE_FILES} exec -T postgres \
  pg_dump -U defectdojo defectdojo | gzip > "backups/${BACKUP_FILE}"
SIZE=\$(du -sh "backups/${BACKUP_FILE}" | cut -f1)
echo "  Backup creado: backups/${BACKUP_FILE} (\${SIZE})"
ls -t backups/backup_qustodia_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r rm --
REMOTE_BACKUP
  ok "Backup creado: backups/${BACKUP_FILE}"
fi

# ── Step 3: Sincronizar código (rsync local → servidor) ───────────────────────
if [[ "${DRY_RUN}" == "true" ]]; then
  info "3/8  [DRY-RUN] Se ejecutaría: rsync ${LOCAL_DIR}/ → ${REMOTE_DIR}/"
else
  info "3/8  Sincronizando código al servidor (tar + scp) — rama: ${BRANCH}..."
  CURRENT_SHA=$(git -C "${LOCAL_DIR}" rev-parse --short "${BRANCH}" 2>/dev/null || echo "unknown")
  TARBALL="/tmp/qustodia-deploy-${CURRENT_SHA}.tar.gz"
  # Crear tarball del ref especificado (no HEAD) para garantizar que se deploy la rama correcta
  git -C "${LOCAL_DIR}" archive --format=tar.gz "${BRANCH}" -o "${TARBALL}"
  # Copiar al servidor y extraer
  scp ${SSH_OPTS} "${TARBALL}" "${PROD_USER}@${PROD_HOST}:/tmp/"
  ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_EXTRACT
set -euo pipefail
cd "${REMOTE_DIR}"
tar -xzf "/tmp/qustodia-deploy-${CURRENT_SHA}.tar.gz" --overwrite
rm -f "/tmp/qustodia-deploy-${CURRENT_SHA}.tar.gz"
# Limpiar bytecode cacheado para forzar recompilación con el nuevo código
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "${CURRENT_SHA}" > .deployed_sha
echo "  Extraído OK — SHA: ${CURRENT_SHA}"
REMOTE_EXTRACT
  rm -f "${TARBALL}"
  ok "Código sincronizado — HEAD: ${CURRENT_SHA}"
fi

# ── Step 4: Plan de migraciones (desde imagen existente) ─────────────────────
info "4/8  Verificando plan de migraciones..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_MIGRATE_PLAN
set -euo pipefail
cd "${REMOTE_DIR}"
echo "  Migraciones pendientes:"
docker compose ${COMPOSE_FILES} run --rm --no-deps --entrypoint "" uwsgi \
  python manage.py migrate --plan --no-input 2>&1 \
  | grep -E "^  (Run|Unapply|No migrations)" || echo "  (ninguna pendiente)"
REMOTE_MIGRATE_PLAN

if [[ "${DRY_RUN}" == "true" ]]; then
  warn "DRY_RUN=true — deteniendo aquí. No se aplicaron cambios."
  exit 0
fi

# ── Step 5: Build imágenes (uwsgi + nginx) ───────────────────────────────────
# nginx build corre collectstatic y Tailwind CSS — DEBE reconstruirse con el nuevo código
info "5/8  Construyendo imágenes Docker (uwsgi + nginx) con el nuevo código..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_BUILD
set -euo pipefail
cd "${REMOTE_DIR}"
echo "  Construyendo uwsgi (--no-cache para garantizar código actualizado)..."
docker compose ${COMPOSE_FILES} build --no-cache uwsgi 2>&1 | tail -5
echo "  Construyendo nginx (incluye collectstatic + Tailwind CSS)..."
docker compose ${COMPOSE_FILES} build nginx 2>&1 | tail -3
echo "  Build OK"
REMOTE_BUILD
ok "Imágenes construidas (uwsgi + nginx)"

# ── Step 5.5: manage.py check contra la imagen recién construida ──────────────
info "5.5/8  Ejecutando manage.py check con la nueva imagen..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_CHECK_DJANGO
set -euo pipefail
cd "${REMOTE_DIR}"
docker compose ${COMPOSE_FILES} run --rm --no-deps --entrypoint "" uwsgi \
  python manage.py check 2>&1 \
  || { echo "ERROR: manage.py check falló — revisar antes de continuar" >&2; exit 1; }
echo "  manage.py check OK"
REMOTE_CHECK_DJANGO
ok "Django check OK"

# ── Step 6: Migraciones + restart ────────────────────────────────────────────
info "6/8  Aplicando migraciones y reiniciando servicios..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_DEPLOY
set -euo pipefail
cd "${REMOTE_DIR}"
echo "  Aplicando migraciones..."
docker compose ${COMPOSE_FILES} run --rm --no-deps --entrypoint "" uwsgi \
  python manage.py migrate --noinput
echo "  Deteniendo workers Celery..."
docker compose ${COMPOSE_FILES} stop celerybeat celeryworker
echo "  Reiniciando uwsgi..."
docker compose ${COMPOSE_FILES} up -d --no-deps uwsgi
echo "  Esperando 10s..."
sleep 10
echo "  Reiniciando Celery y nginx..."
docker compose ${COMPOSE_FILES} up -d --no-deps celerybeat celeryworker nginx
REMOTE_DEPLOY
ok "Servicios reiniciados"

# ── Step 7: Health check ──────────────────────────────────────────────────────
info "7/8  Health check..."
ssh ${SSH_OPTS} "${PROD_USER}@${PROD_HOST}" bash << REMOTE_HEALTH
set -euo pipefail
cd "${REMOTE_DIR}"
MAX_RETRIES=12
RETRY_WAIT=5
HTTP_CODE=""
for i in \$(seq 1 \${MAX_RETRIES}); do
  HTTP_CODE=\$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${HEALTH_URL}" 2>/dev/null || echo "000")
  if [[ "\${HTTP_CODE}" == "200" ]] || [[ "\${HTTP_CODE}" == "401" ]] || [[ "\${HTTP_CODE}" == "403" ]]; then
    echo "  Health check OK (HTTP \${HTTP_CODE}) tras \${i} intento(s)"
    break
  fi
  echo "  Intento \${i}/\${MAX_RETRIES}: HTTP \${HTTP_CODE} — esperando \${RETRY_WAIT}s..."
  sleep \${RETRY_WAIT}
done
if [[ "\${HTTP_CODE}" != "200" ]] && [[ "\${HTTP_CODE}" != "401" ]] && [[ "\${HTTP_CODE}" != "403" ]]; then
  echo "ERROR: App no responde (HTTP: \${HTTP_CODE})" >&2
  docker compose ${COMPOSE_FILES} ps >&2
  docker compose ${COMPOSE_FILES} logs --tail=30 uwsgi >&2
  exit 1
fi
echo ""
echo "  Estado de contenedores:"
docker compose ${COMPOSE_FILES} ps
REMOTE_HEALTH

# ── Resumen ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Deploy completado con éxito ✓          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo "  Backup  : backups/${BACKUP_FILE}"
echo "  URL     : ${HEALTH_URL}"
echo -e "  ${YELLOW}Guarda el nombre del backup para rollback.${NC}"
echo ""
