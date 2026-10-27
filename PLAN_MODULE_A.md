# Plan final — Module A : Molécule + Médicament (Chemlali Ismail)

> Statut : **v2 — décisions prises, en attente du « go » final d'Ismail.**
> Objectif : **note complète sur les 7 critères** (20/20). Chaque section indique le critère visé.
> Source de vérité : `ontologie/pharma.ttl` (v2). Rien n'est inventé hors de l'ontologie.

## 0. Décisions validées
| # | Décision |
|---|---|
| 1 | Back-end **Python + FastAPI + rdflib** (pas de serveur Java). |
| 2 | **Une seule application** pour l'équipe ; mon module est écrit comme un module isolé, intégré aux autres à la fin. |
| 3 | Valeurs ajoutées choisies par Claude (voir §8). |
| 4 | Le **site vitrine actuel reste la page d'accueil** (`/`). |

---

## 1. Structure du dépôt (finale)

```
Pharma projet/
├─ ontologie/                     # partagé (équipe) — pharma.ttl = source
├─ backend/
│  ├─ app/
│  │  ├─ main.py                  # FastAPI : CORS, routeurs, /api/health
│  │  ├─ graph_store.py           # charge pharma.ttl, inférence OWL-RL, exécute SPARQL, sauvegarde
│  │  ├─ config.py                # chemins relatifs + variables .env
│  │  └─ modules/
│  │     └─ molecule_medicament/  # ← MON MODULE (A)
│  │        ├─ router.py          # routes /api/molecules, /api/medicaments, …
│  │        ├─ queries.py         # TOUTES les requêtes SPARQL nommées (catalogue)
│  │        ├─ schemas.py         # modèles Pydantic (validation entrée/sortie)
│  │        └─ service.py         # logique : comparateur, interactions, CRUD
│  ├─ nlp/
│  │  ├─ pharmanlu/               # ← MODÈLE IA « PharmaNLU-A »
│  │  │  ├─ pipeline.py           # question → intention + entités → SPARQL
│  │  │  ├─ normalizer.py         # spaCy : tokens, lemmes, accents
│  │  │  ├─ entities.py           # EntityRuler spaCy + RapidFuzz (fautes)
│  │  │  ├─ intent_model.py       # chargement / prédiction du classifieur
│  │  │  └─ templates.py          # gabarits SPARQL par intention
│  │  ├─ data/
│  │  │  ├─ intents_train.json    # ~300 questions annotées (écrites par nous)
│  │  │  └─ intents_test.json     # ~80 questions jamais vues à l'entraînement
│  │  ├─ models/
│  │  │  ├─ pharmanlu_intent_v1.joblib   # modèle entraîné (< 1 Mo, COMMITÉ)
│  │  │  └─ pharmanlu_intent_v1.json     # métriques + versions (carte du modèle)
│  │  ├─ train.py                 # ré-entraîne le modèle (reproductible, seed fixe)
│  │  └─ evaluate.py              # précision, rapport, matrice de confusion
│  ├─ data/runtime.ttl            # état modifié par le CRUD (ignoré par Git, recréé)
│  ├─ tests/                      # pytest : API + SPARQL + NLP
│  ├─ requirements.txt            # versions épinglées
│  └─ .env.example
├─ src/ (frontend React — site vitrine + application)
│  ├─ pages/  Home.jsx (vitrine) · Molecules.jsx · MoleculeDetail.jsx · Medicaments.jsx
│  │          MedicamentDetail.jsx · Comparateur.jsx · Interactions.jsx · Assistant.jsx · SparqlConsole.jsx
│  ├─ api/client.js               # fetch centralisé vers le back-end (URL via VITE_API_URL)
│  └─ components/ (existants + DataTable, FilterBar, EntityForm, SparqlViewer, ResultGraph…)
├─ scripts/ setup.bat · setup.sh · start.bat · start.sh
├─ README.md                      # installation pas à pas (testée sur clone neuf)
├─ CLAUDECONTEXT.md · PLAN_MODULE_A.md
```

