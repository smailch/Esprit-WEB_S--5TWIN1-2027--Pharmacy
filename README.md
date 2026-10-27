# PharmaSémantique — Ontologie Pharmaceutique et Santé

Mini-projet de Web Sémantique — **NeoCoders**, Esprit 5 TWIN, 2026/2027.
Ontologie OWL (Protégé / HermiT) + back-end SPARQL + application React + assistant en langage naturel.

> Projet académique : données fictives, aucune recommandation médicale.

---

## Installation sur un nouveau PC (5 minutes)

Prérequis : **Python 3.11 ou plus récent** (testé avec 3.13) et **Node.js 18+**. Aucune clé API, aucun serveur à installer.

```bash
git clone https://github.com/smailch/Esprit-WEB_S--5TWIN1-2027--Pharmacy.git
cd Esprit-WEB_S--5TWIN1-2027--Pharmacy
```

| | Windows | macOS / Linux |
|---|---|---|
| Installer (une seule fois) | `scripts\setup.bat` | `./scripts/setup.sh` |
| Lancer | `scripts\start.bat` | `./scripts/start.sh` |

Puis ouvrir **http://localhost:5173** (site vitrine) → bouton « Ouvrir l'application ».
Documentation interactive de l'API : **http://localhost:8000/docs**.

L'installation télécharge automatiquement le modèle spaCy `fr_core_news_sm` (version épinglée).
Le modèle d'intention entraîné (`backend/nlp/models/pharmanlu_intent_v1.joblib`) est déjà dans le dépôt.

> **Windows** : clonez dans un dossier au chemin court (ex. `C:\projets\pharma`). Les chemins de plus de 260 caractères
> empêchent spaCy de charger ses bibliothèques (« DLL load failed… Nom de fichier ou extension trop long »).

### Lancement manuel (si besoin)
```bash
# Terminal 1 — API
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000   # Windows
backend/.venv/bin/python     -m uvicorn app.main:app --app-dir backend --port 8000   # macOS/Linux
# Terminal 2 — front
npm run dev
```

---

## Architecture

```
ontologie/        pharma.ttl (source), pharma.owl (Protégé), requetes.sparql
backend/          FastAPI + rdflib + owlrl (inférence OWL 2 RL)
  app/modules/molecule_medicament/   module A : routes, 16 requêtes SPARQL nommées, CRUD
  nlp/pharmanlu/                     modèle IA PharmaNLU-A (question → SPARQL)
  nlp/data/  nlp/models/             jeux de données et modèle entraîné
  tests/                             36 tests pytest
src/              React + Vite : site vitrine (/) + application (/molecules, /medicaments…)
scripts/          setup / start (Windows et macOS/Linux)
```

- Le graphe est chargé depuis `ontologie/pharma.ttl`, puis enrichi par le raisonneur **OWL 2 RL** (owlrl) dans un graphe nommé séparé : l'interface distingue les faits **déclarés** et **inférés**.
- Le CRUD modifie `backend/data/runtime.ttl` (ignoré par Git) ; `pharma.ttl` n'est jamais écrasé. Bouton « Réinitialiser les données » ou `POST /api/admin/reset` pour revenir à l'état d'origine.
- Chaque réponse de l'API contient les requêtes SPARQL exécutées, affichées dans l'interface.

## Module A — Molécule + Médicament (Chemlali Ismail)

| Page | Contenu |
|---|---|
| Molécules | liste filtrable (classe via la hiérarchie, ATC, recherche sans accents), arbre 3 niveaux, fiche, CRUD |
| Médicaments | cartes filtrables (type, ordonnance, forme, prix), statistiques, fiche, graphe CONSTRUCT, CRUD |
| Comparateur | princeps ↔ génériques de même composition, économie en DT et en % |
| Interactions | interactions (propriété symétrique) et doublons de principe actif entre plusieurs médicaments |
| Assistant IA | question en français → SPARQL → réponse (modèle PharmaNLU-A) |
| Console SPARQL | 16 requêtes du catalogue en un clic + éditeur (lecture seule) |

### Assistant IA — modèle PharmaNLU-A (aucune API de LLM)

