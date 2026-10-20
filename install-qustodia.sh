#!/usr/bin/env bash
# ================================================================
#  QustodIA — Instalador Automático v1.0
#  SQA SA · Plataforma de Gestión de Seguridad de Aplicaciones
#
#  Uso: sudo bash install-qustodia.sh
# ================================================================

set -euo pipefail

# ── Configuración interna (no modificar) ─────────────────────
REPO_URL="https://github.com/adquevedo11/QstodIA.git"
REPO_BRANCH="qustodia/core-vnext"
INSTALL_DIR="/opt/qustodia"
APP_DIR="${INSTALL_DIR}/app"
AGENT_DIR="${INSTALL_DIR}/agent"
NETWORK_NAME="qustodia-net"
PROJECT_NAME="qustodia"

# ── Colores ──────────────────────────────────────────────────
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m'
C='\033[0;36m' B='\033[1m'   N='\033[0m'

# ── UI helpers ────────────────────────────────────────────────
step() { echo -e "\n${Y}[$(date +%H:%M:%S)]${N} ${B}$*${N}"; }
ok()   { echo -e "  ${G}✓${N} $*"; }
info() { echo -e "  ${C}ℹ${N} $*"; }
warn() { echo -e "  ${Y}⚠${N} $*"; }
die()  { echo -e "\n${R}ERROR: $*${N}\n" >&2; exit 1; }

banner() {
  echo -e "\n${Y}${B}"
  echo "   ___  __ _  __  __  ___  ____  ___  ____  ____   __"
  echo "  / _ \/ // / / / / / / __//  _// _ \/ / / /__  \ / /"
  echo " / // / // / /  \/ /_\__ \_/ /_/ // /  / /    / // / "
  echo "/____/\__/  \____/ /_/\___/___//____/  /_/ /___// / "
  echo "                                             /____/    "
  echo -e "${N}"
  echo -e "  ${B}ASPM Platform — Instalador Automático v1.0${N}"
  echo -e "  ${C}SQA SA · Octubre 2026${N}"
  echo -e "\n  Este script instala y configura QustodIA completamente"
  echo -e "  en este servidor desde cero, incluyendo inicio automático."
  echo ""
}

# ── Verificaciones previas ────────────────────────────────────
preflight() {
  [[ $EUID -ne 0 ]] && die "Ejecutar como root:  sudo bash $0"

  # Verificar Ubuntu
  if ! grep -qi ubuntu /etc/os-release 2>/dev/null; then
    warn "Este script está optimizado para Ubuntu. Continuar bajo tu responsabilidad."
  fi

  # Verificar conexión a internet
  if ! curl -fsSL --max-time 10 https://github.com >/dev/null 2>&1; then
    die "Sin acceso a internet. Verificar conectividad."
  fi
  ok "Pre-flight: root, internet OK"
}