## 2. Stack et versions (épinglées dans Git)

| Couche | Outil | Version |
|---|---|---|
| Langage back | Python | 3.10 → 3.13 (testé 3.13) |
| API | FastAPI + Uvicorn | 0.115.x / 0.32.x |
| RDF / SPARQL | rdflib | 7.1.x |
| Inférence | owlrl (OWL 2 RL) | 7.1.x |
| NLP | spaCy + modèle `fr_core_news_sm` | 3.8.x / 3.8.0 |
| Fautes de frappe | RapidFuzz | 3.x |
| Classifieur | scikit-learn + joblib | 1.5.x |
| Tests | pytest + httpx | — |
| Front | React 18 + Vite 5 + react-router-dom 6 + lucide-react | existants |

Le modèle spaCy est installé par `setup` via son URL de wheel officielle épinglée (pas de téléchargement manuel).

## 3. Back-end — API REST (critère « Communication BE↔FE » — 3 pts)

Préfixe commun `/api`. Réponses JSON ; **chaque réponse inclut la requête SPARQL exécutée** (`"sparql": "…"`) pour la montrer à l'oral.

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | état du serveur + nb de triplets |
| GET | `/molecules?classe=&q=&atc=&tri=` | liste + filtres + recherche |
| GET | `/molecules/{id}` | fiche : classes (déclarées + **inférées**), ATC, dose max, médicaments, effets, CI, interactions |
| POST | `/molecules` | créer (INSERT DATA) |
| PUT | `/molecules/{id}` | modifier (DELETE/INSERT WHERE) |
| DELETE | `/molecules/{id}` | supprimer (refus si un médicament la contient → cohérence) |
| GET | `/medicaments?type=&ordonnance=&forme=&prixMin=&prixMax=&molecule=&q=&tri=` | liste + filtres |
| GET | `/medicaments/{id}` | fiche + molécules + indications + contre-indications **déduites par la chaîne OWL** |
| POST / PUT / DELETE | `/medicaments[/{id}]` | CRUD (validation : ≥ 1 molécule, prix ≥ 0) |
| GET | `/medicaments/{id}/alternatives` | ⭐ comparateur princeps ↔ génériques |
| POST | `/interactions/verifier` | ⭐ corps `{ "medicaments": [...] }` → interactions détectées |
| GET | `/hierarchie` | arbre Molecule / Medicament (3 niveaux) |
| GET | `/stats` | agrégats pour le tableau de bord |
| GET | `/requetes` | catalogue des requêtes SPARQL nommées |
| POST | `/requetes/{nom}/executer` | exécute une requête du catalogue |
| POST | `/sparql` | console libre (SELECT/ASK ; UPDATE désactivé par sécurité) |
| POST | `/nlp/ask` | ⭐ question FR → `{intention, confiance, entites, sparql, resultats, reponse}` |
| GET | `/nlp/suggestions` | exemples de questions cliquables |
| POST | `/admin/reset` | recharge l'ontologie d'origine (avant la démo) |

Persistance : le CRUD modifie le graphe en mémoire puis l'enregistre dans `backend/data/runtime.ttl` ; `pharma.ttl` (fichier d'équipe) n'est **jamais** écrasé.

## 4. Requêtes SPARQL (critère 4 pts) — catalogue `queries.py`, 15 requêtes nommées