| Étape | Outil |
|---|---|
| Normalisation, tokenisation, lemmatisation | **spaCy 3.8** + `fr_core_news_sm` |
| Reconnaissance des entités (dictionnaire généré depuis l'ontologie) | **spaCy EntityRuler** |
| Correction des fautes de frappe | **RapidFuzz** (distance de Levenshtein) |
| Classification de l'intention (12 intentions) | **scikit-learn** : TF-IDF mots + caractères → régression logistique |
| Génération et exécution de la requête | gabarits SPARQL + **rdflib** |

Résultats sur 96 questions de test écrites à la main (jamais vues à l'entraînement) : **96,9 % d'intentions correctes, 100 % d'entités reconnues**.

```bash
cd backend
.venv/Scripts/python nlp/data/generer_donnees.py   # régénère le jeu d'entraînement
.venv/Scripts/python -m nlp.train                  # ré-entraîne + évalue + écrit la carte du modèle
.venv/Scripts/python -m nlp.evaluate               # évalue le modèle enregistré
.venv/Scripts/python -m pytest -q                  # 36 tests
```

## Équipe NeoCoders

Allaya Ahmed · Gobji Walid · Missaoui Mourad · Chemlali Ismail

---

## Module D — Prescription + Donnée clinique (Gobji Walid)

Répartition de l'équipe : module A Molécule + Médicament (Chemlali Ismail), Pathologie + Personne (Allaya Ahmed),
EffetSecondaire + ContreIndication (Missaoui Mourad), **Prescription + DonneeClinique (Gobji Walid)**.

Le module utilise l'**ontologie v2 sans aucune modification** (`ontologie/pharma.ttl`) :

- `Prescription` → `PrescriptionSimple` (`PrescriptionNormale`, `PrescriptionUrgente`) / `PrescriptionRenouvelable`
  (`RenouvellementCourt`, `RenouvellementLong`) ; propriétés `prescritPar`, `concernePatient`, `prescritMedicament`,
  `estDelivreePar`, `datePrescription`, `dureeJours`, `posologie`, `estRenouvelable` ;
- `DonneeClinique` → `ExamenClinique` (`SigneVital`, `AnalyseBiologique`) / `HistoriqueMedical` (`Allergie`, `Antecedent`) ;
  propriétés `estDonneeDe` (inverse `aDonneeClinique`), `valeur`, `unite`, `dateMesure`, `allergiqueA`, `porteSur`.

Il **crée, modifie et supprime uniquement** des prescriptions et des données cliniques. Les patients, médecins,
pharmaciens, médicaments, molécules et pathologies des autres modules sont **lus seulement**, car les relations
de Prescription et de DonneeClinique pointent vers eux. Le module est autonome : il ne dépend pas du code des autres
modules (seulement du socle commun `graph_store.py`, inchangé).

### Individus utilisés (ontologie v2)

| Classe | Individus |
|---|---|
| Prescription | `Presc_001` (RenouvellementLong, Ali, Glucophage), `Presc_002` (Urgente, Sara, Clamoxyl), `Presc_003` (Normale, Youssef, Advil + Doliprane), `Presc_004` (RenouvellementCourt, Lina, Zithromax) |
| DonneeClinique | `Glycemie_Ali`, `Creatinine_Ali` (AnalyseBiologique), `Tension_Youssef`, `Temperature_Sara` (SigneVital), `Allergie_Sara` (Allergie → Amoxicilline), `Antecedent_Youssef` (Antecedent → UlcereGastroduodenal) |

La présentation cite des individus qui n'existent plus en v2 (`Patient_F001…F003`, `Dr_Fictif_01`, `Comprimé`, `Voie_Orale`)
et la classe `ModalitéAdministration`, supprimée en v2 : ces diapositives sont à mettre à jour.

### Installation et lancement (Windows, PowerShell)

```powershell
git clone https://github.com/smailch/Esprit-WEB_S--5TWIN1-2027--Pharmacy.git
cd Esprit-WEB_S--5TWIN1-2027--Pharmacy

# Back-end (Python 3.12 ou 3.13)
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # installe aussi le modèle spaCy fr_core_news_sm
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
# Documentation interactive : http://localhost:8000/docs

# Front-end (autre terminal, à la racine du dépôt)
npm install
npm run dev        # http://localhost:5173/prescriptions
```

- Modèle spaCy seul : `.venv\Scripts\python -m spacy download fr_core_news_sm`. S'il est absent, l'assistant passe en
  **mode lexical** (`spacy.blank("fr")`, signalé dans la réponse) ; si spaCy n'est pas installé, l'API répond `503`
  avec la commande d'installation.
- URL de l'API côté front : variable `VITE_API_URL` (défaut `/api`, redirigé vers le port 8000 par le proxy Vite).
- Tests du module : `cd backend` puis `.venv\Scripts\python -m pytest tests/module_d -q` (toute la suite : `pytest -q`).
  Les tests du module D chargent une **copie** de `pharma.ttl` (`tests/module_d/conftest.py`).
- Évaluation du TALN : `.venv\Scripts\python -m nlp.prescrinlu.evaluation`.

### Interfaces (groupe « Module D » du menu)

| Route | Contenu |
|---|---|
| `/prescriptions` | Liste paginée : filtres type (hiérarchie à 3 niveaux), patient, médecin, médicament, période (`xsd:date`), recherche, tri, export CSV, indicateurs |
| `/prescriptions/:id` | Fiche : classes déclarées / **inférées**, patient, médecin, pharmacien, médicaments, dossier clinique du patient, alertes, graphe CONSTRUCT, modifier / supprimer |
| `/donnees-cliniques` | Signes vitaux, analyses, allergies, antécédents : filtres type / patient / période, recherche, tri, pagination, CRUD |
| `/scenario` | Dossier patient : données cliniques, chaîne Patient → Prescription → Médicament → Molécule → Contre-indication → Pathologie, alertes |
| `/module-d/assistant` | Assistant en langage naturel PrescriNLU-D |
| `/module-d/sparql` | Catalogue de 18 requêtes du module + requête libre contrôlée |

L'application n'a pas de gestion d'utilisateurs : les formulaires CRUD sont accessibles comme ceux du module A.

### API REST du module D

Réponses REST : `{ "data": …, "sparql": [{ "titre", "requete" }] }` (requêtes exécutées, affichées dans l'interface).
Les ressources sont sous `/api/prescriptions` et `/api/donnees-cliniques` ; tout le reste est préfixé par
`/api/module-d/` pour éviter les doublons avec les routes des autres modules.

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/prescriptions?type=&patient=&medecin=&pharmacien=&medicament=&dateMin=&dateMax=&q=&tri=&page=&taille=` | liste filtrée, triée, paginée (COUNT + LIMIT/OFFSET) |
| GET | `/api/prescriptions/{id}` · `/api/prescriptions/{id}/graphe` | fiche + alertes · sous-graphe CONSTRUCT |
| POST / PUT / DELETE | `/api/prescriptions[/{id}]` | CRUD validé (types, dates, références, cardinalités) |
| GET | `/api/prescriptions/statistiques` · `/api/prescriptions/alertes?patient=` | agrégats · prescriptions à risque |
| GET | `/api/donnees-cliniques?type=&patient=&dateMin=&dateMax=&q=&tri=&page=&taille=` · `/api/donnees-cliniques/{id}` | liste, fiche |
| POST / PUT / DELETE | `/api/donnees-cliniques[/{id}]` | CRUD validé (champs selon le type, références, dates) |
| GET | `/api/module-d/patients/{id}/dossier` | scénario : chaîne + données cliniques + alertes |
| GET | `/api/module-d/referentiels` · `/api/module-d/ontologie` | listes des formulaires · statistiques du graphe |
| GET / POST | `/api/module-d/requetes` · `/api/module-d/requetes/{nom}/executer` | catalogue SPARQL |
| POST | `/api/module-d/sparql` | requête utilisateur **contrôlée** (SELECT / ASK / CONSTRUCT) |
| POST | `/api/module-d/nlp/ask` | question française → SPARQL → résultats |
| GET | `/api/module-d/nlp/suggestions` · `/api/module-d/nlp/modele` | exemples · carte du modèle + évaluation |

`/api/health` et `/api/admin/reset` sont ceux du socle commun. `/api/nlp/ask` reste réservé à l'assistant du module A.

Exemples :

```http
POST /api/donnees-cliniques
{ "type": "Allergie", "patient": "Patient_Lina", "libelle": "Allergie à l'azithromycine",
  "dateMesure": "2025-01-10", "molecule": "Azithromycine" }
201 { "data": { "id": "Allergie_Lina", "type": "Allergie", "molecule": { "id": "Azithromycine", … }, … },
      "sparql": [{ "titre": "Création (INSERT DATA)", "requete": "INSERT DATA { :Allergie_Lina a owl:NamedIndividual , :Allergie ; … }" }, …] }
→ GET /api/prescriptions/alertes?patient=Patient_Lina signale aussitôt Presc_004 (Zithromax contient de l'azithromycine).

POST /api/module-d/nlp/ask
{ "question": "Quels patients ont une clairance de la créatinine inférieure à 60 ?" }
200 { "intent": "seuil_mesure", "confidence": 1.0,
      "entities": [{ "type": "MESURE", "id": "Clairance de la créatinine", "texte": "clairance de la creatinine", "methode": "dictionnaire" }],
      "seuil": { "op": "<", "valeur": 60.0, "texte": "inferieure a 60" },
      "sparql": "SELECT ?patient ?nom ?donnee ?examen ?valeur ?unite ?date WHERE { … FILTER(?valeur < 60.0) }",
      "results": [{ "patient": "Patient_Ali", "nom": "Ali Ben Salah", "valeur": 38, "unite": "mL/min", … }], "count": 1,
      "message": "Clairance de la créatinine — Ali Ben Salah : 38 mL/min (mesure du 2026-09-01)." }
```

Erreurs : `422` (validation : type inconnu, date future ou mal formée, durée incohérente avec le type, valeur manquante pour
un examen, molécule manquante pour une allergie, identifiant non conforme), `404` (individu inexistant ou de mauvaise classe),
`400` (filtre invalide, requête SPARQL refusée), `503` (spaCy absent).

### Sécurité des écritures et des requêtes

- Aucune requête de mise à jour ne vient du client : le CRUD construit lui-même `INSERT DATA` / `DELETE … INSERT … WHERE`
  avec une **liste blanche** de propriétés par classe.
- Identifiants validés (`^[A-Za-z][A-Za-z0-9_]*$`) et vérifiés dans le graphe avec la bonne classe ; littéraux sérialisés
  et échappés par rdflib ; dates converties en `xsd:date` ; champs autorisés selon le domaine des propriétés
  (`valeur`/`unite` → ExamenClinique, `allergiqueA` → Allergie, `porteSur` → Antecedent).
- `/api/module-d/sparql` **analyse** la requête (parseur SPARQL de rdflib) et inspecte son algèbre : seules SELECT / ASK /
  CONSTRUCT passent ; `INSERT`, `DELETE`, `LOAD`, `DROP`, `SERVICE` et `FROM` sont refusés ; le nombre de lignes est plafonné.

### Requêtes SPARQL (catalogue `backend/app/modules/prescription_clinique/queries.py`)

| Nom | Notion |
|---|---|
| D01 prescriptions par type | `rdf:type/rdfs:subClassOf*`, classe définie inférée |
| D02 période | `FILTER` sur `xsd:date` |
| D03 ordonnance complète | jointures, chemins de propriétés, `OPTIONAL`, `GROUP_CONCAT` |
| D04 prescriptions d'un médecin | propriété inverse `aPrescrit` (inférée) |
| D05 médicaments d'un patient | chemin `aPrescription/prescritMedicament` |
| D06 alertes | `UNION` de 4 raisonnements : pathologie, allergie, antécédent, analyse (extension de Q6 de `requetes.sparql`) |
| D07 chaîne du patient | parcours de 5 relations, `BIND(EXISTS { … UNION … })` |
| D08 activité des médecins | `COUNT`, `AVG`, `MIN`, `MAX`, `GROUP BY`, `HAVING` |
| D09 ordonnances non délivrées · D16 patients sans donnée | `FILTER NOT EXISTS` |
| D10, D11 | `ASK` |
| D12 graphe d'une ordonnance + dossier clinique | `CONSTRUCT` |
| D13 données par type | `GROUP BY` sur la hiérarchie |
| D14 clairance < 60 | `FILTER` numérique (Q8 de `requetes.sparql`) |
| D15 dossier clinique | propriété inverse `aDonneeClinique`, `UNION` |
| D17 types inférés | graphes nommés déclaré / inféré |
| D18 CRUD | `INSERT DATA`, `DELETE/INSERT WHERE`, `DELETE WHERE` (affichée ; exécutée via les formulaires) |

**Limites du raisonnement** : rdflib ne fait pas de raisonnement OWL complet. Le socle utilise **owlrl (OWL 2 RL)** :
sous-classes, propriétés inverses (`aPrescrit`, `aPrescription`, `aDonneeClinique`) et classes définies par `owl:hasValue`
(`PrescriptionSimple` / `PrescriptionRenouvelable` à partir de `estRenouvelable`). Les restrictions sur types de données
(âge, seuils) ne sont pas couvertes par OWL 2 RL : elles sont exprimées en SPARQL (`FILTER`). Protégé + HermiT reste
la référence pour la cohérence globale.

### API IA : PrescriNLU-D (TALN local, sans LLM)

Bibliothèques réellement utilisées : **spaCy 3.8** + modèle **fr_core_news_sm** (tokenisation, lemmatisation,
`PhraseMatcher`), **RapidFuzz** (fautes de frappe), **RDFLib** (exécution SPARQL), **owlrl** (inférence),
**FastAPI** / **Pydantic** (API). Aucun appel réseau, aucune API externe. Code : `backend/nlp/prescrinlu/`.

1. **Prétraitement** (`preprocessing.py`) : minuscules, apostrophes, accents, ponctuation, variantes (« docteur » → « dr »),
   correction des mots métier mal écrits (« medicamants »), lemmes spaCy.
2. **Entités** (`lexicon.py`, `entity_extractor.py`) : dictionnaire **généré depuis l'ontologie par SPARQL** à chaque question
   (ordonnances, patients, médecins, pharmaciens, médicaments, molécules, pathologies, types de prescription et de donnée
   clinique, libellés d'examens) ; `PhraseMatcher` spaCy (plus longue correspondance) ; règles pour « Presc_002 » /
   « ordonnance 3 », les dates et périodes (« octobre 2026 », « entre … et … », « après le 12/10/2026 ») et les seuils
   (« inférieure à 60 », « > 140 ») ; RapidFuzz pour « dolipran » → Doliprane ; un identifiant absent de l'ontologie
   (« Patient_F001 ») est signalé, jamais inventé.
3. **Intention** (`intent_classifier.py`) : 19 intentions décrites par des indices pondérés sur le texte et les lemmes,
   des contraintes d'entités et des indices obligatoires ; scores → probabilités (softmax) ; sous le seuil, une
   reformulation est demandée.
4. **Génération SPARQL** (`sparql_generator.py`) : un gabarit par intention ; seules des URI existantes (revalidées), des
   littéraux échappés par rdflib et des opérateurs d'une liste blanche y sont insérés.
5. **Exécution** (`pipeline.py`) : RDFLib sur le graphe déclaré + inféré, réponse en français.
6. **Explication** : intention, confiance, indices déclenchés, entités et méthode de reconnaissance, période, seuil, lemmes,
   mots corrigés, requête commentée, durée de chaque étape.
7. **Évaluation** (`evaluation.py`, `data/questions_eval.json`) : 62 questions annotées à la main (fautes, entités inconnues,
   hors sujet) ; 100 % d'intentions et d'entités correctes ; affiché dans « À propos du modèle ».

| Question | Intention | Entités | Requête produite (extrait) | Réponse |
|---|---|---|---|---|
| Quelles sont les prescriptions renouvelables ? | `prescriptions_par_type` | `:PrescriptionRenouvelable` | `?prescription a :PrescriptionRenouvelable .` | Presc_001, Presc_004 |
| Quels médicaments sont prescrits à Patient_Ali ? | `medicaments_patient` | `:Patient_Ali` | `?prescription :concernePatient :Patient_Ali .` | Glucophage 850 mg |
| Qui a prescrit Presc_002 ? | `prescripteur` | `:Presc_002` | `:Presc_002 :prescritPar ?medecin .` | Dr Benali |
| Combien de prescriptions sont enregistrées ? | `compter_prescriptions` | aucune | `SELECT (COUNT(DISTINCT ?prescription) AS ?nombre)` | 4 |
| Le patient Youssef a-t-il une prescription contre-indiquée ? | `verifier_contre_indication` | `:Patient_Youssef` | D06 + `FILTER(?pat = :Patient_Youssef)` | Oui : Presc_003, Advil (ibuprofène) — ulcère actuel et antécédent |
| Quelles sont les données cliniques de Ali ? | `donnees_patient` | `:Patient_Ali` | `?donnee :estDonneeDe :Patient_Ali .` | glycémie 1,92 g/L, clairance 38 mL/min |
| Sara est-elle allergique à l'amoxicilline ? | `verifier_allergie` | `:Patient_Sara`, `:Amoxicilline` | `ASK { ?allergie a :Allergie ; :estDonneeDe :Patient_Sara ; :allergiqueA :Amoxicilline }` | Oui |
| Quels patients ont une clairance de la créatinine inférieure à 60 ? | `seuil_mesure` | « Clairance de la créatinine », seuil `< 60` | `FILTER(?valeur < 60.0)` | Ali Ben Salah : 38 mL/min |

### Scénario de démonstration (environ 5 min)

1. `/scenario?patient=Patient_Youssef` : Youssef (ulcère + antécédent d'ulcère) → Presc_003 → Advil → Ibuprofène →
   CI_UlcereGastrique → Ulcère gastro-duodénal, en rouge ; deux alertes (pathologie actuelle, antécédent).
2. Sara : allergie à l'amoxicilline (donnée clinique) → Presc_002 (Clamoxyl) signalée. Ali : clairance 38 mL/min
   (analyse) + insuffisance rénale → Presc_001 (Glucophage) signalée. Lina : aucun risque.
3. `/donnees-cliniques` : ajouter une allergie de Lina à l'azithromycine → Presc_004 devient une alerte immédiatement.
4. `/prescriptions` : filtre « Renouvelables » → Presc_001 et Presc_004 (catégorie **inférée**) ; filtre de période ;
   créer / modifier / supprimer une ordonnance.
5. `/module-d/assistant` : questions du tableau ci-dessus, puis une faute (« qui a prescri le dolipran ») et une entité
   inconnue (« Patient_F001 »).
6. `/module-d/sparql` : D06, D08, D12 ; montrer qu'un `DELETE` est refusé.
7. « Réinitialiser les données » dans le menu avant et après la démonstration.

### Fichiers du module D

- Back-end : `backend/app/modules/prescription_clinique/` (`common.py`, `queries.py`, `schemas.py`, `service.py`,
  `router.py`, `sparql_guard.py`) ; `backend/nlp/prescrinlu/` ; tests `backend/tests/module_d/`.
- Front-end : `src/pages/Prescriptions.jsx`, `PrescriptionDetail.jsx`, `DonneesCliniques.jsx`, `Scenario.jsx`,
  `AssistantModuleD.jsx`, `SparqlModuleD.jsx` ; `src/app/formsModuleD.jsx`, `AssistantPrescriptions.jsx`, `LayerGraph.jsx`,
  `moduleD.css` ; `src/api/moduleD.js`.
- Enregistrement dans les fichiers communs (minimal) : 2 lignes dans `backend/app/main.py` (routeur) ; routes dans
  `src/App.jsx` ; liens du menu dans `src/app/AppShell.jsx`. Aucun fichier des autres modules n'est modifié.
