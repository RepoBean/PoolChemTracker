"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from . import __version__
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
