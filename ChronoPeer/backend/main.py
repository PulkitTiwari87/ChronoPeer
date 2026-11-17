"""Application factory.

Run locally:   uvicorn backend.main:create_app --factory --port 8000
The same process serves the JSON API under /api and the built React app (frontend/dist) at /.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from .api import cases, evidence, inferences, reports, revisions, reviews, timeline
from .config import Settings, load_settings
from .database import make_session_factory
from .services import DomainError


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    session_factory, engine = make_session_factory(settings.db_path)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(_app):
        yield
        engine.dispose()

    app = FastAPI(title="ChronoPeer", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = session_factory

    for module in (cases, evidence, timeline, inferences, reviews, revisions, reports):
        app.include_router(module.router)

    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, exc: DomainError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_request: Request, _exc: IntegrityError):
        return JSONResponse({"detail": "That change conflicts with existing data"}, status_code=409)

    if settings.seed_demo:
        from .services.seed_demo import seed_if_empty

        seed_if_empty(session_factory, settings)

    if settings.frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="ui")
    return app
