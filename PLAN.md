# Build Plan

Ordered milestones. Chemistry first (done) because it de-risks everything.

## MVP (v1)
1. **Chemistry engine + TFP validation tests** ✅ *(done — 47 tests green)*
   - `tfp_data.py` (published TFP tables/constants), `chemistry.py` (targets,
     SLAM, CSI via pypoolchem, dosing, ranges, classification, volume).
2. **Data model + Pool CRUD + Volume Estimator** ✅
   - SQLModel: Pool, TestLog, DoseLog, Chemical (inventory-lite).
   - `POST /api/chem/volume` + estimator UI tool.
3. **Test logging + targets + CSI + dosing endpoints** ✅
   - `POST /api/pools/{id}/tests` (server computes CSI + targets), history query.
   - `POST /api/chem/targets`, `/api/chem/dose`, `/api/chem/csi`.
4. **Dose logging + consumption/cost tracking** *(elevated from v2)* ✅
   - `POST /api/pools/{id}/doses` (decrement inventory, add cost), consumption
     summary over a date range.
5. **Frontend** — Dashboard (status cards + next-action), Log Test, Dosing,
   Volume Estimator, Trends (Recharts), Consumption, Settings. ✅
6. **PWA** — manifest + service worker, installable. ✅ *(offline log queue
   deferred to Phase 2)*
7. **Dockerize + deploy** — multi-stage image (build React → FastAPI serves
   static), compose + `./data` volume, README polish → `/opt/docker/poolmath`.
   ✅ *(image + compose + `.dockerignore` + README built and container
   smoke-tested; deploy to `/opt/docker/poolmath` pending approval)*

## v1.1
- **MQTT → Home Assistant**: publish latest readings + targets to Mosquitto.

## v2 (later)
- SLAM mode (session, FC-loss tracking, 3 exit criteria), OCLT helper.
- Reminders/tasks, richer cost analytics, CSV export/import, multi-pool UI.

## Notes
- All chemistry stays in `chemistry.py` (API layer stays dumb, math testable).
- Color language: below-min = red, in-range = green, above-target-but-safe
  (FC up to SLAM) = neutral/blue, not red.
