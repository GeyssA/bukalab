# Catalogue des données

Date d'accès documentée : **2026-09-24**.

## 1. Parc naturel régional de Corse

| Champ | Valeur |
|---|---|
| Nom | Parcs Naturels Régionaux de France au 07 novembre 2024 — 59 PNR |
| Producteur | Fédération des PNR de France (GéoPNR, base BD TOPO IGN) |
| Remarque | Diffusion indicative data.gouv.fr ; **source officielle de vérification : INPN** |
| URL | https://www.data.gouv.fr/datasets/parcs-naturels-regionaux-de-france-au-07-novembre-2024-59-pnr |
| Période | Géométrie au 07/11/2024 |
| Résolution | Vecteur (limites administratives / projet de parc) |
| Projection fichier | EPSG:2154 (GeoJSON fourni) |
| Format | GeoJSON / GPKG / SHP / KML |
| Licence | Licence Ouverte |
| Variable | `NOM_SITE = Corse` |
| Limites | Le PNR n’est pas une réserve intégrale ; usages humains présents |

Fichier projet : `data/processed/pnr_corse.gpkg`

## 2. BD Forêt® v2 (IGN)

| Champ | Valeur |
|---|---|
| Producteur | IGN |
| URL | https://data.geopf.fr/telechargement/resource/BDFORET |
| Départements | D02A (2017-05-10), D02B (2016-02-16) |
| Résolution | Polygones ≥ 0,5 ha |
| Projection | Lambert-93 (EPSG:2154) |
| Format | Shapefile (.7z) |
| Licence | Licence Ouverte Etalab 2.0 |
| Variables | Codes / libellés de formation végétale → `forest_type_group` |
| Limites | Millésimes différents 2A/2B ; masque **statique** sur 2017–2025 |

## 3. Sentinel-2 L2A

| Champ | Valeur |
|---|---|
| Producteur | ESA / Copernicus |
| Accès | Microsoft Planetary Computer STAC ; export Google Earth Engine |
| URL PC | https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a |
| Période cible | 2017 → dernière année complète |
| Résolution | 10–20 m (indices à 20 m pour NDMI) |
| Temporel | Médianes saisonnières (printemps, été) |
| Projection | UTM / reprojeté en analyse |
| Licence | Copernicus open access |
| Variables | NDVI, NDMI (+ EVI optionnel) |
| Limites | Nuages ; début de série L2A ; maquis vs forêt fermée |

Script : `src/gee_export_s2_seasonal.js`

## 4. Sentinel-1 (optionnel)

| Champ | Valeur |
|---|---|
| Justification | Continuité sous nuages ; signal structurel (VH/VV) |
| Non-usage | Ne pas interpréter VV/VH seuls comme stress hydrique |

## 5. Climat (ERA5-Land via Open-Meteo)

| Champ | Valeur |
|---|---|
| Producteur | ECMWF / Open-Meteo |
| URL | https://open-meteo.com/en/docs/historical-weather-api |
| Variables | Température estivale moyenne ; précipitations annuelles moyennes |
| Résolution | ~9 km (ERA5-Land) agrégé au centroïde de cellule |
| Licence | Open-Meteo + Copernicus climate |
| Limites | Pas un réseau Météo-France station ; lissage spatial |

## 6. Altitude

| Champ | Valeur |
|---|---|
| Source retenue (pipeline actuel) | Open-Meteo Elevation API (proxy rapide) |
| Alternative recommandée | Copernicus DEM GLO-30 via Planetary Computer |
| Limites du proxy | Pente/exposition estimées à l’échelle 1 km |

## 7. Incendies (EFFIS)

| Champ | Valeur |
|---|---|
| Producteur | EC JRC — Copernicus EMS EFFIS |
| URL | https://forest-fire.emergency.copernicus.eu/ |
| Accès historique | Formulaire de demande de données |
| Limites | Feux ≲ 30 ha souvent omis ; délai de livraison hors pipeline auto |

Dépôt local attendu : `data/raw/fire/`

## 8. Inventaire forestier national (IFN / IGN)

| Champ | Valeur |
|---|---|
| Usage prévu | Caractérisation peuplements / validation **de classes de type**, pas des tendances NDVI |
| Accès | https://inventaire-forestier.ign.fr / data.gouv |
| Limite éthique méthodo | Ne pas prétendre valider un indicateur satellitaire avec une variable qui ne mesure pas la même chose |
