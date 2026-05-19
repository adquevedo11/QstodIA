# QstodIA — Go-Live Security Readiness Agent

Agente de inteligencia artificial para análisis automatizado de preparación de seguridad antes de salidas a producción (Go-Live). Se integra con **DefectDojo** para leer hallazgos de seguridad, clasificarlos mediante reglas determinísticas y enriquecerlos con IA, generando reportes ejecutivos en formato JSON, Markdown, HTML y PDF.

Desarrollado por **SQA SA** como componente del ecosistema VMaaS 2.0.

---

## Tabla de Contenidos

- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Endpoints API](#endpoints-api)
- [Lógica de Clasificación](#lógica-de-clasificación)
- [Enriquecimiento con IA](#enriquecimiento-con-ia)
- [Formatos de Reporte](#formatos-de-reporte)
- [Integración con DefectDojo](#integración-con-defectdojo)
- [Caché](#caché)
- [Despliegue en Producción](#despliegue-en-producción)
- [Desarrollo y Tests](#desarrollo-y-tests)
- [Estructura del Proyecto](#estructura-del-proyecto)

---

## Arquitectura

```
                        ┌─────────────────────────────────┐
                        │        DefectDojo (Django)       │
                        │  Engagement → Go-Live Report     │
                        │  (botón en menú de engagement)   │
                        └────────────────┬─────────────────┘
                                         │ HTTP POST
                                         ▼
                        ┌─────────────────────────────────┐
                        │     QstodIA — FastAPI Agent      │
                        │                                  │
                        │  1. Consulta findings en DD      │
                        │  2. Clasifica (reglas determin.) │
                        │  3. Enriquece con IA (Groq/GPT)  │
                        │  4. Genera reporte + PDF         │
                        │  5. Caché 24h por engagement     │
                        └────────────────┬─────────────────┘
                                         │
                    ┌────────────────────┼──────────────────┐
                    ▼                    ▼                   ▼
              JSON Report          HTML/PDF             Markdown
```

### Flujo de Datos

```
DefectDojo API
    │
    ▼ GET /api/v2/findings/?test__engagement={id}
DefectDojoClient._map_finding()
    │
    ▼ list[Finding]
ReadinessAgent.generate_report()
    │
    ├─▶ scoring.classify(finding) × N  →  ReadinessDecision (8 reglas)
    ├─▶ Agrupación por categoría
    ├─▶ Generación de summaries (ejecutivo + técnico)
    │
    ▼ ReadinessReport
LLMEnrichmentAgent.enrich()  (Critical/High/Medium, si LLM_ENABLED=true)
    │
    ▼ ReadinessReport enriquecido
cache.set(engagement_id, findings_hash, report)
    │
    ▼
Salida: JSON | Markdown | HTML | PDF
```

---

## Requisitos

- **Python** 3.11+
- **Docker** y **Docker Compose**
- Instancia de **DefectDojo** accesible con token API
- (Opcional) API key de **Groq** o **OpenAI** para enriquecimiento IA

### Dependencias del sistema (para generación PDF)

```
libcairo2, libpango-1.0-0, libpangocairo-1.0-0, libpangoft2-1.0-0,
libgdk-pixbuf-xlib-2.0-0, libffi-dev, shared-mime-info, fonts-liberation
```

Estas dependencias se instalan automáticamente al construir la imagen Docker.

---

## Instalación

### Con Docker (recomendado)

```bash
git clone https://github.com/adquevedo11/QstodIA.git
cd QstodIA
cp .env.example .env
# Editar .env con tus credenciales
docker compose up -d --build
```

### Sin Docker (desarrollo local)

```bash
git clone https://github.com/adquevedo11/QstodIA.git
cd QstodIA
pip install -e ".[dev]"
cp .env.example .env
# Editar .env con tus credenciales
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Configuración

Copia `.env.example` a `.env` y configura las variables:

```env
# ── DefectDojo ────────────────────────────────────────────────────
DEFECTDOJO_BASE_URL=https://tu-instancia.defectdojo.com
DEFECTDOJO_API_TOKEN=tu-api-token-aqui

# ── LLM (enriquecimiento con IA) ──────────────────────────────────
LLM_ENABLED=true
LLM_PROVIDER=groq              # "groq" o "openai"
LLM_MODEL=llama-3.3-70b-versatile

# Groq (gratuito, recomendado)
GROQ_API_KEY=gsk_...

# OpenAI (alternativo)
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o
```

### Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `DEFECTDOJO_BASE_URL` | URL base de DefectDojo | `http://localhost:8080` |
| `DEFECTDOJO_API_TOKEN` | Token de API de DefectDojo | `""` |
| `LLM_ENABLED` | Activar enriquecimiento con IA | `false` |
| `LLM_PROVIDER` | Proveedor LLM: `groq` o `openai` | `groq` |
| `LLM_MODEL` | Modelo a usar | `llama-3.3-70b-versatile` |
| `GROQ_API_KEY` | API key de Groq | `""` |
| `OPENAI_API_KEY` | API key de OpenAI | `""` |

---

## Uso

### Via API REST

```bash
# Health check
curl http://localhost:8001/health

# Analizar findings JSON directamente
curl -X POST http://localhost:8001/readiness/analyze \
  -H "Content-Type: application/json" \
  -d @examples/sample_findings.json

# Reporte desde DefectDojo (JSON)
curl -X POST http://localhost:8001/readiness/analyze/defectdojo \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "engagement_id": 5, "target_go_live_date": "2026-06-30"}'

# Reporte PDF
curl -X POST http://localhost:8001/readiness/report/defectdojo/pdf \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "engagement_id": 5, "target_go_live_date": "2026-06-30"}' \
  --output reporte-go-live.pdf
```

### Via CLI

```bash
python -m app.cli examples/sample_findings.json \
  --product "Mi Aplicación" \
  --engagement "Sprint 23 - Go-Live" \
  --go-live-date "2026-06-30" \
  --output reporte.md \
  --format markdown
```

---

## Endpoints API

| Método | Endpoint | Descripción | Respuesta |
|---|---|---|---|
| `GET` | `/health` | Estado del servicio | JSON |
| `POST` | `/readiness/analyze` | Analiza findings JSON | `ReadinessReport` JSON |
| `POST` | `/readiness/report/markdown` | Reporte desde JSON | Markdown |
| `POST` | `/readiness/analyze/defectdojo` | Analiza desde DefectDojo | `ReadinessReport` JSON |
| `POST` | `/readiness/report/defectdojo/markdown` | Reporte desde DefectDojo | Markdown |
| `POST` | `/readiness/report/defectdojo/html` | Reporte desde DefectDojo | HTML |
| `POST` | `/readiness/report/defectdojo/pdf` | Reporte desde DefectDojo | PDF |

### Schema de entrada (DefectDojo)

```json
{
  "product_id": 1,
  "engagement_id": 5,
  "target_go_live_date": "2026-06-30"
}
```

### Schema de entrada (findings directos)

```json
{
  "product_name": "Mi App",
  "engagement_name": "Sprint 23",
  "target_go_live_date": "2026-06-30",
  "findings": [
    {
      "id": "123",
      "title": "SQL Injection en login",
      "severity": "Critical",
      "active": true,
      "verified": true,
      "false_positive": false,
      "risk_accepted": false,
      "tags": ["auth", "injection"],
      "cwe": "89",
      "description": "...",
      "component": "backend-api"
    }
  ]
}
```

---

## Lógica de Clasificación

El motor determinístico aplica **8 reglas en orden** para clasificar cada hallazgo:

| # | Condición | Categoría | Descripción |
|---|---|---|---|
| 1 | `false_positive = true` | `informational` | Falso positivo, sin acción |
| 2 | `risk_accepted = true` | `accepted` | Riesgo aceptado formalmente |
| 3 | `Critical` + activo + verificado | `blocker` | Bloquea el Go-Live |
| 4 | `Critical` + activo (sin verificar) | `blocker` | Requiere verificación y remediación |
| 5 | `High` + activo + tags/flujo crítico | `blocker` | Componente crítico de negocio |
| 6 | `High` + activo | `high_pre_go_live` | Remediar antes del Go-Live |
| 7 | `Medium` + activo + tags control crítico | `high_pre_go_live` | Control crítico afectado |
| 8 | `active = false` | `mitigated` | Hallazgo resuelto o inactivo |
| — | Resto | `post_go_live` | Remediar después del Go-Live |

### Recomendación de Go-Live

| Condición | Recomendación |
|---|---|
| Existe al menos 1 `blocker` | **No-Go** |
| Existe al menos 1 `high_pre_go_live` | **Go condicionado** |
| Sin bloqueantes ni alta prioridad | **Go** |

### Tags que disparan `blocker`

`auth`, `mfa`, `payment`, `transfer`, `replay`, `authorization`, `privilege-escalation`

### Tags que disparan `high_pre_go_live`

`security-gate`, `logging`, `audit`, `monitoring`

### Flujos de negocio críticos (→ `blocker`)

`high-value-transfer`, `beneficiary-registration`, `payment-processing`, `authentication`

---

## Enriquecimiento con IA

Cuando `LLM_ENABLED=true`, los hallazgos **Critical, High y Medium** se enriquecen automáticamente con:

| Campo | Descripción |
|---|---|
| `executive_risk_explanation` | Impacto en negocio en lenguaje ejecutivo |
| `remediation_guidance` | Guía técnica de remediación paso a paso |
| `acceptance_criteria` | Criterios para considerar el hallazgo resuelto |
| `negative_tests` | Pruebas negativas sugeridas para validar la corrección |
| `compensating_controls` | Controles compensatorios temporales |

### Proveedores soportados

| Proveedor | Modelo recomendado | Notas |
|---|---|---|
| **Groq** (recomendado) | `llama-3.3-70b-versatile` | Gratuito, altos límites de rate |
| **OpenAI** | `gpt-4o` | De pago, 30k TPM en tier básico |

> El agente usa un prompt de sistema controlado que impide que la IA cambie severidades, apruebe riesgos ni invente evidencia.

---

## Formatos de Reporte

### JSON (`ReadinessReport`)

Estructura completa con todos los campos, ideal para integración con otros sistemas.

### Markdown

Reporte tabular con secciones por categoría, optimizado para GitHub, Confluence o Jira.

### HTML / PDF

Reporte profesional con:
- Portada con logo SQA SA
- Barra de recomendación con código de color (verde/rojo/naranja)
- Tarjetas por hallazgo con badge de severidad
- Estadísticas visuales (píldoras de conteo por categoría)
- Sección de enriquecimiento IA destacada con badge "IA"
- Plan de remediación priorizado
- Sección de hallazgos mitigados separada de falsos positivos
- Compatible con impresión y descarga directa

---

## Integración con DefectDojo

El agente se integra nativamente con DefectDojo a través de su API REST v2.

### Configuración de red (Docker)

Ambos servicios deben estar en la misma red Docker externa `sqasa`:

```bash
# Crear la red compartida en el servidor
docker network create sqasa
```

```yaml
# docker-compose.yml del agente
networks:
  sqasa:
    name: sqasa
    external: true
```

```yaml
# docker-compose.override.sqa.yml de DefectDojo
services:
  nginx:
    networks: [default, sqasa]
  uwsgi:
    networks: [default, sqasa]
    environment:
      GOLIVE_AGENT_URL: "http://go-live-agent:8001"
```

### Campos mapeados desde DefectDojo

| Campo DefectDojo | Campo Finding | Descripción |
|---|---|---|
| `id` | `id` | Identificador único |
| `title` | `title` | Título del hallazgo |
| `severity` | `severity` | Critical/High/Medium/Low/Info |
| `active` | `active` | Si el hallazgo está activo |
| `verified` | `verified` | Si fue verificado manualmente |
| `false_p` | `false_positive` | Marcado como falso positivo |
| `risk_accepted` | `risk_accepted` | Riesgo formalmente aceptado |
| `component_name` | `component` | Componente afectado |
| `cwe` | `cwe` | ID del CWE asociado |
| `cvssv3_score` | `cvss_score` | Score CVSS v3 |
| `description` | `description` | Descripción detallada |
| `mitigation` | `mitigation` | Mitigación documentada |
| `references` | `evidence` | Referencias y evidencia |
| `tags` | `tags` | Etiquetas del hallazgo |

### Owner sugerido (automático)

El agente infiere el equipo responsable en este orden de prioridad:

1. **Tags explícitos** — `auth` → Equipo de Identidad, `payment` → Equipo de Pagos
2. **Campo Component** — `backend-api` → "Equipo responsable de backend-api"
3. **Número CWE** — `CWE-89` → Equipo de Desarrollo, `CWE-295` → Equipo de Infraestructura
4. **Palabras clave en título** — "SQL injection" → Equipo de Desarrollo
5. **Fallback** — Equipo de Desarrollo

---

## Caché

El agente implementa caché de reportes basada en archivo para evitar llamadas repetidas a la IA.

- **Mecanismo:** Hash MD5 de los IDs de findings del engagement (12 caracteres)
- **TTL:** 24 horas
- **Ubicación:** `/app/.cache/report_{engagement_id}_{hash}.json`
- **Invalidación automática:** Si los findings cambian (nuevo hallazgo, cierre, etc.)

```bash
# Limpiar caché manualmente
docker exec <container> bash -c "rm -f /app/.cache/*.json"
```

---

## Despliegue en Producción

### 1. Crear red Docker compartida

```bash
docker network create sqasa
```

### 2. Configurar `.env` de producción

```env
DEFECTDOJO_BASE_URL=http://nginx:8080   # Via red Docker interna
DEFECTDOJO_API_TOKEN=tu-token-produccion
LLM_ENABLED=true
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=gsk_...
```

### 3. Desplegar el agente

```bash
docker compose up -d --build
```

### 4. Verificar conectividad

```bash
curl http://localhost:8001/health
docker network inspect sqasa --format "{{range .Containers}}{{.Name}} {{end}}"
```

### Configuración nginx (timeout para reportes largos)

Agregar en el bloque `server` del reverse proxy externo:

```nginx
location ~* /go-live-readiness/data/ {
    proxy_pass http://127.0.0.1:8888;
    proxy_read_timeout 660;
    proxy_send_timeout 660;
    proxy_connect_timeout 660;
}
```

---

## Desarrollo y Tests

### Ejecutar tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Tests disponibles

| Archivo | Descripción |
|---|---|
| `tests/test_scoring.py` | Lógica de clasificación (8 reglas) |
| `tests/test_readiness_agent.py` | Motor principal de análisis |
| `tests/test_llm_enrichment.py` | Backends LLM (con FakeLLMBackend) |
| `tests/test_api.py` | Endpoints FastAPI |

### Modo LLM fake (para tests sin API)

```env
LLM_ENABLED=true
LLM_PROVIDER=fake
```

### Linting

```bash
ruff check app/
ruff format app/
```

---

## Estructura del Proyecto

```
QstodIA/
├── app/
│   ├── main.py                    # Punto de entrada FastAPI
│   ├── config.py                  # Variables de entorno
│   ├── cache.py                   # Caché de reportes (24h TTL)
│   ├── cli.py                     # Interfaz de línea de comandos
│   ├── agents/
│   │   ├── readiness_agent.py     # Motor principal de análisis
│   │   └── llm_enrichment_agent.py # Enriquecimiento IA (Groq/OpenAI)
│   ├── api/
│   │   └── routes.py              # Endpoints REST
│   ├── clients/
│   │   └── defectdojo_client.py   # Cliente DefectDojo API v2
│   ├── domain/
│   │   ├── models.py              # Modelos Pydantic
│   │   ├── scoring.py             # Clasificación determinística
│   │   └── rules.py               # Reglas, tags y templates
│   ├── reports/
│   │   ├── html_report.py         # Generador HTML/PDF
│   │   └── markdown_report.py     # Generador Markdown
│   └── static/
│       └── sqa_logo.png           # Logo para PDF
├── tests/
│   ├── test_api.py
│   ├── test_readiness_agent.py
│   ├── test_scoring.py
│   └── test_llm_enrichment.py
├── examples/
│   └── sample_findings.json       # Ejemplo de findings
├── .env.example                   # Plantilla de configuración
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## Stack Tecnológico

| Componente | Tecnología | Versión |
|---|---|---|
| Framework web | FastAPI | ≥ 0.111.0 |
| Servidor ASGI | Uvicorn + Watchfiles | ≥ 0.29.0 |
| Validación | Pydantic | ≥ 2.7.0 |
| HTTP client | httpx | ≥ 0.27.0 |
| Config | python-dotenv | ≥ 1.0.0 |
| LLM | openai SDK | ≥ 1.30.0 |
| PDF | WeasyPrint | latest |
| Tests | pytest + pytest-asyncio | dev |
| Linting | ruff | dev |
| Python | 3.11+ | — |
| Contenedor | Docker (python:3.11-slim) | — |

---

## Licencia

Propiedad de **SQA SA**. Uso interno. Todos los derechos reservados.

---

*QstodIA — Go-Live Security Readiness Agent · SQA SA · Security Quality Assurance*
