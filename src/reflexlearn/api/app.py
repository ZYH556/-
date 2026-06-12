from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from reflexlearn.api.routes import (
    auth,
    chat,
    health,
    knowledge,
    mistakes,
    profile,
    today,
    traces,
    tutor,
    video,
    workspace,
)
from reflexlearn.common.auth import validate_auth_runtime
from reflexlearn.common.config import get_settings
from reflexlearn.common.db import lifespan_db
from reflexlearn.common.logging import configure_logging
from reflexlearn.observability.metrics import instrument_app
from reflexlearn.observability.routes import router as metrics_router
from reflexlearn.security.csrf import CSRFMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with lifespan_db():
        yield


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    validate_auth_runtime(settings)
    app = FastAPI(
        title="ReflexLearn Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=_split_csv(settings.trusted_hosts),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_split_csv(settings.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    app.add_middleware(CSRFMiddleware)
    instrument_app(app)
    app.include_router(metrics_router, tags=["observability"])
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(knowledge.router, prefix="/api", tags=["knowledge"])
    app.include_router(workspace.router, prefix="/api", tags=["workspace"])
    app.include_router(mistakes.router, prefix="/api", tags=["mistakes"])
    app.include_router(traces.router, prefix="/api", tags=["collaboration"])
    app.include_router(video.router, prefix="/api", tags=["video"])
    app.include_router(profile.router, prefix="/api", tags=["profile"])
    app.include_router(today.router, prefix="/api", tags=["today"])
    app.include_router(tutor.router, prefix="/api", tags=["tutor"])
    return app
