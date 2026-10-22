# Figures climat France — version publication

## Données
- **Source :** ERA5-Land (ECMWF), accès Open-Meteo Archive API  
- **Variables :** température moyenne annuelle (`temperature_2m_mean`), précipitations annuelles (`precipitation_sum`)  
- **Maillage source :** ~2 865 points terre (pas ~0,15°)

## Classification (stable entre années)
Seuils **figés** (quartiles 2025 arrondis) — ne pas recalculer par année :

| | Classe 1 | Classe 2 | Classe 3 | Classe 4 |
|---|---|---|---|---|
| T° (°C) | ≤ 11,2 | 11,2 – 12,0 | 12,0 – 13,1 | > 13,1 |
| P (mm) | ≤ 780 | 780 – 900 | 900 – 1 040 | > 1 040 |

## Traitement cartographique
1. Interpolation IDW (puissance 2, 16 voisins)  
2. Lissage gaussien du champ continu  
3. Classification 4×4 sur le champ lissé  
4. Panneaux (a)–(b) : champs continus + isolignes aux seuils  

## Fichiers

| Fichier | Usage |
|---------|--------|
| `france_climat_poster_YYYY.pdf` / `.png` | **Poster A3 paysage** (~4960×3500 px) — impression, PDF |
| `france_climat_YYYY_linkedin.pdf` | **LinkedIn** — même figure que le poster (post « Document ») |

```text
py export_poster_linkedin.py --poster output_france/publication/france_climat_poster_2025.png
```
| `classes_stables_4x4.json` | Seuils de classes figés |

Générer la version LinkedIn à partir du poster :

```text
py export_poster_linkedin.py --poster output_france/publication/france_climat_poster_2025.png
```

## Régénération
```text
py render_france_animation.py --years 2015 2025 --res 0.038 --smooth 1.6 --dpi 300
```
