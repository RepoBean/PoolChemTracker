# TFP Reference Data (source of truth)

This file captures TroubleFreePool's published guidance verbatim-enough to be the
**source of truth** for targets, chemical choices, dosing, and wait times. The
chemistry code (`backend/poolmath/tfp_data.py`) encodes these numbers and cites
this file. Provenance: TFP blog articles supplied by the pool owner.

Sources:
- ABCs of Pool Water Chemistry — https://www.troublefreepool.com/blog/2018/12/12/abcs-of-pool-water-chemistry/
- FC & CYA Relationship Explained — https://www.troublefreepool.com/blog/2019/01/18/free-chlorine-and-cyanuric-acid-relationship-explained/
- Recommended Pool Chemicals — https://www.troublefreepool.com/blog/2019/01/18/recommended-pool-chemicals/
- How Long to Wait Between Adding Chemicals — https://www.troublefreepool.com/blog/2019/12/02/how-long-to-wait-between-adding-pool-chemicals/
- Basic Pool Care Schedule — https://www.troublefreepool.com/blog/2019/01/18/basic-pool-care-schedule/

---

## FC / CYA relationship (TFP published chart)

**Liquid chlorine (non-SWG)** — ppm

| CYA | Min FC | Target FC |
|----:|:------:|:---------:|
| 20  | 2 | 3–5 |
| 30  | 2 | 4–6 |
| 40  | 3 | 5–7 |
| 50  | 4 | 6–8 |
| 60  | 5 | 7–9 |
| 70  | 5 | 8–10 |
| 80  | 6 | 9–11 |
| 90  | 7 | 10–12 |
| 100 | 8 | 11–13 |

**Salt water chlorine (SWG)** — ppm

| CYA | Min FC | Target FC |
|----:|:------:|:---------:|
| 20  | 2 | 3–5 |
| 30  | 2 | 3–6 |
| 40  | 2 | 3–7 |
| 50  | 2 | 3–8 |
| 60  | 3 | 4–9 |
| 70  | 3 | 5–10 |
| 80  | 4 | 6–11 |
| 90  | 4 | 6–12 |
| 100 | 5 | 7–13 |

**SLAM level** (shock) — ppm

| CYA | SLAM |
|----:|:----:|
| 20 | 10 |
| 30 | 12 |
| 40 | 16 |
| 50 | 20 |
| 60 | 24 |
| 70 | 28 |
| 80 | 31 |
| 90 | 35 |
| 100 | 39 |

Notes:
- Recommended CYA: **30–60 for liquid chlorine**, **60–90 for SWG**. High-UV/high-loss
  liquid-chlorine pools may run ~60 to protect chlorine.
- **Never** let FC fall below Min FC for your CYA (algae risk → SLAM).
- FC anywhere **up to and including SLAM level is safe** to swim (CYA buffers active
  chlorine). Even at SLAM FC, active chlorine ≈ 55% of a CYA-0 public pool at 1 FC.
- Mustard/yellow-algae SLAM ≈ **0.6 × CYA**.
- Indoor pools target CYA 20–30.
- CYA degrades ~5–10 ppm/month (summer); retest every 1–2 weeks.

## Recommended target ranges (plaster pool, liquid chlorine)

| Parameter | Acceptable min | Ideal | Acceptable max |
|---|---|---|---|
| pH | 7.2 | 7.6–7.8 | 8.0 |
| TA (Total Alkalinity) | 50 | 50–90 (ideal 60–80) | 90 |
| CH (Calcium Hardness, plaster) | 250 | 350–550 | 650 |
| CYA (liquid chlorine) | 30 | 40–50 | 60 |
| CC (Combined Chlorine) | — | 0 | 0.5 (>0.5 → investigate/SLAM) |
| CSI | −0.6 | −0.3…+0.3 | +0.6 |

- **Managing pH matters far more than TA.** High TA just makes pH rise faster; it
  won't harm the pool. Lowering pH with muriatic acid also lowers TA.
- Plaster: CH of 250 will protect the pool. Gas heaters want ≥200 CH.
- Cold water: allow pH to drift to 7.8–8.0 to reduce etching risk (CSI).
- Salt (non-SWG, optional comfort): ~1500–2000 ppm. SWG: ~3000 (per manufacturer).
- Borates (optional): 30–50 ppm.
- Order of importance: **FC (daily, by CYA) → CYA → pH → CH → TA → salt/borates → skip phosphates.**

## Recommended chemicals

| Adjust | Use | Notes |
|---|---|---|
| Raise FC | Liquid chlorine (6% / 10% / 12.5%) | Same as unscented bleach. Pour in a thin stream in front of a return; pump ≥30 min. |
| Lower pH / lower TA | Muriatic acid (31.45% = 20°Bé, or 15.725% = 10°Bé) | Pump ≥30 min after. |
| Raise pH | 20 Mule Team Borax or aeration | Only if pH < 7.0 and TA ≥ 50. Not soda ash (raises TA). |
| Raise TA | Baking soda | Only if TA < 50. |
| Raise CH | Calcium chloride (anhydrous) or calcium chloride dihydrate | Spread over deep end; brush in. |
| Raise CYA | Granular stabilizer (sock method) | Pump 24 h; no backwash 1 week; dose as if already present. |
| Raise salt | Water softener/pool salt, 99.4%+ pure, no additives | Pump 24 h; SWG off 24 h. |
| Raise borates | Granular boric acid | — |
| Lower FC | Wait (sunlight/organics) | — |
| Lower CYA / CH / salt / borates | Water exchange or RO | No chemical fix. |

**Avoid:** dry acid (sulfates damage plaster/metal), MPS non-chlorine shock, metal
algaecides/ionizers, ammonia, floc, clarifiers, UV (outdoor), CYA reducers, ozone,
and **routine** trichlor/dichlor (they continuously raise CYA). Trichlor is OK
temporarily (e.g., vacation floater) if CYA is well managed.

## Wait times & safety when adding chemicals

- General: ~**10 minutes** between chemicals (also enough to mix). Can typically swim
  ~10 min after adding. Pump on high + pour in front of return = mixes fast. Brush after.
- Liquid chlorine: pump ≥30 min after. Muriatic acid: pump ≥30 min after.
- Salt: pump 24 h; SWG off 24 h. CYA sock: pump 24 h, no backwash for a week.
- **Never mix:**
  - Trichlor + Cal-Hypo (can explode).
  - Muriatic acid + chlorine at the same time (toxic gas).
- After **Cal-Hypo**, wait **24 h** before adding anything that alters pH (avoids calcium clouding).
- Rule of thumb: never mix pool chemicals directly with each other.

## Basic care schedule / order

- Test **FC daily** for manually dosed (liquid chlorine) pools; every few days for SWG/automated.
- Maintain FC by CYA (FC/CYA chart). Track **CYA every 1–2 weeks**.
- Keep pH 7.2–8.0 (adjust toward 7.6–7.8). Monitor CH; maintain TA to stabilize pH.
- Outdoor pools with FC maintained: ignore phosphates.
