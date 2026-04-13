"""FastAPI web application for Pubmedsoso."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pubmedsoso.web.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Pubmedsoso",
        description="PubMed literature crawler web interface",
        version="2.0.0",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router, prefix="/api")

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
