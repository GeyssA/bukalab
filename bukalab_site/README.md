# Site BukaLab (statique)

Page d’accueil + onglet **Cartographie** avec **PNG pleine résolution** (zoom + téléchargement PDF).

## Mise à jour des cartes

```text
py bukalab_site/build_site.py
```

## Prévisualisation locale

Les images sont dans `assets/cartes/` après le build. Prévisualisation (recommandé) :

```text
py -m http.server 8080 --directory bukalab_site
```

Puis ouvrir :

- Accueil : http://localhost:8080/
- Cartographie : http://localhost:8080/#cartographie
- Lien direct France 2025 : http://localhost:8080/#cartographie?carte=france-climat-2025

## Publication

Déployer le dossier `bukalab_site/` entier (Netlify, GitHub Pages, OVH, etc.).

Lien à coller sur LinkedIn : `https://votre-domaine.fr/#cartographie?carte=france-climat-2025`
