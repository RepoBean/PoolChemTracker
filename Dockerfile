# syntax=docker/dockerfile:1

# ---- Stage 1: build the React PWA -------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /app/frontend

# Install deps against the lockfile first so this layer caches across src edits.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Build the static bundle -> /app/frontend/dist
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime (FastAPI serves the built PWA) -----------------
FROM python:3.13-slim AS runtime

# uv gives us install parity with the dev workflow (astral-sh/uv).
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    POOLMATH_DB_PATH=/data/poolmath.db \
    POOLMATH_STATIC_DIR=/app/frontend/dist

WORKDIR /app

# Install the backend (runtime deps only, no dev extras) into the system
# interpreter. This builds the poolmath wheel from backend/pyproject.toml.
COPY backend/ ./backend/
RUN uv pip install --system --no-cache ./backend

# Bring in the built frontend from stage 1; POOLMATH_STATIC_DIR points here.
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Non-root runtime user that owns /data so SQLite can be created on a fresh
# bind mount. uid/gid 1000 matches the typical host user for bind-mount parity.
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --home-dir /app --no-create-home app \
    && mkdir -p /data \
    && chown -R app:app /app /data
USER app

EXPOSE 8790

CMD ["uvicorn", "poolmath.main:app", "--host", "0.0.0.0", "--port", "8790"]
