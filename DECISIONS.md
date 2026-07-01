# Decisions

Resolved decisions for this build (spec §10 and beyond). Newest context wins.

## Product / scope
- **Pool profile:** single plaster pool, chlorine source = liquid (tablets
  available for temporary use), no salt, borates off by default.
- **Volume:** entered manually; a **Pool Volume Estimator** tool computes
  gallons from shape + dimensions and populates the field.
- **Goals:** replace paid PoolMath; **track chemical consumption/cost**;
  **Home Assistant** integration; **shareable** so others can self-host.
- **Multi-pool:** single pool for the UI; schema is multi-pool-ready.
- **Consumption tracking is elevated into the MVP** (spec had it in v2) because
  it's a primary goal — log doses, track quantity + cost over time.
- **Units:** US customary only. No metric toggle (users convert themselves).

## Chemistry engine
- **Hybrid, TFP-first.** `pypoolchem` (pinned `>=0.1.1,<0.2`) is used only for
  **CSI / equilibrium math**, where it matches TFP. **FC/CYA targets, SLAM,
  ideal ranges, and all dosing** are computed from TFP's published data
  (`docs/tfp-reference.md` → `backend/poolmath/tfp_data.py`).
- **Why:** validation of pypoolchem v0.1.1 against TFP found:

  | Chemistry | pypoolchem | TFP expected | Use |
  |---|---|---|---|
  | CSI | −0.11 (balanced sample) | ~−0.2…0.0 | ✅ pypoolchem |
  | Baking soda / CYA dose | matches | matches | own (TFP) |
  | FC target factor | ~2 ppm low vs chart | published chart | own (TFP) |
  | Chlorine dose | ~25% low | ~10.7 fl oz/ppm 12.5% | own (TFP) |
  | Muriatic acid | ~100× low (broken) | ~20 fl oz for 0.5 pH | own (TFP) |

- Muriatic acid dosing is an **estimate** (nonlinear/TA-buffered); the app tells
  the user to lower toward pH 7.2 and retest, per TFP.
- Constants are traceable to `docs/tfp-reference.md`; 47 unit tests assert the
  published tables so a pypoolchem bump can't silently change a number.

## Auth / access
- **No auth by default** — open on LAN/WireGuard. Optional `POOLMATH_AUTH_TOKEN`
  env: unset = open, set = required (lets other self-hosters lock their instance).
- Single-user. Multi-pool ≠ multi-user.

## Ops
- **Repo:** new repo, **public + MIT** (shareable). Local git only for now;
  push to GitHub later (gh not installed on d3050).
- **Dev:** Python 3.13 via `uv` (box has 3.12); Docker build uses `python:3.13`.
- **Deploy:** `/opt/docker/poolmath` on d3050, Portainer stack, bind-mounted
  `./data` for SQLite (ZFS-snapshotted). No public exposure.
- **v1.1:** MQTT → Home Assistant (Mosquitto already runs at `/opt/docker/mqtt`).

## Container (milestone 7)
- **Multi-stage image.** Stage 1 `node:22-slim` builds the PWA (`npm ci` +
  `vite build`); stage 2 `python:3.13-slim` runs it. Keeps node out of the
  final image (~249 MB).
- **`uv` in the build**, not pip: `uv pip install --system` for parity with the
  dev workflow. Runtime deps only (no `[dev]` extras) — no pytest/httpx shipped.
- **FastAPI serves the static bundle.** `POOLMATH_STATIC_DIR=/app/frontend/dist`
  baked into the image; no separate web server / nginx.
- **Non-root, uid/gid 1000.** Matches the typical host user so the `./data`
  bind mount is writable without fiddling; documented `chown 1000` for hosts
  where it isn't. App owns `/data`.
- **Port 8790** (matches dev). Compose publishes `8790:8790` on the LAN;
  documented `127.0.0.1:8790:8790` for reverse-proxy fronting. No public expose.
- **Healthcheck uses `python -c urllib`**, not curl — curl isn't in the slim
  image and adding it just for a healthcheck isn't worth the bytes.
- **Zero-config.** `docker compose up` works with no `.env`: `TZ` defaults,
  `POOLMATH_DB_PATH=/data/poolmath.db`, auth unset (open on LAN), `MQTT_*`
  left commented for the later phase.
- **No `VOLUME` directive** in the Dockerfile — persistence is the compose bind
  mount only, to avoid stray anonymous volumes on `docker run`.
