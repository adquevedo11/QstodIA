#!/usr/bin/env bash
# ================================================================
#  QustodIA — Script de actualización (ejecutar EN el servidor)
#  Uso:
#    bash update-heinsohn.sh
# ================================================================

set -euo pipefail

REPO_URL="https://github.com/adquevedo11/QstodIA.git"
BRANCH="qustodia/core-vnext"

R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' C='\033[0;36m' B='\033[1m' N='\033[0m'
step() { echo -e "\n${Y}[$(date +%H:%M:%S)]${N} ${B}$*${N}"; }
ok()   { echo -e "  ${G}✓${N} $*"; }
info() { echo -e "  ${C}ℹ${N} $*"; }
die()  { echo -e "\n${R}ERROR: $*${N}\n" >&2; exit 1; }

# ── 1. Detectar directorio de instalación ─────────────────────
step "Detectando directorio de instalación"
APP_DIR=""
for d in /opt/qustodia/app /home/azureuser/defectdojo-sqa /home/azureuser/app; do
  if [ -f "$d/manage.py" ]; then APP_DIR="$d"; break; fi
done
[ -z "$APP_DIR" ] && die "No se encontró manage.py. Indique el directorio manualmente."
ok "Directorio: $APP_DIR"

# Detectar nombre del proyecto docker
PROJECT_NAME=$(docker compose --project-directory "$APP_DIR" ps --format json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['Project'])" 2>/dev/null \
  || basename "$APP_DIR")
ok "Proyecto Docker: $PROJECT_NAME"

UWSGI_CONTAINER="${PROJECT_NAME}-uwsgi-1"

# ── 2. Clonar/actualizar repo temporal ────────────────────────
step "Descargando últimos cambios desde GitHub"
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

git clone --depth=1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR/repo" 2>&1 | tail -3
ok "Rama $BRANCH clonada"

SRC="$TMP_DIR/repo"

# ── 3. Copiar archivos actualizados ───────────────────────────
step "Copiando archivos al directorio de instalación"

mkdir -p \
  "$APP_DIR/dojo/license_manager/migrations" \
  "$APP_DIR/dojo/templates/dojo"

files=(
  "dojo/license_manager/__init__.py"
  "dojo/license_manager/apps.py"
  "dojo/license_manager/models.py"
  "dojo/license_manager/admin.py"
  "dojo/license_manager/middleware.py"
  "dojo/license_manager/migrations/__init__.py"
  "dojo/license_manager/migrations/0001_initial.py"
  "dojo/license_manager/migrations/0002_product_fk.py"
  "dojo/templates/dojo/license_expired.html"
  "dojo/templates/dojo/pentest_list.html"
  "dojo/templates/dojo/view_eng.html"
  "dojo/settings/settings.py"
  "dojo/apps.py"
)

for f in "${files[@]}"; do
  if [ -f "$SRC/$f" ]; then
    cp "$SRC/$f" "$APP_DIR/$f"
    ok "$f"
  else
    echo -e "  ${Y}⚠${N} No existe en el repo: $f (se omite)"
  fi
done

# ── 4. Recrear uwsgi (limpia caché de templates en memoria) ───
step "Reiniciando uwsgi"
cd "$APP_DIR"
docker compose --project-name "$PROJECT_NAME" up -d --force-recreate --no-deps uwsgi
ok "uwsgi reiniciado"

info "Esperando que Django arranque..."
for i in $(seq 1 30); do
  if docker exec "$UWSGI_CONTAINER" python manage.py check --verbosity=0 >/dev/null 2>&1; then
    break
  fi
  printf "."
  sleep 5
done
echo ""
ok "Django listo"

# ── 5. Migraciones ────────────────────────────────────────────
step "Aplicando migraciones"
docker exec "$UWSGI_CONTAINER" python manage.py migrate license_manager --verbosity=1
ok "license_manager migrada"

PENDING=$(docker exec "$UWSGI_CONTAINER" python manage.py showmigrations dojo --plan 2>/dev/null \
  | grep -c '^\[ \]' || true)
if [ "${PENDING:-0}" -gt 0 ]; then
  info "$PENDING migraciones dojo pendientes — aplicando"
  docker exec "$UWSGI_CONTAINER" python manage.py migrate
  ok "Todas las migraciones aplicadas"
else
  ok "No hay migraciones pendientes"
fi

# ── 6. Verificar ──────────────────────────────────────────────
step "Verificando"
STATUS=$(curl -sf -o /dev/null -w '%{http_code}' http://localhost:8080/admin/ 2>/dev/null || echo "000")
if [[ "$STATUS" == "302" || "$STATUS" == "200" ]]; then
  ok "Aplicación responde (HTTP $STATUS)"
else
  echo -e "  ${Y}⚠${N} HTTP $STATUS — verificar manualmente en http://localhost:8080"
fi

# ── 7. Resumen ────────────────────────────────────────────────
echo ""
echo -e "${Y}${B}════════════════════════════════════════════════════════${N}"
echo -e "${G}${B}  ✓  ACTUALIZACIÓN COMPLETADA${N}"
echo -e "${Y}${B}════════════════════════════════════════════════════════${N}"
echo ""
echo -e "  ${B}Novedades en esta versión:${N}"
echo -e "  • Bloqueo de acceso por licencia expirada/inactiva"
echo -e "  • Página /license-expired/ con logo y contacto qustodia@sqasa.co"
echo -e "  • Botón 'Nuevo Pentest' en /pentest/ y en el menú del Engagement"
echo ""
echo -e "  ${B}Próximos pasos:${N}"
echo -e "  1. Entrar al admin → /admin/license_manager/clientlicense/"
echo -e "  2. Crear la licencia del cliente con fecha de vencimiento del PoC"
echo -e "  3. Asignar el Producto (activo) correspondiente a la licencia"
echo ""
