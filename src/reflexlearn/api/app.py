from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from reflexlearn.api.routes import auth, health, chat, knowledge, video
from reflexlearn.common.auth import validate_auth_runtime
from reflexlearn.common.config import get_settings
from reflexlearn.common.db import lifespan_db
from reflexlearn.common.logging import configure_logging


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
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(knowledge.router, prefix="/api", tags=["knowledge"])
    app.include_router(video.router, prefix="/api", tags=["video"])
    return app
