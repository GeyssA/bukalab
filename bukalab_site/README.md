# Site BukaLab (statique)

Page d’accueil + onglet **Cartographie** avec **PNG pleine résolution** (zoom + téléchargement PDF).

## Mise à jour des cartes

```text
py bukalab_site/build_site.py
```

## Ajouter une vidéo

1. Déposer le `.mp4` (H.264) dans `assets/video/`, avec un nom sans accents ni espaces.
2. Ajouter une entrée dans `window.BUKALAB_VIDEOS` en tête de `js/videos.js`
   (titre, sous-titre, description FR/EN, durée, chapitres, poster facultatif).
3. Elle apparaît dans l'onglet **Vidéos** ; pour la mettre aussi sur l'accueil,
   ajouter un `<div class="film-slot" data-film-slot="id-de-la-video"></div>`.

Note : `py -m http.server` ne gère pas les requêtes partielles, donc on ne peut pas
naviguer dans la vidéo en local avec ce serveur (tout hébergeur classique le gère).

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
