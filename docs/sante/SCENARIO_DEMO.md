# Scénario de démonstration (6 à 7 minutes) — Ahmed Allaya

Modules **Pathologie** et **Personne**. Toutes les étapes ont été rejouées via l'API : les chiffres ci-dessous sont les vrais.

## Avant de commencer (2 min avant l'oral)
1. `scripts\start.bat` à la racine (API commune sur :8000, application sur http://localhost:5173), puis menu latéral → section **Pathologie + Personne** (**http://localhost:5173/sante**).
2. Menu latéral → **Réinitialiser les données** (état initial garanti, pour tous les modules).
3. Onglets ouverts : l'application, `http://localhost:8000/docs` (section « Module Pathologie + Personne »), et ce document.
4. Faire une question NLP « à blanc » : le premier appel charge spaCy (~4 s), les suivants prennent environ 20 ms.

## Déroulé

| # | Durée | Action | Ce qu'on voit | Ce qu'on dit |
|---|---|---|---|---|
| 1 | 0:45 | **Tableau santé** | 3 enfants, 8 adultes, 9 aiguës, 10 chroniques, 5 médecins, 3 pharmaciens, **3 alertes** | « Mes deux modules : Pathologie (3 niveaux : aiguë/chronique puis 4 sous-types) et Personne (Patient enfant/adulte, Médecin, Pharmacien). Les données viennent du triplestore, interrogé en SPARQL. Les compteurs aiguës/chroniques incluent les sous-types grâce à `rdf:type/rdfs:subClassOf*`. » |
| 2 | 0:45 | **Pathologies** → filtre « Chroniques » → **+ Nouvelle pathologie** : `Asthme`, type « Maladie chronique (autre) », code `J45.9` | Asthme apparaît dans la liste ; essayer le code `asthme` → refus 422 (format CIM-10) | « Création par un `INSERT DATA` paramétré : URI `:Asthme` générée sans accents, typée `owl:NamedIndividual` + classe. Le texte saisi est échappé : aucune injection SPARQL possible. » |
| 3 | 1:00 | **Personnes → Patients → + Nouveau patient** : Yassine Kefi, 12 ans, M, cocher Asthme + Otite | Fiche de Yassine : badge **Enfant** + **inféré** | « Je n'écris jamais `PatientEnfant` : je stocke `:Patient` + `:age 12`. `PatientEnfant` est une **classe définie** OWL (âge < 18). HermiT la déduit, et l'appli fait la même déduction en SPARQL avec un `FILTER`. C'est le cas de Lina dans l'ontologie de l'équipe. » |
| 4 | 0:45 | **Tableau santé → Alertes** | 3 alertes : Ali/Glucophage (rénale), Sara/Clamoxyl (allergie), Youssef/Advil (ulcère), avec médecin et pharmacien | « Requête d'alerte : patient → prescription → médicament → molécule → contre-indication → pathologie que le patient a, **ou** allergie connue à la molécule. HermiT ne peut pas le faire : la chaîne `estContreIndiquePour` relie le médicament à la pathologie, pas au patient. » |
| 5 | 1:00 | **Personnes → Lina Gharbi** → Ajouter la pathologie « Insuffisance hépatique » | **Bandeau rouge** : Ordonnance 004 — Zithromax, contre-indiqué : insuffisance hépatique ; la ligne de l'ordonnance passe en rouge | « Alerte **déclenchée en direct** : Zithromax contient de l'azithromycine, qui a la contre-indication hépatique. Aucune règle écrite pour Lina : c'est le graphe qui fait le travail. » |
| 6 | 1:30 | **Assistant santé** : (a) « Quels patients souffrent d'asthme ? » (b) « De quoi souffre Yassine Kefi ? » (c) « Combien de patients enfants ? » (d) faute : « médicaments contre-indiqués en cas d'insufisance hépatique » (e) hors sujet : « Quel temps fait-il à Tunis ? » | (a) Yassine ; (b) 2 pathologies ; (c) **4** ; (d) 3 médicaments, entité reconnue par similarité ; (e) refus honnête + suggestions | « spaCy analyse la phrase, les entités de l'ontologie sont reconnues (vocabulaire lu dans le triplestore : l'asthme créé il y a 3 minutes est déjà connu), RapidFuzz corrige la faute, scikit-learn classe l'intention, puis un **gabarit** produit le SPARQL : aucune API de LLM. » Déplier **Étapes du pipeline**, montrer et copier la requête. |
| 7 | 1:00 | Fiche Yassine → **Modifier** : âge 19 | Badge devient **Adulte** | « La classe suit l'âge, sans rien réécrire. » |
|   |   | **Supprimer** Ali Ben Salah | Refus : « lié à une prescription ou à une donnée clinique » + liste des liens | « Avant chaque `DELETE`, un `ASK` vérifie les références. Réponse 409 avec la raison. » |
|   |   | Supprimer la pathologie Asthme | Refus (Yassine en souffre) ; supprimer Yassine puis l'Asthme → OK | « Même contrôle pour une pathologie référencée par un patient, une contre-indication ou un médicament. » |

**Conclusion (15 s)** : « 36 requêtes SPARQL nommées et documentées, 64 tests automatiques (100 avec ceux du module A), NLP évalué à 100 % sur 78 questions de test, et tout s'installe après un `git clone` avec un script. »

## Plan B
- Backend planté : relancer `scripts\start.bat`. Données incohérentes : **Réinitialiser les données** (ou `POST /api/admin/reset` depuis `/docs`).
- Interface inutilisable : tout montrer depuis `http://localhost:8000/docs` (Try it out), avec les mêmes étapes.
- Rien ne marche : `docs/sante/SPARQL.md` (requêtes et vrais résultats), `docs/sante/NLP.md`, et la sortie de `backend\tools\eval_nlp_sante.py` et `backend\tools\validate_ontology.py`.
- Prévoir des captures d'écran des étapes 1, 3, 5 et 6 dans `docs/sante/captures/` (à prendre la veille).
