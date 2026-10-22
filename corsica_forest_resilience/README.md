# Forest Resilience in Corsica

**Question.** Do forests inside the *Parc naturel régional de Corse* (PNR) show different ecological trajectories—productivity, moisture stress, disturbance, recovery, temporal stability, climate-anomaly response—than **comparable** forests outside the PNR?

This is **not** “are PNR forests better?”. The project is an observational Earth Observation study with explicit bias control (matching), documented limits, and no fabricated EO results.

---

## Scientific question

| Population A | Population B |
|---|---|
| Forest analysis cells (≥60% forest) **inside** PNR | Forest cells **outside** PNR, matched on covariates |

**Outcomes (Sentinel-2 L2A, seasonal medians):** NDVI & NDMI trends, anomalies, interannual CV, recovery time after spectral drops; optional Sentinel-1 structure metrics.

**Confounders controlled (matching):** elevation, slope, aspect, summer temperature, annual precipitation, forest-type group (BD Forêt), distance to coast, burn flag (EFFIS when available).

**Causal stance:** associations conditional on observed covariates — **not** automatic causal proof that “PNR protection causes” differences.

---

## Data

| Dataset | Producer | Role | Access |
|---|---|---|---|
| PNR boundaries (07/11/2024) | FPNRF / GéoPNR (BD TOPO); indicative on data.gouv; official INPN | Treatment mask | [data.gouv.fr](https://www.data.gouv.fr/datasets/parcs-naturels-regionaux-de-france-au-07-novembre-2024-59-pnr) |
| BD Forêt® v2 (2A, 2B) | IGN | Forest mask + type | [data.geopf.fr BDFORET](https://data.geopf.fr/telechargement/resource/BDFORET) |
| Sentinel-2 L2A | ESA / Copernicus | NDVI, NDMI, EVI | Planetary Computer STAC + **GEE export script** |
| Sentinel-1 RTC (optional) | ESA | Structure / VH-VV | Planetary Computer |
| ERA5-Land climate | ECMWF via Open-Meteo | Covariates & drought context | Open-Meteo Archive API |
| Elevation | Open-Meteo elevation API (proxy) / Copernicus DEM | Topography | API / PC |
| Burned areas | EFFIS / Copernicus EMS | Fire history | [data request](https://forest-fire.emergency.copernicus.eu/apps/data.request.form/) |

Full catalogue: `docs/data_catalog.md`.

---

## Methodology (summary)

1. **Unit of analysis:** 1 km grid cells with ≥60% BD Forêt cover (robustness: 500 m / 2 km).
2. **EO:** Seasonal medians (spring, summer) 2017–last complete year; SCL clear-sky mask; Mediterranean summer window for drought stress.
3. **Trajectories:** slope, anomaly vs early baseline, CV, recovery years after spectral drop.
4. **Matching:** 1:1 nearest neighbour on standardized covariates (Mahalanobis-like); report SMD balance.
5. **Inference:** paired Wilcoxon + bootstrap 95% CI on matched differences; naive means shown for contrast.
6. **Validation:** EFFIS overlay protocol (`docs/validation_protocol.md`) — no fake IFN “validation” of NDVI trends.

---

## Workflow

```text
py -m pip install -r requirements.txt
# 1. Place BD Forêt .7z for D02A/D02B in data/raw/foret/ and extract (7-Zip)
py run_pipeline.py
# 2. Upload forest cell centroids to Google Earth Engine
# 3. Run src/gee_export_s2_seasonal.js → save CSV to data/processed/
py -m src.timeseries
py -m src.matching
```

Config: `config.yaml`.

---

## Results (exécutés — 2026-09-24)

**Rapport PDF publiable (figures intégrées + glossaire) :**  
[`outputs/figures/Rapport_PNR_Corse_Trajectoires_Forestieres.pdf`](outputs/figures/Rapport_PNR_Corse_Trajectoires_Forestieres.pdf)

Régénérer : `py -m src.publication_report`

Figures haute résolution : `outputs/figures/pub_fig*.png`  
Rapport Markdown : [`docs/report.md`](docs/report.md) · Résumé : [`docs/EXECUTIVE_SUMMARY.md`](docs/EXECUTIVE_SUMMARY.md)

Verdict empirique : pas de différence détectable des *tendances* estivales NDVI/NDMI PNR vs contrôles matchés ; signal NDMI moyen faible/fragile. Design observationnel, non causal.

---

## Limitations

- PNR is not a randomized treatment; residual confounding possible (management history, soils, unmeasured structure).
- Open-Meteo elevation/climate at cell centroids ≠ 30 m DEM / dense weather network.
- EFFIS omits small fires; spectral drops ≠ fires.
- BD Forêt millésime differs 2A/2B; static forest mask over 2017–2025.
- Without local `rasterio` COG sampling, S2 depends on GEE export (user account).

---

## Reproducibility

- No secrets in repo. GEE needs a Google account; Planetary Computer STAC is open.
- Large rasters / BD Forêt binaries are gitignored; download scripts + URLs documented.
- Someone else can clone → install → download → run → regenerate figures.

---

## Licence

Code: MIT (unless otherwise noted).  
Data: respective open licences (Etalab / Copernicus / FPNRF Licence Ouverte). Always cite producers.

---

## References (selected, real)

See `docs/references.md` and `docs/report.md`.
