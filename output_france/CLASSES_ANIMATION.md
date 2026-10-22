# Classes T° / précipitations — animation 2015–2025

## Le bug que tu as remarqué (5 vs 4×4)

Sur ta carte 2025 :

| Couche | Nb de classes | Méthode typique |
|--------|---------------|-----------------|
| Carte T° seule (petite) | **5** | quantiles 20 % (quintiles) |
| Carte précip seule (petite) | **5** | quantiles 20 % |
| Carte combinée (losange) | **4 × 4 = 16** | quantiles 25 % (quartiles) |

Ce n’est **pas** cohérent : les petits cartons et le losange ne découpent pas les mêmes seuils.  
Dans le dépôt, le QML communes bivarié était même en **3×3** (encore une autre grille).

Conséquence : une zone « classe 5 » en T° ne correspond à aucune ligne exacte du losange 4×4.

## Ce qu’il faut pour un défilé 10 ans

1. **Même maillage** tous les ans (on réutilise les 2 865 points de 2025).
2. **Mêmes seuils** tous les ans (figés sur 2025, pas recalculés chaque année).
   - Sinon les couleurs bougent parce que les quantiles bougent, pas seulement le climat.
3. **Même n** pour mono et bivarié :
   - **4 classes** → losange **4×4** (recommandé, = ta légende centrale)
   - ou **5 classes** → losange **5×5** (25 couleurs, plus lourd)
   - ou **3×3** (plus lisible, moins de nuance)

**Recommandation :** `n = 4` partout (T, P, bivarié). Les petites cartes T/P de ta mise en page devront passer de 5 à 4 classes pour coller au losange.

## Commandes

```powershell
# 1) Extraire 2015 (reprise auto si interrompu)
py recuperer_france_climat_grille.py --year 2015 --classes 4

# 2) Quand le CSV est complet : exporter couches + QML (seuils figés 2025)
py export_france_annee_couches.py --year 2015 --classes 4

# Plus tard : 2016–2024
py recuperer_france_climat_grille.py --from 2016 --to 2024 --classes 4
```

## Variante printemps-été (1er mars – 31 août)

Même maillage, même rendu, mêmes règles de classes (4×4, quartiles 2025 arrondis, figés),
mais agrégé sur mars–août : moitié moins de jours à télécharger et signal des épisodes de
chaleur plus net. Colonnes en plus : `tmax_moyenne_{année}` et `jours_30_{année}`
(nombre de jours avec Tmax ≥ 30 °C).

```powershell
py recuperer_france_climat_grille.py --saison printemps_ete --year 2025
py recuperer_france_climat_grille.py --saison printemps_ete --from 2015 --to 2024
py render_france_animation.py --saison printemps_ete --years 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025
```

- Grilles : `output_france/grilles_printemps_ete/` (+ `classes_fixes_4x4_ref2025.json`)
- Posters / vidéo : `output_france/publication_printemps_ete/`

Fichiers :
- Grilles : `output_france/grilles_annuelles/france_climat_{année}_grille.csv`
- Seuils : `output_france/grilles_annuelles/classes_fixes_4x4_ref2025.json`
- Couches année : `output_france/annees/{année}/`
