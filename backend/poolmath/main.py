"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, config
from .api import chem, chemicals, doses, pools
from .api import tests as tests_api
from .auth import require_auth
from .db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PoolMath", version=__version__, lifespan=lifespan)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}


# All data/chemistry routes sit behind the optional shared-token guard
# (no-op unless POOLMATH_AUTH_TOKEN is set).
_guard = [Depends(require_auth)]
app.include_router(chem.router, dependencies=_guard)
app.include_router(pools.router, dependencies=_guard)
app.include_router(tests_api.router, dependencies=_guard)
app.include_router(doses.router, dependencies=_guard)
app.include_router(chemicals.router, dependencies=_guard)


# Serve the built PWA (if present). Registered last so /api routes win. Any
# non-file path falls back to index.html for client-side routing.
_dist = Path(config.STATIC_DIR)
if (_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = _dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
