import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.audit import HIPAAAuditMiddleware
from api.middleware.error_handler import careguard_exception_handler, unhandled_exception_handler
from api.routes import dashboard, discharge, twilio_voice
from config import get_settings
from exceptions import CareGuardError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()

app = FastAPI(
    title="CareGuard API",
    version=settings.app_version,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)

# Middleware (order matters — outermost runs first)
app.add_middleware(HIPAAAuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.careguard.health"] if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(CareGuardError, careguard_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routers
app.include_router(discharge.router)
app.include_router(twilio_voice.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok", "version": settings.app_version}
