"""Étape 4 — Génération SPARQL par gabarits.

Chaque intention possède un gabarit rempli avec les URI des entités reconnues et les filtres extraits.
Aucun texte libre n'est généré : la requête produite est toujours syntaxiquement valide.
Chaque fonction renvoie (sparql, explication[], formateur_de_reponse).
"""
from __future__ import annotations

from rdflib import Literal
from rdflib.namespace import XSD

INTENT_LABELS = {
    "lister_molecules_classe": "Lister les molécules d'une classe",
    "lister_medicaments_filtre": "Lister / filtrer les médicaments",
    "medicaments_contenant": "Médicaments contenant une molécule",
    "molecules_de_medicament": "Composition d'un médicament",
    "effets_secondaires": "Effets secondaires",
    "contre_indications": "Contre-indications",
    "contre_indiques_pour_pathologie": "Médicaments contre-indiqués pour une pathologie",
    "generique_alternative": "Alternative / générique moins cher",
    "interaction": "Interactions médicamenteuses",
    "info_attribut": "Attribut d'un médicament ou d'une molécule",
    "indication": "Indications thérapeutiques",
    "statistiques": "Statistiques",
}

ATTR_LABELS = {"prixDT": "prix", "codeATC": "code ATC", "doseMaxJourMg": "dose maximale par jour", "dosage": "dosage", "formeGalenique": "forme galénique", "surOrdonnance": "délivrance sur ordonnance"}


class MissingEntity(Exception):
    """L'intention est comprise mais une entité indispensable manque."""


def dec(v: float) -> str:
    return Literal(float(v), datatype=XSD.decimal).n3()


def first(ents, *types):
    return next((e for e in ents if e.type in types), None)


def fmt_prix(v):
    return f"{v:.2f}".replace(".", ",") + " DT" if isinstance(v, (int, float)) else "—"


def liste(values, max_n=6):
    values = list(dict.fromkeys(values))
    if not values:
        return ""
    if len(values) > max_n:
        return ", ".join(values[:max_n]) + f" et {len(values) - max_n} autre(s)"
    return values[0] if len(values) == 1 else ", ".join(values[:-1]) + " et " + values[-1]


# ---------------------------------------------------------------------------
def lister_molecules_classe(ents, slots):
    c = first(ents, "Classe")
    classe = c.id if c else "Molecule"
    sparql = f"""SELECT ?molecule ?label ?codeATC WHERE {{
  ?molecule a :{classe} ; rdfs:label ?label .
  OPTIONAL {{ ?molecule :codeATC ?codeATC }}
}} ORDER BY ?label"""
    expl = [f"Classe ciblée : :{classe} (les sous-classes sont incluses grâce à l'inférence rdfs:subClassOf)."]
    nom = c.texte if c else "molécules"
    return sparql, expl, lambda rows: (f"{len(rows)} molécule(s) de la classe « {nom} » : {liste([r['label'] for r in rows])}." if rows else f"Aucune molécule dans la classe « {nom} ».")


