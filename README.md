# PoolMath (self-hosted)

A self-hostable pool water-chemistry log and calculator that follows
[TroubleFreePool](https://www.troublefreepool.com/)'s **TFP methodology** — FC
driven by CYA, CSI (not LSI), liquid-chlorine bias. Log test results, get
FC/CYA targets + SLAM levels, calculate chemical doses, track CSI and chemical
consumption, and see trends over time. Runs entirely on your own hardware.

> Not affiliated with TroubleFreePool. Chemistry follows TFP's published
> guidance (see [`docs/tfp-reference.md`](docs/tfp-reference.md)). Always
> validate a dose against your own test kit before trusting it poolside.

## Why this exists

Replaces the paid PoolMath app for personal/family use, adds better **chemical
consumption/cost tracking**, and can publish to **Home Assistant** (MQTT).
Self-hosted, single Docker stack, no cloud, no account required.

## Chemistry engine

The chemistry is the hard part, so it's isolated in
[`backend/poolmath/chemistry.py`](backend/poolmath/chemistry.py) and unit-tested
against TFP's published tables.

- **CSI** and equilibrium math → delegated to [`pypoolchem`](https://pypi.org/project/pypoolchem/) (validated to match TFP).
- **FC/CYA targets, SLAM, ideal ranges, and all dosing** → computed from TFP's
  published data in [`backend/poolmath/tfp_data.py`](backend/poolmath/tfp_data.py).

Why the split: `pypoolchem` v0.1.1 nails CSI but its dosing diverges from TFP
(chlorine ~25% low; muriatic acid ~100× off), so those come straight from TFP.
See [`DECISIONS.md`](DECISIONS.md).

## Stack

Python 3.13 + FastAPI + SQLModel/SQLite (backend) · React + Vite + Tailwind PWA
(frontend) · single multi-stage Docker image.

## Development

Requires [`uv`](https://docs.astral.sh/uv/) (gets Python 3.13 automatically).

```bash
uv venv --python 3.13
uv pip install -e "backend[dev]"
uv run pytest backend/tests -q       # 47 chemistry tests
```

## Deployment (target: d3050 `/opt/docker/poolmath`)

One container + a bind-mounted `./data` for the SQLite file (covered by ZFS
snapshots). Front with your existing reverse proxy; expose only over LAN/WireGuard.

Config via env: `POOLMATH_DB_PATH`, `TZ`, optional `POOLMATH_AUTH_TOKEN`
(unset = open on LAN), optional `MQTT_*` for Home Assistant.

## Status

- [x] Chemistry engine + TFP validation tests
- [ ] Pool CRUD + volume estimator
- [ ] Test logging + targets + dosing endpoints
- [ ] Dose logging + consumption tracking
- [ ] Frontend (dashboard, log, dosing, trends)
- [ ] PWA + Docker deploy
- [ ] MQTT → Home Assistant

See [`PLAN.md`](PLAN.md).

## License

MIT — see [`LICENSE`](LICENSE).
