from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db
from .jobs.router import batches_router, reports_router, router as jobs_router
from .storage import ensure_storage_dirs


def create_app() -> FastAPI:
    settings = get_settings()
    ensure_storage_dirs(settings.storage_root)
    init_db()
    app = FastAPI(title="Ninebot Upscale API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": settings.service_name}

    app.include_router(jobs_router)
    app.include_router(batches_router)
    app.include_router(reports_router)
    if settings.storage_root.exists():
        app.mount("/storage", StaticFiles(directory=settings.storage_root), name="storage")
    return app


app = create_app()
