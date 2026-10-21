#!/usr/bin/env bash
# deploy-poc.sh — Despliegue QustodIA completo en servidor cliente
set -euo pipefail

APP=/opt/qustodia/app
echo "▶ [1/7] Directorio de trabajo..."
cd "$APP"

echo "▶ [2/7] Actualizando código..."
git pull origin qustodia/core-vnext

echo "▶ [3/7] Activando overlay QustodIA SQA SA..."
cp docker-compose.override.sqa.yml docker-compose.override.yml

echo "▶ [4/7] Verificando red Docker..."
docker network create qustodia-net 2>/dev/null || echo "   Red qustodia-net ya existe"

echo "▶ [5/7] Reiniciando contenedores con diseño SQA SA..."
docker compose down
docker compose up -d
echo "   Esperando que uwsgi arranque (60 seg)..."
sleep 60

echo "▶ [6/7] Aplicando migraciones de módulos QustodIA..."
docker compose exec -T uwsgi python manage.py migrate --run-syncdb

echo "▶ [7/7] Iniciando Go-Live Agent (Release Manager)..."
cd "$APP/go-live-agent"
TOKEN=$(docker compose -f ../docker-compose.yml exec -T uwsgi python manage.py shell -c \
  "from rest_framework.authtoken.models import Token; from django.contrib.auth import get_user_model; u=get_user_model().objects.get(username='admin'); t,_=Token.objects.get_or_create(user=u); print(t.key)" 2>/dev/null | tail -1)
if [ -n "$TOKEN" ]; then
  printf "DEFECTDOJO_BASE_URL=http://nginx:8080\nDEFECTDOJO_API_TOKEN=%s\nLLM_ENABLED=false\nLLM_PROVIDER=groq\n" "$TOKEN" > .env
  echo "   Token obtenido correctamente"
else
  echo "   AVISO: no se pudo obtener el token — el agente inicia sin conexión a DefectDojo"
  printf "DEFECTDOJO_BASE_URL=http://nginx:8080\nDEFECTDOJO_API_TOKEN=change-me\nLLM_ENABLED=false\nLLM_PROVIDER=groq\n" > .env
fi
docker compose up -d --build

echo ""
echo "✓ Despliegue completado."
echo "  Abrir en el navegador: http://$(hostname -I | awk '{print $1}'):8080"
echo "  Módulos activos: Pentest · Bolsa de Horas · Concepto de Seguridad · Informe Ejecutivo · Métricas SQA · Release Manager"
