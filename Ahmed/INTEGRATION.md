# Intégration avec le travail de l'équipe (pull manuel de `origin/main`)

## Comment mon travail s'insère dans le projet
| Élément | Module A (sur `origin/main`) | Ahmed (cette branche) |
|---|---|---|
| Interface | `index.html` → `src/App.jsx` (react-router, `src/pages/`, `src/app/`) | `ahmed.html` → `src/ahmed/` (même projet Vite) |
| URL | http://localhost:5173/molecules … | http://localhost:5173/ahmed.html |
| Backend | `backend/` à la racine, port **8000**, préfixe `/api` | `Ahmed/backend/`, port **8001**, préfixe `/api-ahmed` |
| Scripts | `scripts/` à la racine | `Ahmed/scripts/` |

Aucun de mes fichiers ne porte le même chemin qu'un fichier du module A.
Les deux seuls fichiers partagés que j'ai modifiés sont `vite.config.js` et `src/components/Footer.jsx` (non modifié par le module A).

## Étapes du pull
```powershell
git status                      # doit être propre (tout est commité)
git pull origin main            # sur la branche AhmedAllaya
```
Conflit attendu : **`vite.config.js` uniquement**. Remplacer tout son contenu par :

```js
import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// En développement, /api est redirigé vers le back-end FastAPI (port 8000) : pas de souci de CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Modules Pathologie + Personne (Ahmed) : back-end sur le port 8001, page /ahmed.html.
      // À garder AVANT '/api' : sinon '/api' capterait aussi les URL '/api-ahmed/…'.
      '/api-ahmed': {
        target: process.env.VITE_AHMED_BACKEND_URL || 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api-ahmed/, '/api'),
      },
      '/api': { target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    rollupOptions: {
      input: { main: resolve(__dirname, 'index.html'), ahmed: resolve(__dirname, 'ahmed.html') },
    },
  },
});
```
Puis :
```powershell
git add vite.config.js
git commit                      # termine la fusion
npm install                     # le module A a ajouté react-router-dom
```

## Vérifier après la fusion
1. Backend module A : selon leur README (port 8000). Mon backend : `cd Ahmed/backend; .venv/Scripts/python -m uvicorn app.main:app --port 8001`.
2. `npm run dev` à la racine, puis ouvrir http://localhost:5173/ahmed.html et http://localhost:5173/molecules.
3. `npm run build` : `dist/ahmed.html` doit exister.
4. Mes tests : `cd Ahmed/backend; .venv/Scripts/python -m pytest -q` (65 tests). Si `ontologie/pharma.ttl` a changé,
   certains tests qui comptent exactement (11 patients, 3 alertes) peuvent échouer : à adapter, l'appli reste fonctionnelle.

## Option après la fusion (facultatif)
Ajouter un lien vers mon application dans le menu du module A (`src/app/AppShell.jsx`, tableau `links`) :
`<a href="/ahmed.html">Pathologies & Personnes</a>`. Un lien `<Link>` de react-router ne convient pas : `ahmed.html` est une page à part.
