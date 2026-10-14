# PoolMath (self-hosted)

A self-hostable pool water-chemistry log and calculator that follows
[TroubleFreePool](https://www.troublefreepool.com/)'s **TFP methodology** — FC
driven by CYA, CSI (not LSI), liquid-chlorine bias. Log test results, get
FC/CYA targets + SLAM levels, calculate chemical doses, track CSI and chemical
consumption, and see trends over time. Runs entirely on your own hardware.

> Not affiliated with TroubleFreePool. Chemistry follows TFP's published
> guidance (see [`docs/tfp-reference.md`](docs/tfp-reference.md)). Always
> validate a dose against your own test kit before trusting it poolside.

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

## Deploy (Docker)

One container: a multi-stage image builds the React PWA and FastAPI serves the
built bundle plus the `/api`. State is a single SQLite file on a bind-mounted
`./data` (covered by ZFS snapshots on d3050). LAN only — front with your
existing reverse proxy; do not expose to the internet.

```bash
git clone https://github.com/RepoBean/PoolChemTracker.git poolmath
cd poolmath
docker compose up -d --build      # zero-config: no .env required
curl http://localhost:8790/api/health   # {"status":"ok",...}
```

That's it — open `http://<host>:8790/`. The SQLite DB is created on first run at
`./data/poolmath.db`.

**Data volume.** `./data` is bind-mounted to `/data` in the container. The app
runs as **uid 1000**, so on a host where that dir isn't already owned by 1000,
make it writable once:

```bash
mkdir -p data && sudo chown -R 1000:1000 data
```

**Config (env, all optional).** Defaults work with nothing set; override in a
`.env` next to the compose file (see [`.env.example`](.env.example)):

| Var | Default | Purpose |
|---|---|---|
| `TZ` | `America/New_York` | Timezone for log timestamps |
| `POOLMATH_DB_PATH` | `/data/poolmath.db` | SQLite location (inside the volume) |
| `POOLMATH_AUTH_TOKEN` | *unset* | Set to require a shared token; unset = open on LAN |
| `MQTT_*` | *unset* | Home Assistant publish (wired up in a later phase) |

**Reverse proxy.** `docker-compose.yml` publishes `8790:8790` on the LAN. To
keep it off other interfaces and front it with a proxy on the same host, switch
the port mapping to `127.0.0.1:8790:8790` (commented example in the file).

**Portainer (d3050).** Target `/opt/docker/poolmath`. Deploy as a stack from
this repo (or the web editor), keeping the `./data` bind mount so the DB is
ZFS-snapshotted with the rest of `/opt/docker`.

## Status

- [x] Chemistry engine + TFP validation tests
- [x] Pool CRUD + volume estimator
- [x] Test logging + targets + dosing endpoints
- [x] Dose logging + consumption tracking
- [x] Frontend (dashboard, log, dosing, trends)
- [x] PWA + Docker image (multi-stage, compose stack)
- [ ] MQTT → Home Assistant

See [`PLAN.md`](PLAN.md).

## License

MIT — see [`LICENSE`](LICENSE).
