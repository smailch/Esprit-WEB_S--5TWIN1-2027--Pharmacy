# PharmaSémantique — Ontologie Pharmaceutique et Santé

Site vitrine (React + Vite) du projet de Web Sémantique de l’équipe **NeoCoders** — 5 TWIN · 2026–2027.

Projet académique : il présente la structure de l’ontologie (classes, relations, individus, ontographe).
Il ne réalise aucun diagnostic et ne fournit aucune recommandation médicale.

## Installation et lancement

Prérequis : Node.js 18 ou plus récent.

```bash
npm install
npm run dev
```

Puis ouvrir l’URL affichée (par défaut http://localhost:5173).

Build de production : `npm run build`, aperçu : `npm run preview`.

## Vidéo d’arrière-plan

Placer la vidéo du hero dans `public/videos/pharmacy-hero.mp4` (et, en option, une affiche
`public/videos/pharmacy-hero-poster.png`). Les chemins se modifient dans `src/data/ontologyData.js`
(`HERO_VIDEO_SRC`, `HERO_POSTER_SRC`).

Sans fichier vidéo, ou si l’utilisateur a activé « réduire les animations », un fond vert sauge statique est affiché.

## Structure

```
src/
  components/   Navbar, Hero, ApproachSection, OntologyDiagram, ClassGrid, RelationshipTable,
                IndividualsSection, OntoGraphSection, ValidationSection, TeamSection, Footer…
  data/         ontologyData.js — toutes les classes, relations, individus et textes
  hooks/        useReveal.js — apparition au défilement (IntersectionObserver)
  App.jsx, main.jsx, styles.css
```

Le contenu est piloté par `src/data/ontologyData.js` : modifier ce fichier suffit pour mettre à jour
les classes, relations, individus ou l’ontographe.

## Équipe NeoCoders

Allaya Ahmed · Gobji Walid · Missaoui Mourad · Chemlali Ismail
