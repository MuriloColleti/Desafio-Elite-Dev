"""Bootstrap do FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import auth, catalog, events, gate, payments, reservations, tickets
from app.core.config import settings
from app.core.db import engine
from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.core.redis_client import ping as redis_ping

app = FastAPI(
    title=settings.app_name,
    description="Plataforma de Eventos e Ingressos — Desafio Elite Dev",
    version="0.1.0",
    debug=settings.debug,
)

# allow_credentials=True é obrigatório aqui: o session_id vai por cookie, e sem
# isso o navegador não o envia em requisição cross-origin. Por isso também não
# é possível usar "*" em allow_origins — a lista tem de ser explícita.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(events.router)
app.include_router(reservations.router)
app.include_router(payments.router)
app.include_router(tickets.router)
app.include_router(gate.router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, object]:
    """Estado das dependências, separadamente.

    Banco e Redis têm papéis diferentes: sem banco não há ingresso; sem Redis
    ninguém entra, mas nada se perde. O health reflete essa distinção para o
    diagnóstico não virar adivinhação.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    redis_ok = redis_ping()

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "database": "up" if db_ok else "down",
        "redis": "up" if redis_ok else "down",
        "catalog": "offline" if settings.catalog_offline else "online",
    }
