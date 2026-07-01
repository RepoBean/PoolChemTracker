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
