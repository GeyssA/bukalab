# Protocole de validation

## Ce qui EST validable dans ce design

| Résultat télédétection | Donnée indépendante | Alignement | Limite |
|---|---|---|---|
| Chute NDVI / NDMI estivale | Périmètres EFFIS | spatial + année | EFFIS ≥~30 ha; omission petits feux |
| Type forestier (groupe) | BD Forêt IGN / IFN points | classe | pas de validation biomasse |
| Gradient altitude | MNT / Open-Meteo elev. | spatial | OK |
| Stress hydrique NDMI | IFN dépérissement / observations terrain | rare / décalé | **ne pas prétendre valider NDMI = dépérissement** |

## Ce qui N'EST PAS une validation

- Corréler NDVI avec un autre indice spectral dérivé de Sentinel-2
- Utiliser l'IFN pour "valider" une tendance NDVI pixel sans co-localisation temporelle

## Procédure EFFIS

1. Demander les burnt areas Corse 2017–2025 via le formulaire JRC
2. Intersection avec `forest_grid_1km`
3. Matrice de confusion : événement spectral vs feu cartographié
4. Rapporter précision / rappel — pas seulement des exemples

## Robustesse prévue (scripts)

- Grilles 500 m / 1000 m / 2000 m
- Avec / sans cellules `burned_ever`
- Matching caliper 0.25 / 0.5 / 1.0
- Années 2017–2019 exclues (début S2 L2A plus hétérogène)
