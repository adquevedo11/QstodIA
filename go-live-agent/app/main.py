from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Go-Live Security Readiness Agent",
    description="Analiza hallazgos de seguridad y determina la readiness para Go-Live.",
    version="0.1.0",
)

app.include_router(router)
