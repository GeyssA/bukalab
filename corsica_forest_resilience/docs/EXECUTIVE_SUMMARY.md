# Résumé exécutif — résultats empiriques inclus

> Rapport complet (méthodologie + figures intégrées) : [`report.md`](report.md)

## Question
Les forêts **comparables** du PNR de Corse présentent-elles des trajectoires Sentinel-2 (NDVI, NDMI) différentes des forêts hors PNR ?

## Données & méthode
- **1 495 paires** matchées (cellules 1 km, ≥60 % BD Forêt)
- Sentinel-2 L2A (Planetary Computer) : médianes estivales JJA 2017–2025, 200 m, masque SCL
- Différences appariées + IC95 % bootstrap (design observationnel, **non causal**)

## Résultats principaux

### 1. Tendances (cœur de la question « trajectoires »)
| Indicateur | Δ moyen (PNR − contrôle) | IC95 % | Conclusion |
|---|---|---|---|
| Pente NDVI | ≈ 0 | inclut 0 | **Pas de différence détectable** |
| Pente NDMI | ≈ 0 | inclut 0 | **Pas de différence détectable** |

Sur le support commun, les forêts PNR et hors PNR **évoluent de façon similaire** en verdure et indice d’humidité estivaux (2017–2025).

### 2. Niveaux moyens
- **NDMI moyen** : PNR légèrement plus élevé (Δ ≈ +0,012 ; IC95 % n’inclut pas 0), mais le test de signes reste non concluant → **signal faible / fragile**.
- **NDVI moyen** : pas de différence claire (IC inclut 0).

### 3. Variabilité / récupération
- CV NDVI : suggestion de variabilité un peu plus faible dans le PNR (IC négatif), à prendre avec prudence.
- Temps de récupération (sous-échantillon) : **pas de différence**.

## Interprétation (prudente)
**Observation :** après contrôle (imparfait) des covariables, on n’observe **pas** de divergence claire des *tendances* estivales PNR vs hors PNR.

**Ce n’est pas :** « le PNR n’a aucun effet » (résidus de matching, pas tout le PNR, pas de design causal).

**Ce n’est pas non plus :** « le PNR protège mieux » — les données ne le montrent pas sur ces métriques.

## Figures
`outputs/figures/fig03_timeseries_matched.png` · `fig05_trends_distribution.png` · `fig10_matched_effects.png`

## What I would do next
1. Matching plus strict / stratifié par altitude pour réduire les SMD résiduels.  
2. DEM 30 m + climat 2017–2025 homogènes.  
3. EFFIS pour les perturbations.  
4. Analyses par type forestier.  
5. Sensibilité résolution 500 m / 2 km.
