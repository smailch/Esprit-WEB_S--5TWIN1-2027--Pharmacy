# Ontologie PharmaSémantique v2

Thème : **molécules, effets secondaires, contre-indications et données cliniques**.

| Fichier | Rôle |
|---|---|
| `pharma.ttl` | Source lisible (Turtle) — à éditer |
| `pharma.owl` | Même ontologie en RDF/XML — à ouvrir dans Protégé (OntoGraf, HermiT) |
| `requetes.sparql` | Requêtes testées : RDFS, filtres, recherche, raisonnement, agrégation, CRUD |

URI de base : `http://example.org/pharma#` (préfixe `:`). URI sans accents ; libellés accentués dans `rdfs:label`.

## 8 modules (classes) — 3 niveaux chacun

| Membre | Module | Niveau 2 | Niveau 3 |
|---|---|---|---|
| A | Molecule | Antibiotique / Antalgique | Penicilline, Macrolide / AntalgiqueNonOpioide, AntalgiqueOpioide |
| A | Medicament | Princeps / Generique | …SurOrdonnance, …SansOrdonnance |
| B | EffetSecondaire | EffetLeger / EffetGrave | EffetLegerDigestif, EffetLegerCutane / EffetGraveDigestif, EffetGraveNeurologique |
| B | ContreIndication | ContreIndicationAbsolue / ContreIndicationRelative | Allergique, Digestive / Renale, Hepatique |
| C | Pathologie | MaladieAigue / MaladieChronique | InfectionAigue, DouleurAigue / MaladieMetabolique, InsuffisanceOrgane |
| C | DonneeClinique | ExamenClinique / HistoriqueMedical | SigneVital, AnalyseBiologique / Allergie, Antecedent |
| D | Personne | Patient / ProfessionnelSante | PatientEnfant, PatientAdulte / Medecin, Pharmacien |
| D | Prescription | PrescriptionSimple / PrescriptionRenouvelable | PrescriptionNormale, PrescriptionUrgente / RenouvellementCourt, RenouvellementLong |

L'ancien module « Administration » (formes/voies) est supprimé : la forme devient l'attribut `formeGalenique` du médicament, et le 8ᵉ module est **DonneeClinique** (exigé par le thème).

## Logique appliquée
- **RDF** : triplets, individus typés (`rdf:type`), littéraux typés `xsd:`.
- **RDFS** : `subClassOf` (3 niveaux), `domain`/`range` sur chaque propriété, `label`/`comment`.
- **OWL** :
  - disjonctions (`AllDisjointClasses` des 8 modules + `disjointWith` entre sœurs) ;
  - propriétés inverses (`contientMolecule`/`estContenuDans`, `peutProvoquer`/`estProvoquePar`, `prescritPar`/`aPrescrit`…) ;
  - propriétés fonctionnelles (`age`, `codeATC`, `prescritPar`…) et symétrique (`interagitAvec`) ;
  - chaîne de propriétés : `contientMolecule ∘ aContreIndication ∘ concernePathologie ⇒ estContreIndiquePour` ;
  - classes définies (`equivalentClass`) : `PatientEnfant` (âge < 18), `EffetGrave` (gravité = "grave"), `ContreIndicationAbsolue`, `GeneriqueSurOrdonnance`, `PrescriptionRenouvelable`… ;
  - restrictions : tout médicament contient ≥ 1 molécule ; une prescription a exactement 1 médecin et 1 patient ; toute pénicilline a la contre-indication « allergie aux pénicillines ».
- **SPARQL** : voir `requetes.sparql` (Q6 détecte les 3 prescriptions dangereuses du scénario).

## Scénario de démonstration
- Sara (9 ans, allergique à l'amoxicilline) reçoit du Clamoxyl → alerte allergie.
- Youssef (ulcère) reçoit de l'Advil (ibuprofène) → alerte contre-indication digestive.
- Ali (insuffisance rénale, clairance 38 mL/min) reçoit du Glucophage → alerte rénale.
- Lina n'est typée que `Patient` : HermiT la classe automatiquement en `PatientAdulte` (âge 31).