def lister_medicaments_filtre(ents, slots):
    where = ["?medicament a :Medicament ; rdfs:label ?label ; :prixDT ?prix ; :surOrdonnance ?ordonnance ."]
    expl = []
    if slots.get("type"):
        where.append(f"?medicament a :{slots['type']} .")
        expl.append(f"Type : :{slots['type']}")
    if "ordonnance" in slots:
        where.append(f"FILTER(?ordonnance = {'true' if slots['ordonnance'] else 'false'})")
        expl.append("Délivrance " + ("sur" if slots["ordonnance"] else "sans") + " ordonnance (FILTER booléen)")
    if slots.get("forme"):
        where.append(f'?medicament :formeGalenique ?forme . FILTER(STR(?forme) = "{slots["forme"]}")')
        expl.append(f"Forme galénique = {slots['forme']}")
    if "prixMax" in slots:
        where.append(f"FILTER(?prix <= {dec(slots['prixMax'])})")
        expl.append(f"Prix ≤ {slots['prixMax']} DT (FILTER numérique)")
    if "prixMin" in slots:
        where.append(f"FILTER(?prix >= {dec(slots['prixMin'])})")
        expl.append(f"Prix ≥ {slots['prixMin']} DT (FILTER numérique)")
    mol = first(ents, "Molecule")
    if mol:
        where.append(f"?medicament :contientMolecule :{mol.id} .")
        expl.append(f"Contient la molécule :{mol.id}")
    order, limit = "?prix", ""
    if slots.get("superlatif") == "max":
        order, limit = "DESC(?prix)", "\nLIMIT 1"
        expl.append("Le plus cher : ORDER BY DESC + LIMIT 1")
    elif slots.get("superlatif") == "min":
        limit = "\nLIMIT 1"
        expl.append("Le moins cher : ORDER BY + LIMIT 1")
    body = "\n  ".join(where)
    sparql = f"SELECT ?medicament ?label ?prix ?ordonnance WHERE {{\n  {body}\n}} ORDER BY {order}{limit}"
    if not expl:
        expl.append("Aucun filtre : tous les médicaments, triés par prix.")

    def answer(rows):
        if not rows:
            return "Aucun médicament ne correspond à ces critères."
        if limit:
            r = rows[0]
            return f"{r['label']} : {fmt_prix(r['prix'])}."
        return f"{len(rows)} médicament(s) trouvé(s) : " + liste([f"{r['label']} ({fmt_prix(r['prix'])})" for r in rows]) + "."
    return sparql, expl, answer


def medicaments_contenant(ents, slots):
    mol = first(ents, "Molecule")
    if not mol:
        raise MissingEntity("Précisez la molécule (ex. : « quels médicaments contiennent du paracétamol ? »).")
    sparql = f"""SELECT ?medicament ?label ?prix WHERE {{
  :{mol.id} :estContenuDans ?medicament .
  ?medicament rdfs:label ?label .
  OPTIONAL {{ ?medicament :prixDT ?prix }}
}} ORDER BY ?prix"""
    expl = [f"Propriété inverse :estContenuDans (inférée depuis :contientMolecule) appliquée à :{mol.id}."]
    return sparql, expl, lambda rows: (f"{mol.label} se trouve dans : {liste([r['label'] for r in rows])}." if rows else f"Aucun médicament ne contient {mol.label}.")


def molecules_de_medicament(ents, slots):
    med = first(ents, "Medicament")
    if not med:
        raise MissingEntity("Précisez le médicament (ex. : « que contient le Doliprane ? »).")
    sparql = f"""SELECT ?molecule ?label ?codeATC WHERE {{
  :{med.id} :contientMolecule ?molecule .
  ?molecule rdfs:label ?label .
  OPTIONAL {{ ?molecule :codeATC ?codeATC }}
}}"""
    return sparql, [f"Propriété :contientMolecule de :{med.id}."], lambda rows: f"{med.label} contient : {liste([r['label'] for r in rows])}."


def effets_secondaires(ents, slots):
    e = first(ents, "Medicament", "Molecule")
    if not e:
        raise MissingEntity("Précisez le médicament ou la molécule (ex. : « effets secondaires de l'Advil »).")
    path = f":{e.id} :contientMolecule/:peutProvoquer ?effet ." if e.type == "Medicament" else f":{e.id} :peutProvoquer ?effet ."
    filt = f'\n  FILTER(?gravite = "{slots["gravite"]}")' if slots.get("gravite") else ""
    sparql = f"""SELECT DISTINCT ?effet ?label ?gravite ?frequence WHERE {{
  {path}
  ?effet rdfs:label ?label ; :niveauGravite ?gravite .
  OPTIONAL {{ ?effet :frequence ?frequence }}{filt}
}} ORDER BY ?gravite ?label"""
    expl = ["Chemin de propriétés :contientMolecule/:peutProvoquer (médicament → molécule → effet)." if e.type == "Medicament" else "Propriété :peutProvoquer de la molécule."]
    if slots.get("gravite"):
        expl.append(f"Filtre sur la gravité = {slots['gravite']}")
    qual = f" {slots['gravite']}s" if slots.get("gravite") == "grave" else ""
    return sparql, expl, lambda rows: (f"Effets secondaires{qual} de {e.label} : " + liste([f"{r['label']} ({r['gravite']})" for r in rows]) + "." if rows else f"Aucun effet secondaire{qual} connu pour {e.label}.")


