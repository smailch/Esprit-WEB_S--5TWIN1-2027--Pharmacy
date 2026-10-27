# Fiche de présentation — Module A : Molécule + Médicament

**Chemlali Ismail — NeoCoders, 5 TWIN 2026/2027.** À relire avant la validation.

## 1. Ce que couvre mon module, critère par critère

| Critère (points) | Ce que je montre | Où |
|---|---|---|
| Requêtes SPARQL (4) | 16 requêtes nommées : chemins `subClassOf+`, `rdf:type/rdfs:subClassOf*`, FILTER numérique/booléen/REGEX, UNION, OPTIONAL, BIND, agrégats COUNT/AVG/MIN/MAX + GROUP BY + HAVING, FILTER NOT EXISTS, ASK, CONSTRUCT, GRAPH nommés, CRUD INSERT DATA / DELETE-INSERT WHERE / DELETE WHERE | Console SPARQL ; panneau « Requêtes SPARQL exécutées » sur chaque page |
| Individus (2) | 8 molécules, 9 médicaments ; CRUD complet avec validation (≥ 1 molécule, refus de supprimer une molécule utilisée ou un médicament prescrit) | Pages Molécules / Médicaments |
| Scénario (2) | démo de 5 min ci-dessous | — |
| API IA (4) | PharmaNLU-A : spaCy + scikit-learn + RapidFuzz, **sans LLM**, 96,9 % sur 96 questions de test | Page Assistant → « À propos du modèle » |
| Interfaces (3) | 6 pages + site vitrine, responsive, filtres, formulaires, graphe, export CSV | `/molecules`… |
| Communication BE↔FE (3) | API REST FastAPI (JSON), proxy Vite, chaque réponse renvoie ses requêtes SPARQL | http://localhost:8000/docs |
| Valeur ajoutée (2) | comparateur générique, vérificateur d'interactions, IA explicable, faits inférés visibles | Comparateur, Interactions, badges « inféré » |

## 2. Outils NLP utilisés (à citer explicitement — consigne de la prof)

- **spaCy 3.8** + modèle **fr_core_news_sm** : tokenisation, lemmatisation, **EntityRuler** (reconnaissance d'entités par dictionnaire).
- **scikit-learn 1.9** : **TF-IDF** (mots 1–2-grammes + caractères 3–5-grammes) + **régression logistique** multinomiale → intention + probabilité (confiance).
- **RapidFuzz 3.14** : correction des fautes de frappe (similarité de Levenshtein).
- **rdflib 7.6** : exécution de la requête SPARQL générée.
- **Aucune API de LLM** (ni OpenAI, ni Gemini…) : tout tourne en local, le modèle fait 253 Ko.

## 3. Comment marche PharmaNLU-A (à expliquer en 1 minute)

1. **Normalisation** (spaCy) : « Quels médicaments contiennent de l'ibuprophène ? » → `quels medicaments contiennent de l' ibuprophene`.
2. **Entités** : EntityRuler cherche les noms de l'ontologie ; « ibuprophene » n'existe pas → RapidFuzz trouve **Ibuprofène** (86 %).
   Le dictionnaire est **généré depuis l'ontologie** : un médicament ajouté par le CRUD est reconnu immédiatement.
3. **Délexicalisation** : `quel medicament contenir de le xmol` — le classifieur apprend la *forme* de la question, pas les noms.
4. **Intention** : régression logistique → `medicaments_contenant` (97 %). Sous 40 % de confiance, on ne génère pas de requête.
5. **Gabarit SPARQL** rempli avec l'URI `:Ibuprofene` → exécution → réponse en français + requête affichée et expliquée.

Données : 314 questions d'entraînement (gabarits écrits à la main, remplis avec les noms de l'ontologie) ; 96 questions de test écrites séparément, avec fautes et formulations différentes.
Résultats : **96,9 % d'intentions correctes, F1 macro 0,969, 100 % d'entités reconnues**. Les 3 erreurs restantes sont assumées (ex. « CI de l'azithromycine » : abréviation inconnue).

## 4. Scénario de démonstration (≈ 5 min)

1. Accueil (site vitrine) → **Ouvrir l'application**. Montrer « API connectée · N triplets déclarés · M inférés ».
2. **Assistant** : taper « quels médicaments contiennent de l'ibuprophene » (faute volontaire) → Advil + Ibuprofène Mylan ; montrer intention, confiance, entité « corrigé 86 % », requête SPARQL générée.
3. **Comparateur** : Advil 6,50 DT → Ibuprofène Mylan 3,90 DT = **−40 %**.
4. **Interactions** : Advil + Aspégic → interaction ibuprofène ↔ aspirine. Expliquer : déclarée **une seule fois** (Ibuprofène → Aspirine), l'autre sens est **déduit** car `interagitAvec` est symétrique. Ajouter Ibuprofène Mylan → alerte « doublon de principe actif ».
5. **CRUD** : Médicaments → Nouveau → « Paracétamol Biogaran », Générique, 500 mg, sans ordonnance, 2,10 DT, Paracétamol. La fiche affiche **Générique sans ordonnance — inféré** (classe définie `owl:equivalentClass`).
   Retour à l'Assistant : « que contient le paracetamol biogaran » → reconnu sans ré-entraînement.
6. **Console SPARQL** : Q08 (chaîne de propriétés), Q10 (agrégats + HAVING), Q11 (NOT EXISTS → Codéine), Q15 (types inférés).
7. Bouton **Réinitialiser les données**.

## 5. Questions probables du jury

- **Pourquoi pas un LLM ?** Interdit par la consigne ; et un modèle à gabarits produit toujours une requête valide et explicable.
- **Que se passe-t-il si la question est hors sujet ?** Confiance < 40 % → « je n'ai pas compris » + suggestions ; si une entité manque → message précis (« Précisez le médicament… »).
- **Comment le modèle reconnaît un nouveau médicament ?** Le dictionnaire d'entités est reconstruit depuis le graphe à chaque modification (compteur de version).
- **Comment est faite l'inférence ?** owlrl (OWL 2 RL) calcule la fermeture déductive dans un graphe nommé séparé `urn:pharma:inferred` ; HermiT reste l'outil de validation dans Protégé.
- **Où sont les données modifiées ?** `backend/data/runtime.ttl` ; l'ontologie de l'équipe `pharma.ttl` n'est jamais modifiée.
- **Sécurité ?** Les paramètres sont sérialisés en termes RDF échappés (pas de concaténation brute), identifiants validés par regex, console en lecture seule.
- **Reproductibilité ?** Graine 42, versions épinglées, `python -m nlp.train` régénère le modèle et la carte du modèle ; 36 tests pytest.
