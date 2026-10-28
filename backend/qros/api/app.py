"""Dashboard process: database access only; never starts an executor."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from qros.config.settings import PROJECT_DIR

from qros.config.settings import Settings, get_settings
from qros.db.session import session_factory, session_scope
from qros.services.settings_store import seed_if_empty
from . import routes_config, routes_control, routes_core, routes_strategy, routes_pipeline


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    token = settings.api_token.get_secret_value()
    if not token.strip() or (settings.env == "prod" and (token == "change-me" or len(token) < 32)):
        raise ValueError("Set QROS_API_TOKEN to a secret of at least 32 characters in production")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.session_factory = session_factory(settings.database_url)
        with session_scope(app.state.session_factory) as db:
            seed_if_empty(db, settings.config_dir)
        yield

    app = FastAPI(title="QROS-PROP", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    from qros.api.routes_library import router as library_router
    app.include_router(library_router)
    for router in (routes_core.router, routes_config.router, routes_control.router, routes_strategy.router, routes_pipeline.router):
        app.include_router(router)

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        logging.getLogger(__name__).exception("API request failed")
        return JSONResponse(status_code=500, content={"detail": "Internal server error; see server logs"})

    frontend_dist = PROJECT_DIR / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/",StaticFiles(directory=str(frontend_dist),html=True),name="dashboard")
    return app