def contre_indications(ents, slots):
    e = first(ents, "Medicament", "Molecule")
    if not e:
        raise MissingEntity("Précisez le médicament ou la molécule (ex. : « contre-indications de l'aspirine »).")
    path = f":{e.id} :contientMolecule/:aContreIndication ?ci ." if e.type == "Medicament" else f":{e.id} :aContreIndication ?ci ."
    sparql = f"""SELECT DISTINCT ?ci ?label ?risque ?pathologie WHERE {{
  {path}
  ?ci rdfs:label ?label .
  OPTIONAL {{ ?ci :niveauRisque ?risque }}
  OPTIONAL {{ ?ci :concernePathologie ?p . ?p rdfs:label ?pathologie }}
}}"""
    expl = ["Chemin :contientMolecule/:aContreIndication (médicament → molécule → contre-indication)." if e.type == "Medicament" else "Propriété :aContreIndication de la molécule."]
    return sparql, expl, lambda rows: (f"Contre-indications de {e.label} : " + liste([f"{r['label']} ({r['risque']})" for r in rows]) + "." if rows else f"Aucune contre-indication connue pour {e.label}.")


def contre_indiques_pour_pathologie(ents, slots):
    p = first(ents, "Pathologie")
    if not p:
        raise MissingEntity("Précisez la pathologie (ex. : « médicaments à éviter en cas d'ulcère »).")
    sparql = f"""SELECT DISTINCT ?medicament ?label ?prix WHERE {{
  ?medicament :estContreIndiquePour :{p.id} ; rdfs:label ?label .
  OPTIONAL {{ ?medicament :prixDT ?prix }}
}} ORDER BY ?label"""
    expl = [f"Propriété :estContreIndiquePour, INFÉRÉE par le raisonneur via la chaîne OWL contientMolecule ∘ aContreIndication ∘ concernePathologie (pathologie :{p.id})."]
    return sparql, expl, lambda rows: (f"En cas de {p.label.lower()}, à éviter : {liste([r['label'] for r in rows])}." if rows else f"Aucun médicament n'est contre-indiqué pour {p.label.lower()} dans l'ontologie.")


def generique_alternative(ents, slots):
    med = first(ents, "Medicament")
    if not med:
        raise MissingEntity("Précisez le médicament (ex. : « générique moins cher que l'Advil »).")
    sparql = f"""SELECT DISTINCT ?alternative ?label ?type ?prix ?economie WHERE {{
  :{med.id} :contientMolecule ?mol ; :prixDT ?prixReference .
  ?alternative :contientMolecule ?mol ; :prixDT ?prix ; rdfs:label ?label .
  FILTER(?alternative != :{med.id})
  FILTER NOT EXISTS {{ ?alternative :contientMolecule ?autre . FILTER NOT EXISTS {{ :{med.id} :contientMolecule ?autre }} }}
  OPTIONAL {{ ?alternative a ?type . VALUES ?type {{ :Princeps :Generique }} }}
  BIND(?prixReference - ?prix AS ?economie)
}} ORDER BY ?prix"""
    expl = ["Même composition : mêmes molécules et aucune en plus (double FILTER NOT EXISTS).", "Économie calculée dans la requête (BIND)."]

    def answer(rows):
        cheaper = [r for r in rows if (r["economie"] or 0) > 0]
        if cheaper:
            b = max(cheaper, key=lambda r: r["economie"])
            return f"Oui : {b['label']} ({fmt_prix(b['prix'])}) a la même composition que {med.label}, soit {fmt_prix(b['economie'])} d'économie."
        if rows:
            return f"Il existe {liste([r['label'] for r in rows])}, mais pas moins cher que {med.label}."
        return f"Aucun autre médicament n'a la même composition que {med.label}."
    return sparql, expl, answer