| Nom | Notion SPARQL montrée |
|---|---|
| `Q01_hierarchie_molecules` | `rdfs:subClassOf+` (chemin de propriété) |
| `Q02_antibiotiques` | `rdf:type/rdfs:subClassOf*` |
| `Q03_sans_ordonnance_moins_de` | FILTER numérique + booléen + ORDER BY |
| `Q04_recherche_texte` | FILTER REGEX insensible à la casse |
| `Q05_medicaments_par_molecule` | propriété inverse `estContenuDans` |
| `Q06_alternatives_generiques` | jointure + BIND (économie en DT et %) |
| `Q07_interactions` | propriété **symétrique** `interagitAvec` |
| `Q08_contre_indiques_pour` | chaîne `contientMolecule/aContreIndication/concernePathologie` |
| `Q09_effets_graves_medicament` | OPTIONAL + FILTER |
| `Q10_stats_par_classe` | COUNT, AVG, MIN, MAX, GROUP BY, HAVING |
| `Q11_molecules_orphelines` | FILTER NOT EXISTS |
| `Q12_est_sur_ordonnance` | ASK |
| `Q13_fiche_medicament` | CONSTRUCT (sous-graphe pour la visualisation) |
| `Q14_crud_*` | INSERT DATA / DELETE-INSERT WHERE / DELETE WHERE |
| `Q15_types_inferes` | comparaison types déclarés vs inférés (OWL-RL) |

## 5. Module IA — modèle « PharmaNLU-A » (critère API IA — 4 pts)

**Nom :** `PharmaNLU-A` (Natural Language Understanding, module A), fichier `pharmanlu_intent_v1.joblib`.
**Type :** modèle **hybride** — classifieur statistique supervisé + règles linguistiques. **Aucune API LLM.**

### Pipeline (5 étapes, toutes locales)
1. **Normalisation — spaCy `fr_core_news_sm`** : tokenisation, lemmatisation, minuscules, suppression des accents.
2. **Classification d'intention — scikit-learn** :
   - Vectorisation `FeatureUnion` : TF-IDF **mots** (1–2-grammes, sur les lemmes) + TF-IDF **caractères** (3–5-grammes, robuste aux fautes).
   - Classifieur : **régression logistique** multinomiale (`class_weight="balanced"`, `random_state=42`) → donne une **probabilité** (confiance).
   - Seuil : si confiance < 0,45 → réponse « je n'ai pas compris » + suggestions (pas de requête fausse).
   - Entraîné sur `intents_train.json` (~300 phrases écrites par nous), évalué sur `intents_test.json` (~80 phrases jamais vues). Objectif ≥ 90 % de précision.
3. **Extraction d'entités — spaCy `EntityRuler` + RapidFuzz** :
   - Dictionnaire **généré automatiquement depuis l'ontologie** (labels de molécules, médicaments, classes, pathologies, formes) → toute nouvelle donnée ajoutée par le CRUD est reconnue sans ré-entraîner.
   - RapidFuzz (`token_set_ratio` ≥ 85) corrige « ibuprophene », « dolipran », « amoxiciline ».
   - Règles pour nombres et comparateurs : « moins de 5 dinars » → `prix < 5`.
4. **Génération SPARQL** — gabarit de l'intention rempli avec les URI trouvées → requête **toujours valide**.
5. **Réponse** — exécution + phrase en français + requête SPARQL affichée et expliquée.

### Intentions (12)
| Intention | Exemple |
|---|---|
| `lister_molecules_classe` | « Liste des antibiotiques » |
| `lister_medicaments_filtre` | « Médicaments sans ordonnance à moins de 5 dinars » |
| `medicaments_contenant` | « Quels médicaments contiennent de l'ibuprofène ? » |
| `molecules_de_medicament` | « Que contient le Doliprane ? » |
| `effets_secondaires` | « Effets secondaires graves de l'Advil ? » |
| `contre_indications` | « Contre-indications de l'aspirine ? » |
| `contre_indiques_pour_pathologie` | « Médicaments déconseillés en cas d'ulcère ? » |
| `generique_alternative` | « Y a-t-il un générique moins cher que le Clamoxyl ? » |
| `interaction` | « Advil et Aspégic interagissent-ils ? » |
| `info_attribut` | « Quel est le code ATC du paracétamol ? » / « Prix du Zithromax ? » |
| `indication` | « Pour quoi est indiqué le Glucophage ? » |
| `statistiques` | « Combien de médicaments génériques ? » |

### Carte du modèle (`pharmanlu_intent_v1.json`)
Versions des bibliothèques, date d'entraînement, taille du jeu, précision, F1 par intention → affichée dans l'interface (onglet « À propos du modèle »).

