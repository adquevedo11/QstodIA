#!/usr/bin/env bash
# deploy-qustodia.sh — Despliega QustodIA en el servidor de producción
#
# Uso:
#   PROD_HOST=prod.sqasa.co PROD_USER=deploy ./scripts/deploy-qustodia.sh
#
# Variables de entorno requeridas:
#   PROD_HOST   — hostname o IP del servidor de producción
#   PROD_USER   — usuario SSH (default: deploy)
#   REMOTE_DIR  — directorio en el servidor (default: /opt/qustodia)
#   BRANCH      — rama a desplegar (default: qustodia/core-vnext)

set -euo pipefail

PROD_HOST="${PROD_HOST:?Falta PROD_HOST. Ejemplo: PROD_HOST=prod.sqasa.co ./scripts/deploy-qustodia.sh}"
PROD_USER="${PROD_USER:-deploy}"
REMOTE_DIR="${REMOTE_DIR:-/opt/qustodia}"
BRANCH="${BRANCH:-qustodia/core-vnext}"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.override.sqa.yml"

echo "=== QustodIA Deploy ==="
echo "  Host  : ${PROD_USER}@${PROD_HOST}"
echo "  Dir   : ${REMOTE_DIR}"
echo "  Rama  : ${BRANCH}"
echo ""

ssh -o StrictHostKeyChecking=no "${PROD_USER}@${PROD_HOST}" bash << REMOTE
set -euo pipefail
cd "${REMOTE_DIR}"

echo "--- 1/5 Actualizando código ---"
git fetch --all
git checkout "${BRANCH}"
git reset --hard "origin/${BRANCH}"

echo "--- 2/5 Construyendo imagen ---"
docker compose ${COMPOSE_FILES} build uwsgi

echo "--- 3/5 Migraciones ---"
docker compose ${COMPOSE_FILES} run --rm uwsgi python manage.py migrate --noinput

echo "--- 4/5 Static files ---"
docker compose ${COMPOSE_FILES} run --rm uwsgi python manage.py collectstatic --noinput

echo "--- 5/5 Reiniciando servicios ---"
docker compose ${COMPOSE_FILES} up -d --no-deps uwsgi celerybeat celeryworker nginx

echo ""
echo "=== Deploy completado ==="
docker compose ${COMPOSE_FILES} ps
REMOTE