# ── Recopilar configuración ──────────────────────────────────
gather_config() {
  step "Configuración inicial"

  # Detectar IP pública
  SERVER_IP=$(curl -fsSL --max-time 5 ifconfig.me 2>/dev/null \
    || hostname -I | awk '{print $1}')

  echo ""
  read -rp "  IP o dominio del servidor [${SERVER_IP}]: " _in
  SERVER_IP="${_in:-$SERVER_IP}"

  echo ""
  while true; do
    read -rsp "  Contraseña del administrador (mín. 8 caracteres): " ADMIN_PASSWORD
    echo ""
    [[ ${#ADMIN_PASSWORD} -ge 8 ]] && break
    warn "La contraseña necesita al menos 8 caracteres. Intenta de nuevo."
  done

  read -rsp "  Confirmar contraseña: " ADMIN_PASSWORD2; echo
  [[ "$ADMIN_PASSWORD" != "$ADMIN_PASSWORD2" ]] && die "Las contraseñas no coinciden"

  echo ""
  read -rp "  Email del administrador [admin@qustodia.local]: " _in
  ADMIN_EMAIL="${_in:-admin@qustodia.local}"

  read -rp "  Nombre del cliente: " CLIENT_NAME
  CLIENT_NAME="${CLIENT_NAME:-Empresa Cliente}"

  # Confirmar
  echo ""
  echo -e "  ${B}Resumen de configuración:${N}"
  echo -e "  • Servidor:    ${Y}${SERVER_IP}${N}"
  echo -e "  • Email admin: ${Y}${ADMIN_EMAIL}${N}"
  echo -e "  • Cliente:     ${Y}${CLIENT_NAME}${N}"
  echo -e "  • Directorio:  ${Y}${INSTALL_DIR}${N}"
  echo -e "  • Proyecto:    ${Y}${PROJECT_NAME}${N}"
  echo ""
  read -rp "  ¿Iniciar instalación? [S/n]: " _in
  [[ "${_in,,}" == "n" ]] && { echo "Cancelado."; exit 0; }
}

# ── 1. Actualizar sistema ─────────────────────────────────────
install_system_deps() {
  step "Actualizando sistema e instalando dependencias"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get upgrade -y -qq
  apt-get install -y -qq \
    git curl ca-certificates gnupg python3 openssl
  ok "Sistema actualizado"
}

# ── 2. Docker Engine ──────────────────────────────────────────
install_docker() {
  step "Instalando Docker Engine"

  if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    ok "Docker ya instalado: $(docker --version | cut -d' ' -f3)"
    ok "Compose: $(docker compose version --short 2>/dev/null || echo 'v2')"
    return 0
  fi

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc 2>/dev/null
  chmod a+r /etc/apt/keyrings/docker.asc

  # shellcheck disable=SC1091
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
    https://download.docker.com/linux/ubuntu ${VERSION_CODENAME:-noble} stable" \
    | tee /etc/apt/sources.list.d/docker.list >/dev/null

  apt-get update -qq
  apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

  systemctl enable docker --now
  ok "Docker instalado: $(docker --version | cut -d' ' -f3)"
  ok "Compose: $(docker compose version --short 2>/dev/null || echo 'v2')"
}

# ── 3. Directorios ────────────────────────────────────────────
create_dirs() {
  step "Preparando directorios de instalación"
  mkdir -p "${APP_DIR}" "${AGENT_DIR}"
  ok "${INSTALL_DIR}/ listo"
}

# ── 4. Repositorio ────────────────────────────────────────────
clone_repo() {
  step "Clonando repositorio QustodIA"

  if [[ -d "${APP_DIR}/.git" ]]; then
    info "Repositorio ya existe — actualizando al último commit..."
    git -C "${APP_DIR}" fetch --quiet origin "${REPO_BRANCH}"
    git -C "${APP_DIR}" reset --hard "origin/${REPO_BRANCH}" --quiet
    ok "Repositorio actualizado"
  else
    git clone \
      --branch "${REPO_BRANCH}" \
      --depth 1 \
      --quiet \
      "${REPO_URL}" \
      "${APP_DIR}"
    ok "Repositorio clonado (rama: ${REPO_BRANCH})"
  fi

  # Verificar si el agente viene en el repo
  AGENT_IN_REPO="false"
  for p in \
    "${APP_DIR}/go-live-agent" \
    "${APP_DIR}/go-live-readiness-agent/app" \
    "${APP_DIR}/go-live-readiness-agent"; do
    if [[ -f "${p}/docker-compose.yml" ]]; then
      AGENT_IN_REPO="${p}"
      ok "Go-live agent encontrado en el repo: ${p}"
      break
    fi
  done
}

# ── 5. Configuración compose ──────────────────────────────────
create_config() {
  step "Generando configuración de entorno"

  # Secret key única para esta instancia
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(50))")

  cat > "${APP_DIR}/docker-compose.override.yml" <<OVERRIDE
version: '3'

services:
  uwsgi:
    restart: unless-stopped
    environment:
      DD_SECRET_KEY: "${SECRET_KEY}"
      DD_ALLOWED_HOSTS: "localhost,127.0.0.1,${SERVER_IP}"
      DD_ADMIN_USER: "admin"
      DD_ADMIN_PASSWORD: "${ADMIN_PASSWORD}"
      DD_ADMIN_MAIL: "${ADMIN_EMAIL}"
      DD_OS_MESSAGE_ENABLED: "false"
      GOLIVE_AGENT_URL: "http://go-live-agent:8001"
    networks:
      - default
      - ${NETWORK_NAME}

  nginx:
    restart: unless-stopped
    ports:
      - "80:8080"
    networks:
      - default
      - ${NETWORK_NAME}

  celery:
    restart: unless-stopped

  celerybeat:
    restart: unless-stopped

  postgresql:
    restart: unless-stopped

networks:
  ${NETWORK_NAME}:
    external: true
OVERRIDE

  ok "docker-compose.override.yml generado"

  # Guardar configuración en log local (sin la contraseña)
  cat > "${INSTALL_DIR}/install-info.txt" <<INFO
QustodIA - Información de Instalación
Fecha: $(date)
Servidor: ${SERVER_IP}
Email admin: ${ADMIN_EMAIL}
Cliente: ${CLIENT_NAME}
Proyecto Docker: ${PROJECT_NAME}
Red Docker: ${NETWORK_NAME}
Directorio app: ${APP_DIR}
Directorio agente: ${AGENT_DIR}
INFO
  ok "Información de instalación guardada en ${INSTALL_DIR}/install-info.txt"
}

# ── 6. Red Docker ─────────────────────────────────────────────
setup_network() {
  step "Configurando red Docker interna"

  if docker network inspect "${NETWORK_NAME}" &>/dev/null; then
    info "Red '${NETWORK_NAME}' ya existe"
  else
    docker network create "${NETWORK_NAME}"
    ok "Red '${NETWORK_NAME}' creada"
  fi
}

# ── 7. Iniciar QustodIA ───────────────────────────────────────
start_platform() {
  step "Iniciando QustodIA (primera vez: 5-10 minutos)"

  cd "${APP_DIR}"

  info "Descargando imágenes Docker..."
  docker compose --project-name "${PROJECT_NAME}" pull --quiet 2>&1 | \
    grep -E "^(Pulling|Downloaded|Image)" || true

  docker compose --project-name "${PROJECT_NAME}" up -d

  ok "Contenedores iniciados"
  info "Esperando inicialización de la base de datos..."

  local max_wait=300
  local waited=0
  local ready=false

  while [[ $waited -lt $max_wait ]]; do
    if docker exec "${PROJECT_NAME}-uwsgi-1" \
        python manage.py check --database default \
        >/dev/null 2>&1; then
      ready=true
      break
    fi
    printf "."
    sleep 6
    waited=$((waited + 6))
  done
  echo ""

  if $ready; then
    ok "QustodIA listo y respondiendo"
  else
    warn "Inicialización lenta — la app puede aún estar cargando"
    warn "Verifica con: docker compose -f ${APP_DIR}/docker-compose.yml logs uwsgi"
  fi
}

# ── 8. Bridge de red ──────────────────────────────────────────
connect_bridge() {
  step "Conectando servicios a la red interna"
  sleep 5

  if docker network connect --alias nginx "${NETWORK_NAME}" \
      "${PROJECT_NAME}-nginx-1" 2>/dev/null; then
    ok "nginx conectado a '${NETWORK_NAME}'"
  else
    info "nginx ya estaba conectado a '${NETWORK_NAME}'"
  fi
}

# ── 9. Go-live agent ──────────────────────────────────────────
deploy_agent() {
  step "Configurando Go-Live Readiness Agent"

  if [[ "${AGENT_IN_REPO}" != "false" ]]; then
    # Copiar al directorio de agente si no es el mismo
    if [[ "${AGENT_IN_REPO}" != "${AGENT_DIR}" ]]; then
      cp -r "${AGENT_IN_REPO}/." "${AGENT_DIR}/"
    fi

    # Crear .env con placeholder para el token
    cat > "${AGENT_DIR}/.env" <<AGENTENV
DEFECTDOJO_BASE_URL=http://nginx:8080
DEFECTDOJO_API_TOKEN=PENDIENTE_CONFIGURAR
AGENTENV

    cd "${AGENT_DIR}"
    docker compose up -d --build
    ok "Go-live agent iniciado"
    warn "El token de API debe configurarse después del primer login (ver PASO FINAL)"
  else
    warn "Código del agente no encontrado en el repositorio"
    info "Transferir manualmente al directorio: ${AGENT_DIR}"
    info "Luego ejecutar: cd ${AGENT_DIR} && docker compose up -d"
  fi
}

# ── 10. Systemd ───────────────────────────────────────────────
setup_systemd() {
  step "Configurando inicio automático (systemd)"

  # Servicio principal
  cat > /etc/systemd/system/qustodia.service <<UNIT
[Unit]
Description=QustodIA ASPM Platform
Documentation=https://sqasa.co
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/docker compose --project-name ${PROJECT_NAME} up -d
ExecStartPost=/bin/bash -c 'sleep 10 && /usr/bin/docker network connect --alias nginx ${NETWORK_NAME} ${PROJECT_NAME}-nginx-1 2>/dev/null || true'
ExecStop=/usr/bin/docker compose --project-name ${PROJECT_NAME} down
TimeoutStartSec=300
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
UNIT

  # Servicio del agente
  cat > /etc/systemd/system/qustodia-agent.service <<UNIT
[Unit]
Description=QustodIA Go-Live Readiness Agent
Documentation=https://sqasa.co
Requires=docker.service qustodia.service
After=qustodia.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${AGENT_DIR}
ExecStartPre=/bin/sleep 15
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
UNIT

  systemctl daemon-reload
  systemctl enable qustodia.service
  ok "qustodia.service habilitado"

  if [[ -f "${AGENT_DIR}/docker-compose.yml" ]]; then
    systemctl enable qustodia-agent.service
    ok "qustodia-agent.service habilitado"
  fi

  ok "QustodIA se iniciará automáticamente al encender/reiniciar el servidor"
}

# ── Resumen final ─────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${Y}${B}════════════════════════════════════════════════════════${N}"
  echo -e "${G}${B}  ✓  QUSTODIA INSTALADO CORRECTAMENTE${N}"
  echo -e "${Y}${B}════════════════════════════════════════════════════════${N}"
  echo ""
  echo -e "  ${B}Acceso a la plataforma:${N}"
  echo -e "  • URL:         ${Y}http://${SERVER_IP}/${N}"
  echo -e "  • Usuario:     ${Y}admin${N}"
  echo -e "  • Contraseña:  [la que configuraste]"
  echo ""
  echo -e "  ${B}Gestión del servicio:${N}"
  echo -e "  • Estado:      ${C}systemctl status qustodia${N}"
  echo -e "  • Logs:        ${C}journalctl -u qustodia -f${N}"
  echo -e "  • Reiniciar:   ${C}systemctl restart qustodia${N}"
  echo -e "  • Detener:     ${C}systemctl stop qustodia${N}"
  echo ""
  echo -e "  ${B}Contenedores activos:${N}"
  echo -e "  • Listar:      ${C}docker ps --filter name=${PROJECT_NAME}${N}"
  echo -e "  • Logs app:    ${C}docker logs ${PROJECT_NAME}-uwsgi-1 --tail=30${N}"
  echo ""
  echo -e "  ${Y}${B}⚠  PASO FINAL OBLIGATORIO — Configurar el token del agente:${N}"
  echo ""
  echo -e "     1. Abrir en el navegador: ${Y}http://${SERVER_IP}/${N}"
  echo -e "     2. Login como admin"
  echo -e "     3. Menú usuario → Profile → API v2 Key → copiar token"
  echo -e "     4. En el servidor ejecutar:"
  echo -e "        ${C}nano ${AGENT_DIR}/.env${N}"
  echo -e "        → cambiar PENDIENTE_CONFIGURAR por el token real"
  echo -e "     5. ${C}systemctl restart qustodia-agent${N}"
  echo ""
  echo -e "  ${B}SQA SA · andres.quevedo@sqasa.co${N}"
  echo -e "${Y}${B}════════════════════════════════════════════════════════${N}"
  echo ""
}

# ── Main ──────────────────────────────────────────────────────
main() {
  banner
  preflight
  gather_config
  install_system_deps
  install_docker
  create_dirs
  clone_repo
  create_config
  setup_network
  start_platform
  connect_bridge
  deploy_agent
  setup_systemd
  print_summary
}

main "$@"
