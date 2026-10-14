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

## Quick (categorical) tests
- **OTO step set is TFP's published 5-drop result set**, verbatim:
  `none, 0.5, 1, 2, 3, 5, 10, 15, 20, 30, 40, 50, 100` (`FC_COLOR_STEPS` in
  `models.py`). `none` = no color change = FC < 0.5.
- **Numeric `fc` is the step's lower bound** ("2" → 2.0, "none" → 0.0) so
  quick readings plot on Trends and hit the same min-FC checks. Both fields are
  stored (`fc_color` keeps the raw swatch) so the UI can say "FC ≈ 2 (quick)"
  vs a precise reading. If a precise `fc` *and* `fc_color` are both sent, the
  precise number wins.
- **Quick pH chips (7.2–8.4, step 0.2) also derive numeric `ph`** — otherwise
  a quick pH reading would never appear on the pH line. 0.2 resolution is fine
  for trend purposes; the point is still approx-marked.
- **`is_approx`** is a pydantic `computed_field` on `TestLog` (serialized in
  API responses, *not* a DB column): true when `test_type == "quick"` or
  `fc_color` is set.
- **No-CYA quick-test recommendation:** quick tests normally have no CYA, so
  there are no CYA-derived targets. TFP's universal "keep FC ≥ 1.0" rule
  (`tfp_data.MIN_FC_NO_CYA`, new constant — existing table values untouched)
  is the fallback: a quick test with FC < 1.0 gets the danger
  "FC below minimum, add ~X of 12.5%" dose; CH/TA/temp still gate only CSI.
- **Existing-DB migration:** SQLite `create_all` never adds columns to existing
  tables, so `db.init_db()` runs a tiny startup guard (`_COLUMN_MIGRATIONS`):
  `PRAGMA table_info` per (table, column) and `ALTER TABLE … ADD COLUMN` when
  missing. A test simulates a pre-quick-test DB and exercises the path.
  Resetting the DB is *not* required.

## Receipt scanning (local VLM)
- **Target is Ollama's `/api/chat`**, image base64 in `messages[0].images`,
  `format` = JSON schema for the item list. Why Ollama: d3050 already runs
  Docker, one `ollama pull` away, zero new infra, and it's the most common
  self-hosted vision runtime. `POOLMATH_VLM_URL` is env-gated and **off by
  default**; with it unset the scan endpoint 503s, `/api/ai/status` reports
  `{enabled: false}`, and the frontend hides the button — the rest of the app
  is byte-for-byte unchanged.
- **HTTP client is stdlib `urllib`** — `httpx` is a *dev-only* dependency
  (pytest/TestClient) and adding it at runtime was avoided. `python-multipart`
  *is* a new regular dependency: FastAPI's form/file handling requires it and
  there is no stdlib workaround (small, FastAPI-endorsed).
- **Two-phase, human-in-the-loop:** `POST …/receipts` returns a *draft* and
  writes nothing; `POST …/receipts/confirm` (multipart: `items` JSON form
  field + `received_at` + optional re-uploaded image) merges into `Chemical`
  and persists a `ReceiptLog`. The image is re-uploaded on confirm rather than
  cached server-side — stateless parse, and **discarded scans store nothing**.
- **Image storage policy:** only on confirm, under `<POOLMATH_DB_PATH
dir>/receipts/<utc-timestamp>.<ext>` (i.e. inside the bind-mounted, ZFS-
  snapshotted volume alongside the DB). Bad extension/oversize at confirm =
  skip storage, still log the receipt.
- **Confirm-merge rules:** name match is case-insensitive and
  whitespace-collapsed; if the item carries a strength, it must match too
  (12.5% ≠ 6%). On match: `qty_on_hand += package_qty` and
  `cost_per_unit = price / package_qty` (in the receipt's unit — the review
  form is where a unit mismatch gets fixed; the backend does not silently
  convert). No match → create the `Chemical` with the item's unit.
- **Unit normalization** (`units.normalize_unit`): free-text words → the app's
  unit set; bare "oz" is ambiguous — **oz_wt for dry/powder chemicals
  (name heuristics: hypo, calcium/chloride, baking soda, stabilizer, cya,
  salt, borax, …), fl_oz for liquids**. "chlor" alone is deliberately *not*
  a dry hint (liquid pool chlorine). Unknown words pass through untouched.
- **Dropping non-chemicals is the model's job** (prompt-instructed) with the
  human review form as backstop; the code only drops nameless lines. Receipt
  total vs item-sum mismatch is surfaced in the UI as a sanity hint, not an
  error — receipts include tax.

## Consumption aggregation
- **One row per chemical name, in one base unit.** `/consumption` groups by
  case/whitespace-normalized name (so "acid"/"Acid"/"ACID" merge) and converts
  every dose amount into a single base unit per chemical:
  **the matching inventory item's unit if one exists, else the unit of the
  highest-cost dose in the window** (the most representative purchase unit).
  Cost summing is unchanged; doses in an incompatible dimension (a "gallon"
  and a "pound" under one name) are counted but not summed — silently mixing
  volume + weight would fabricate numbers.
- **`POST /doses` with `chemical_id`** now writes the inventory item's
  canonical `name`/`strength` onto the dose record, so free-text variants stop
  fragmenting totals. Free-text doses without `chemical_id` keep what was
  typed (backwards compatible).
