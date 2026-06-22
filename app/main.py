"""Punto de entrada FastAPI."""
import os
import sys
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from app.api import (
    routes_actions,
    routes_analyze,
    routes_detections,
    routes_entities,
    routes_export,
    routes_upload,
)
from app.config import APP_VERSION, FRONTEND_DIR, HOST, PORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Anonimizador Judicial",
    description="Anonimización local de documentos judiciales — uso personal",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.include_router(routes_upload.router)
app.include_router(routes_analyze.router)
app.include_router(routes_actions.router)
app.include_router(routes_detections.router)
app.include_router(routes_entities.router)
app.include_router(routes_export.router)

class NoCacheStaticFiles(StarletteStaticFiles):
    async def get_response(self, path: str, scope):  # type: ignore[override]
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


if FRONTEND_DIR.exists():
    app.mount("/static", NoCacheStaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(
            index_path,
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
    return {"message": "Anonimizador Judicial API", "docs": "/docs"}


@app.get("/health")
async def health():
    from app.detection.nlp_status import get_nlp_layers_status

    return {
        "status": "ok",
        "host": HOST,
        "port": PORT,
        "app_version": APP_VERSION,
        "frontend_dir": str(FRONTEND_DIR),
        "nlp_layers": get_nlp_layers_status(),
    }


def run_server(open_browser: bool = True, cache_bust: bool = True):
    import time
    import uvicorn

    # En builds "windowed" (PyInstaller), stdout/stderr pueden ser None.
    # Uvicorn intenta acceder a .isatty() y falla si el stream es None.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    url = f"http://{HOST}:{PORT}"
    if cache_bust:
        url += f"?_{int(time.time())}"
    if open_browser:
        webbrowser.open(url)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    run_server()