## 6. Interface graphique (critère 3 pts) — charte « Sage Studio »

| Route | Page |
|---|---|
| `/` | Site vitrine existant (accueil) + bouton « Ouvrir l'application » |
| `/molecules` | tableau filtrable (classe, ATC, recherche) + arbre de hiérarchie |
| `/molecules/:id` | fiche + mini-graphe (médicaments, effets, CI) |
| `/medicaments` | cartes + barre de filtres (type, ordonnance, forme, curseur de prix) |
| `/medicaments/:id` | fiche + contre-indications déduites + alternatives |
| `/comparateur` | ⭐ princeps vs génériques |
| `/interactions` | ⭐ vérificateur multi-médicaments |
| `/assistant` | ⭐ questions en langage naturel |
| `/sparql` | console : 15 requêtes en un clic + éditeur |

Formulaires CRUD en fenêtre modale avec validation, notifications de succès/erreur, états de chargement et « aucun résultat », responsive mobile.

## 7. Scénario de démonstration (critère 2 pts) — ~5 min

1. **Accueil** → « Ouvrir l'application ».
2. **Assistant** : « quels médicaments contiennent de l'ibuprophene » (faute volontaire) → Advil + Ibuprofène Mylan ; je montre la requête générée, l'intention et la confiance.
3. **Comparateur** : Advil 6,5 DT → Ibuprofène Mylan 3,9 DT = **−40 %**.
4. **Interactions** : Advil + Aspégic → ⚠️ ibuprofène ↔ aspirine (propriété symétrique, déclarée dans un seul sens).
5. **CRUD** : j'ajoute « Paracétamol Biogaran » (générique, sans ordonnance) → l'inférence le classe automatiquement en `GeneriqueSansOrdonnance` (badge « inféré ») ; l'assistant le trouve immédiatement.
6. **Console SPARQL** : 2–3 requêtes du catalogue (chaîne de propriétés, agrégat, NOT EXISTS).
7. `/admin/reset` pour remettre les données.

## 8. Valeur ajoutée (critère 2 pts) — proposition retenue

1. ⭐ **Comparateur princeps / générique** avec économie en DT et en %.
2. ⭐ **Vérificateur d'interactions** entre plusieurs médicaments (exploite la symétrie OWL).
3. ⭐ **IA explicable** : intention + confiance + entités + requête SPARQL commentée + tolérance aux fautes + précision mesurée affichée.
4. **Inférence visible** : badges « inféré » (classes définies OWL, propriétés inverses/symétriques, chaîne de contre-indications).
5. **Graphe interactif** d'une fiche (réutilise le style de l'ontographe du site vitrine).
6. Export CSV des résultats + historique des questions de l'assistant.

## 9. Qualité, portabilité, Git
- `scripts/setup.(bat|sh)` : crée le venv, `pip install -r requirements.txt`, installe `fr_core_news_sm`, `npm install`.
- `scripts/start.(bat|sh)` : lance back (port 8000) + front (port 5173).
- Tests `pytest` (API, 15 requêtes, NLP ≥ 90 % sur le jeu de test) lancés avant chaque push.
- Commits fréquents et explicites sur `main` (ou branche `module-a` si l'équipe le souhaite).
- Validation finale : **clone neuf dans un dossier vide → setup → start → scénario complet**.

## 10. Ordre de réalisation
1. Back-end socle (`graph_store`, `/health`) + catalogue SPARQL + tests.
2. API Molécules/Médicaments + CRUD + comparateur + interactions.
3. Front : routage, pages listes/fiches/CRUD, console SPARQL.
4. PharmaNLU-A : jeux de données → entraînement → évaluation → `/nlp/ask` → page Assistant.
5. Valeurs ajoutées restantes (graphe, export, badges inférés).
6. Scripts setup/start, README, test sur clone neuf, push.
7. Fiche de présentation (outils NLP cités, captures, scénario).