def interaction(ents, slots):
    items = [e for e in ents if e.type in ("Medicament", "Molecule")]
    items = list({(e.type, e.id): e for e in items}.values())
    if not items:
        raise MissingEntity("Précisez au moins un médicament ou une molécule (ex. : « Advil et Aspégic interagissent-ils ? »).")

    def mols(e, var):
        return f":{e.id} :contientMolecule {var} ." if e.type == "Medicament" else f"BIND(:{e.id} AS {var})"

    if len(items) >= 2:
        a, b = items[0], items[1]
        sparql = f"""SELECT DISTINCT ?moleculeA ?moleculeB WHERE {{
  {mols(a, '?ma')}
  {mols(b, '?mb')}
  ?ma :interagitAvec ?mb .
  ?ma rdfs:label ?moleculeA . ?mb rdfs:label ?moleculeB .
}}"""
        expl = ["Propriété SYMÉTRIQUE :interagitAvec : une interaction déclarée dans un sens est déduite dans l'autre."]
        return sparql, expl, lambda rows: (f"Attention : {a.label} et {b.label} interagissent ({rows[0]['moleculeA']} ↔ {rows[0]['moleculeB']})." if rows else f"Aucune interaction connue entre {a.label} et {b.label} dans l'ontologie.")
    a = items[0]
    sparql = f"""SELECT DISTINCT ?molecule ?label WHERE {{
  {mols(a, '?ma')}
  ?ma :interagitAvec ?molecule .
  ?molecule rdfs:label ?label .
}}"""
    return sparql, ["Propriété symétrique :interagitAvec."], lambda rows: (f"{a.label} interagit avec : {liste([r['label'] for r in rows])}." if rows else f"Aucune interaction connue pour {a.label}.")


def info_attribut(ents, slots):
    e = first(ents, "Medicament", "Molecule")
    if not e:
        raise MissingEntity("Précisez le médicament ou la molécule (ex. : « prix du Zithromax »).")
    attr = slots.get("attribut")
    if e.type == "Molecule" and attr not in (None, "codeATC", "doseMaxJourMg"):
        attr = None
    if e.type == "Medicament" and attr in ("codeATC", "doseMaxJourMg"):
        sparql = f"""SELECT ?molecule ?valeur WHERE {{
  :{e.id} :contientMolecule ?m . ?m rdfs:label ?molecule ; :{attr} ?valeur .
}}"""
        return sparql, [f"Attribut :{attr} porté par la molécule (via :contientMolecule)."], lambda rows: f"{ATTR_LABELS[attr].capitalize()} de {e.label} : " + liste([f"{r['molecule']} → {r['valeur']}" for r in rows]) + "."
    if attr == "surOrdonnance":
        sparql = f"ASK {{ :{e.id} :surOrdonnance true }}"
        return sparql, ["Requête ASK : réponse oui / non."], lambda res: f"{e.label} est {'délivré sur ordonnance' if res else 'disponible sans ordonnance'}."
    if attr:
        sparql = f"SELECT ?valeur WHERE {{ :{e.id} :{attr} ?valeur }}"

        def answer(rows):
            if not rows:
                return f"Le {ATTR_LABELS[attr]} de {e.label} n'est pas renseigné."
            v = rows[0]["valeur"]
            v = fmt_prix(v) if attr == "prixDT" else f"{v} mg" if attr == "doseMaxJourMg" else v
            return f"{ATTR_LABELS[attr].capitalize()} de {e.label} : {v}."
        return sparql, [f"Lecture de la propriété de données :{attr}."], answer
    props = ":codeATC :doseMaxJourMg" if e.type == "Molecule" else ":nomCommercial :dosage :formeGalenique :surOrdonnance :prixDT"
    sparql = f"""SELECT ?propriete ?valeur WHERE {{
  VALUES ?p {{ {props} }}
  :{e.id} ?p ?valeur .
  BIND(STRAFTER(STR(?p), "#") AS ?propriete)
}}"""
    return sparql, ["Toutes les propriétés de données de la ressource (VALUES)."], lambda rows: f"Fiche de {e.label} : " + "; ".join(f"{r['propriete']} = {r['valeur']}" for r in rows) + "."


def indication(ents, slots):
    med = first(ents, "Medicament")
    if med:
        sparql = f"""SELECT ?pathologie ?label WHERE {{
  :{med.id} :estIndiquePour ?pathologie . ?pathologie rdfs:label ?label .
}}"""
        return sparql, [f"Propriété :estIndiquePour de :{med.id}."], lambda rows: (f"{med.label} est indiqué pour : {liste([r['label'] for r in rows])}." if rows else f"Aucune indication renseignée pour {med.label}.")
    p = first(ents, "Pathologie")
    if not p:
        raise MissingEntity("Précisez un médicament ou une pathologie (ex. : « quel médicament pour la migraine ? »).")
    sparql = f"""SELECT ?medicament ?label ?prix WHERE {{
  ?medicament :estIndiquePour :{p.id} ; rdfs:label ?label .
  OPTIONAL {{ ?medicament :prixDT ?prix }}
  FILTER NOT EXISTS {{ ?medicament :estContreIndiquePour :{p.id} }}
}} ORDER BY ?prix"""
    expl = [f"Médicaments :estIndiquePour :{p.id}, en excluant ceux contre-indiqués pour cette même pathologie (FILTER NOT EXISTS)."]
    return sparql, expl, lambda rows: (f"Pour {p.label.lower()} : " + liste([f"{r['label']} ({fmt_prix(r['prix'])})" for r in rows]) + "." if rows else f"Aucun médicament indiqué pour {p.label.lower()} dans l'ontologie.")


def statistiques(ents, slots):
    c = first(ents, "Classe")
    if c and c.id != "Molecule":
        sparql = f"SELECT (COUNT(DISTINCT ?m) AS ?nombre) WHERE {{ ?m a :{c.id} }}"
        return sparql, [f"COUNT des individus de la classe :{c.id} (sous-classes incluses par inférence)."], lambda rows: f"L'ontologie compte {rows[0]['nombre']} molécule(s) de type « {c.texte} »."
    if c and c.id == "Molecule" and not slots.get("type"):
        sparql = "SELECT (COUNT(DISTINCT ?m) AS ?nombre) WHERE { ?m a :Molecule }"
        return sparql, ["COUNT des individus de :Molecule."], lambda rows: f"L'ontologie compte {rows[0]['nombre']} molécules."
    where = ["?med a :Medicament ; :prixDT ?prix ."]
    expl = []
    if slots.get("type"):
        where.append(f"?med a :{slots['type']} .")
        expl.append(f"Type :{slots['type']}")
    if "ordonnance" in slots:
        where.append(f"?med :surOrdonnance {'true' if slots['ordonnance'] else 'false'} .")
        expl.append("Délivrance " + ("sur" if slots["ordonnance"] else "sans") + " ordonnance")
    body = "\n  ".join(where)
    sparql = f"""SELECT (COUNT(DISTINCT ?med) AS ?nombre) (AVG(?prix) AS ?prixMoyen) (MIN(?prix) AS ?prixMin) (MAX(?prix) AS ?prixMax) WHERE {{
  {body}
}}"""
    expl.append("Agrégats COUNT, AVG, MIN, MAX.")
    quoi = {"Generique": "génériques", "Princeps": "princeps"}.get(slots.get("type"), "médicaments")

    def answer(rows):
        r = rows[0]
        if not r["nombre"]:
            return f"Aucun {quoi[:-1]} ne correspond."
        return f"{r['nombre']} {quoi} ; prix moyen {fmt_prix(r['prixMoyen'])} (de {fmt_prix(r['prixMin'])} à {fmt_prix(r['prixMax'])})."
    return sparql, expl, answer


GENERATORS = {name: globals()[name] for name in INTENT_LABELS}
