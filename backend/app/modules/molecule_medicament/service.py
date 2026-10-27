"""Logique métier du module A. Toute lecture/écriture passe par SPARQL.

Chaque fonction reçoit un `Trace` qui enregistre les requêtes exécutées :
l'API les renvoie au front-end pour les afficher (transparence / démo).
"""
from __future__ import annotations

import re
import unicodedata

from ...graph_store import store, PH, RDF
from . import queries as Q
from .queries import lit, render, uri


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class Trace:
    def __init__(self):
        self.items: list[dict] = []

    def _log(self, titre, sparql):
        self.items.append({"titre": titre, "requete": sparql})

    def select(self, titre, sparql):
        self._log(titre, sparql)
        return store.select(sparql)

    def ask(self, titre, sparql):
        self._log(titre, sparql)
        return store.ask(sparql)

    def construct(self, titre, sparql):
        self._log(titre, sparql)
        return store.construct(sparql)

    def update(self, titre, sparql):
        self._log(titre, sparql)
        store.update(sparql)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def make_id(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", strip_accents(text))
    ident = "".join(w[:1].upper() + w[1:] for w in words)
    if not ident or not ident[0].isalpha():
        ident = "X" + ident
    return ident


def _require(local_id: str, cls: str):
    uri(local_id)  # valide le format
    if not store.exists(local_id, cls):
        raise NotFound(f"{cls} introuvable : {local_id}")


def _declared_class(local_id: str, allowed: list[str]) -> str | None:
    for o in store.base.objects(PH[local_id], RDF.type):
        name = str(o).rsplit("#", 1)[-1]
        if name in allowed:
            return name
    return None


def _declared(subject: str, predicate, obj: str) -> bool:
    """Vrai si le triplet est déclaré dans le graphe de base (sinon il vient du raisonneur)."""
    return (PH[subject], predicate, PH[obj]) in store.base


def _split(value) -> list[str]:
    return [v for v in (value or "").split("|") if v]


# ===========================================================================
#  Molécules
# ===========================================================================
LEAF_MOLECULE_CLASSES = Q.MOLECULE_CLASSES


def list_molecules(t: Trace, classe=None, q=None, atc=None, tri="label"):
    filters = []
    params = {}
    if classe:
        if classe not in Q.MOLECULE_CLASSES:
            raise ValueError("Classe inconnue")
        filters.append("?m a {{classe}} .")
        params["classe"] = uri(classe)
    if q:
        filters.append('FILTER(REGEX(STR(?label), {{motif}}, "i") || REGEX(STRAFTER(STR(?m), "#"), {{motifSansAccent}}, "i"))')
        params["motif"] = lit(re.escape(q))
        params["motifSansAccent"] = lit(re.escape(strip_accents(q)))
    if atc:
        filters.append('FILTER(STRSTARTS(?atc, {{atc}}))')
        params["atc"] = lit(atc.upper())
    order = {"label": "?label", "dose": "DESC(?dose)", "atc": "?atc", "medicaments": "DESC(?nbMedicaments)"}.get(tri, "?label")
    sparql = render("""
SELECT ?m ?label ?atc ?dose (COUNT(DISTINCT ?med) AS ?nbMedicaments) (GROUP_CONCAT(DISTINCT ?medLabel; separator="|") AS ?medicaments) WHERE {
  ?m a :Molecule ; rdfs:label ?label .
  OPTIONAL { ?m :codeATC ?atc }
  OPTIONAL { ?m :doseMaxJourMg ?dose }
  OPTIONAL { ?med :contientMolecule ?m ; rdfs:label ?medLabel }
  """ + "\n  ".join(filters) + """
} GROUP BY ?m ?label ?atc ?dose ORDER BY """ + order, **params)
    rows = t.select("Liste des molécules (filtres)", sparql)
    return [{
        "id": r["m"], "label": r["label"], "classe": _declared_class(r["m"], Q.MOLECULE_CLASSES),
        "codeATC": r["atc"], "doseMaxJourMg": r["dose"], "nbMedicaments": r["nbMedicaments"],
        "medicaments": _split(r["medicaments"]),
    } for r in rows]


def get_molecule(t: Trace, mid: str):
    _require(mid, "Molecule")
    m = uri(mid)
    info = t.select("Attributs de la molécule", render("""
SELECT ?label ?atc ?dose WHERE {
  {{m}} rdfs:label ?label .
  OPTIONAL { {{m}} :codeATC ?atc } OPTIONAL { {{m}} :doseMaxJourMg ?dose }
}""", m=m))[0]
    types = t.select("Classes déclarées et inférées", render("""
SELECT ?classe ?label WHERE {
  {{m}} rdf:type ?classe . ?classe rdfs:subClassOf* :Molecule ; rdfs:label ?label .
}""", m=m))
    meds = t.select("Médicaments qui la contiennent (propriété inverse)", render("""
SELECT ?id ?label ?prix WHERE { {{m}} :estContenuDans ?id . ?id rdfs:label ?label . OPTIONAL { ?id :prixDT ?prix } } ORDER BY ?prix""", m=m))
    effets = t.select("Effets secondaires", render("""
SELECT ?id ?label ?gravite ?frequence WHERE {
  {{m}} :peutProvoquer ?id . ?id rdfs:label ?label .
  OPTIONAL { ?id :niveauGravite ?gravite } OPTIONAL { ?id :frequence ?frequence }
} ORDER BY ?label""", m=m))
    cis = t.select("Contre-indications", render("""
SELECT ?id ?label ?risque ?pathologie WHERE {
  {{m}} :aContreIndication ?id . ?id rdfs:label ?label .
  OPTIONAL { ?id :niveauRisque ?risque }
  OPTIONAL { ?id :concernePathologie ?p . ?p rdfs:label ?pathologie }
}""", m=m))
    inter = t.select("Interactions (propriété symétrique)", render("""
SELECT ?id ?label WHERE {
  {{m}} :interagitAvec ?id . ?id rdfs:label ?label .
}""", m=m))
    return {
        "id": mid, "label": info["label"], "codeATC": info["atc"], "doseMaxJourMg": info["dose"],
        "classe": _declared_class(mid, Q.MOLECULE_CLASSES),
        "classes": [{"id": r["classe"], "label": r["label"], "inferee": not _declared(mid, RDF.type, r["classe"])} for r in types],
        "medicaments": meds, "effets": effets, "contreIndications": cis,
        "interactions": [{"id": r["id"], "label": r["label"], "inferee": not _declared(mid, PH.interagitAvec, r["id"])} for r in inter],
    }


def _molecule_triples(mid: str, data) -> str:
    m = uri(mid)
    lines = [f"{m} a owl:NamedIndividual , {uri(data.classe)} ; rdfs:label {lit(data.nom, lang='fr')} ."]
    if data.codeATC:
        lines.append(f"{m} :codeATC {lit(data.codeATC)} .")
    if data.doseMaxJourMg is not None:
        lines.append(f"{m} :doseMaxJourMg {lit(float(data.doseMaxJourMg))} .")
    for e in data.effets:
        lines.append(f"{m} :peutProvoquer {uri(e)} .")
    for c in data.contreIndications:
        lines.append(f"{m} :aContreIndication {uri(c)} .")
    for i in data.interactions:
        lines.append(f"{m} :interagitAvec {uri(i)} .")
    return "\n  ".join(lines)


def _check_refs(data):
    for e in data.effets:
        _require(e, "EffetSecondaire")
    for c in data.contreIndications:
        _require(c, "ContreIndication")
    for i in data.interactions:
        _require(i, "Molecule")


MOLECULE_OWNED = ":codeATC :doseMaxJourMg :peutProvoquer :aContreIndication :interagitAvec rdfs:label rdf:type"


def create_molecule(t: Trace, data):
    mid = make_id(data.nom)
    if store.exists(mid):
        raise Conflict(f"La ressource {mid} existe déjà")
    _check_refs(data)
    t.update("Création (INSERT DATA)", f"INSERT DATA {{\n  {_molecule_triples(mid, data)}\n}}")
    return get_molecule(t, mid)


def update_molecule(t: Trace, mid: str, data):
    _require(mid, "Molecule")
    _check_refs(data)
    m = uri(mid)
    t.update("Modification (DELETE / INSERT WHERE)", f"""DELETE {{ {m} ?p ?o }}
INSERT {{
  {_molecule_triples(mid, data)}
}}
WHERE {{ OPTIONAL {{ {m} ?p ?o . VALUES ?p {{ {MOLECULE_OWNED} }} }} }}""")
    return get_molecule(t, mid)


def delete_molecule(t: Trace, mid: str):
    _require(mid, "Molecule")
    m = uri(mid)
    used = t.select("Vérification : molécule utilisée ?", render("""
SELECT ?label WHERE { ?med :contientMolecule {{m}} ; rdfs:label ?label }""", m=m))
    if used:
        raise Conflict("Suppression impossible : la molécule est contenue dans " + ", ".join(r["label"] for r in used))
    t.update("Suppression (DELETE WHERE)", f"DELETE WHERE {{ {m} ?p ?o }} ;\nDELETE WHERE {{ ?s ?p {m} }}")
    return {"supprime": mid}


# ===========================================================================
#  Médicaments
# ===========================================================================
def list_medicaments(t: Trace, type=None, ordonnance=None, forme=None, prixMin=None, prixMax=None, molecule=None, q=None, tri="label"):
    filters, params = [], {}
    if type:
        if type not in Q.MEDICAMENT_TYPES:
            raise ValueError("Type inconnu (Princeps ou Generique)")
        filters.append("?med a {{type}} .")
        params["type"] = uri(type)
    if ordonnance is not None:
        filters.append("?med :surOrdonnance {{ordonnance}} .")
        params["ordonnance"] = lit(bool(ordonnance))
    if forme:
        filters.append('FILTER(LCASE(STR(?forme)) = LCASE({{forme}}))')
        params["forme"] = lit(forme)
    if prixMin is not None:
        filters.append("FILTER(?prix >= {{prixMin}})")
        params["prixMin"] = lit(float(prixMin))
    if prixMax is not None:
        filters.append("FILTER(?prix <= {{prixMax}})")
        params["prixMax"] = lit(float(prixMax))
    if molecule:
        filters.append("?med :contientMolecule {{molecule}} .")
        params["molecule"] = uri(molecule)
    if q:
        filters.append('FILTER(REGEX(STR(?label), {{motif}}, "i") || REGEX(STRAFTER(STR(?med), "#"), {{motifSansAccent}}, "i") || REGEX(?molLabels, {{motif}}, "i"))')
        params["motif"] = lit(re.escape(q))
        params["motifSansAccent"] = lit(re.escape(strip_accents(q)))
    order = {"label": "?label", "prix": "?prix", "prix_desc": "DESC(?prix)"}.get(tri, "?label")
    sparql = render("""
SELECT ?med ?label ?nom ?dosage ?forme ?ordonnance ?prix ?type ?molLabels ?molIds WHERE {
  {
    SELECT ?med (GROUP_CONCAT(DISTINCT ?ml; separator="|") AS ?molLabels) (GROUP_CONCAT(DISTINCT STRAFTER(STR(?mol), "#"); separator="|") AS ?molIds) WHERE {
      ?med a :Medicament ; :contientMolecule ?mol . ?mol rdfs:label ?ml .
    } GROUP BY ?med
  }
  ?med rdfs:label ?label .
  OPTIONAL { ?med :nomCommercial ?nom } OPTIONAL { ?med :dosage ?dosage } OPTIONAL { ?med :formeGalenique ?forme }
  OPTIONAL { ?med :surOrdonnance ?ordonnance } OPTIONAL { ?med :prixDT ?prix }
  OPTIONAL { ?med a ?type . VALUES ?type { :Princeps :Generique } }
  """ + "\n  ".join(filters) + """
} ORDER BY """ + order, **params)
    rows = t.select("Liste des médicaments (filtres)", sparql)
    return [{
        "id": r["med"], "label": r["label"], "nomCommercial": r["nom"], "dosage": r["dosage"], "formeGalenique": r["forme"],
        "surOrdonnance": r["ordonnance"], "prixDT": r["prix"], "type": r["type"],
        "classe": _declared_class(r["med"], ["Princeps", "Generique", "PrincepsSurOrdonnance", "PrincepsSansOrdonnance", "GeneriqueSurOrdonnance", "GeneriqueSansOrdonnance"]),
        "molecules": [{"id": i, "label": l} for i, l in zip(_split(r["molIds"]), _split(r["molLabels"]))],
    } for r in rows]


def get_medicament(t: Trace, mid: str):
    _require(mid, "Medicament")
    m = uri(mid)
    info = t.select("Attributs du médicament", render("""
SELECT ?label ?nom ?dosage ?forme ?ordonnance ?prix WHERE {
  {{m}} rdfs:label ?label .
  OPTIONAL { {{m}} :nomCommercial ?nom } OPTIONAL { {{m}} :dosage ?dosage } OPTIONAL { {{m}} :formeGalenique ?forme }
  OPTIONAL { {{m}} :surOrdonnance ?ordonnance } OPTIONAL { {{m}} :prixDT ?prix }
}""", m=m))[0]
    types = t.select("Classes déclarées et inférées", render("""
SELECT ?classe ?label WHERE {
  {{m}} rdf:type ?classe . ?classe rdfs:subClassOf* :Medicament ; rdfs:label ?label .
}""", m=m))
    mols = t.select("Molécules contenues", render("""
SELECT ?id ?label ?atc ?dose WHERE {
  {{m}} :contientMolecule ?id . ?id rdfs:label ?label .
  OPTIONAL { ?id :codeATC ?atc } OPTIONAL { ?id :doseMaxJourMg ?dose }
}""", m=m))
    indications = t.select("Indications", render("""
SELECT ?id ?label ?cim10 WHERE { {{m}} :estIndiquePour ?id . ?id rdfs:label ?label . OPTIONAL { ?id :codeCIM10 ?cim10 } }""", m=m))
    ci = t.select("Contre-indications déduites (chaîne OWL estContreIndiquePour)", render("""
SELECT DISTINCT ?id ?label ?via ?viaLabel ?ci ?ciLabel ?risque WHERE {
  {{m}} :estContreIndiquePour ?id . ?id rdfs:label ?label .
  {{m}} :contientMolecule ?via . ?via :aContreIndication ?ci . ?ci :concernePathologie ?id .
  ?via rdfs:label ?viaLabel . ?ci rdfs:label ?ciLabel . OPTIONAL { ?ci :niveauRisque ?risque }
}""", m=m))
    ci_sans_patho = t.select("Contre-indications sans pathologie liée", render("""
SELECT DISTINCT ?ci ?ciLabel ?viaLabel ?risque WHERE {
  {{m}} :contientMolecule ?via . ?via :aContreIndication ?ci ; rdfs:label ?viaLabel . ?ci rdfs:label ?ciLabel .
  OPTIONAL { ?ci :niveauRisque ?risque }
  FILTER NOT EXISTS { ?ci :concernePathologie ?p }
}""", m=m))
    effets = t.select(Q.CATALOGUE["Q09_effets_graves_medicament"]["titre"], Q.catalogue_entry("Q09_effets_graves_medicament", medicament=m))
    ordonnance = t.ask(Q.CATALOGUE["Q12_est_sur_ordonnance"]["titre"], Q.catalogue_entry("Q12_est_sur_ordonnance", medicament=m))
    return {
        "id": mid, "label": info["label"], "nomCommercial": info["nom"], "dosage": info["dosage"],
        "formeGalenique": info["forme"], "surOrdonnance": ordonnance, "prixDT": info["prix"],
        "classes": [{"id": r["classe"], "label": r["label"], "inferee": not _declared(mid, RDF.type, r["classe"])} for r in types],
        "molecules": mols, "indications": indications,
        "contreIndications": ci, "contreIndicationsGenerales": ci_sans_patho, "effets": effets,
    }


def _medicament_triples(mid: str, d) -> str:
    m = uri(mid)
    label = f"{d.nomCommercial} {d.dosage}"
    lines = [
        f"{m} a owl:NamedIndividual , {uri(d.type)} ; rdfs:label {lit(label, lang='fr')} ;",
        f"   :nomCommercial {lit(d.nomCommercial)} ; :dosage {lit(d.dosage)} ; :formeGalenique {lit(d.formeGalenique)} ;",
        f"   :surOrdonnance {lit(d.surOrdonnance)} ; :prixDT {lit(float(d.prixDT))} .",
    ]
    for mol in d.molecules:
        lines.append(f"{m} :contientMolecule {uri(mol)} .")
    for p in d.indications:
        lines.append(f"{m} :estIndiquePour {uri(p)} .")
    return "\n  ".join(lines)


MEDICAMENT_OWNED = ":nomCommercial :dosage :formeGalenique :surOrdonnance :prixDT :contientMolecule :estIndiquePour rdfs:label rdf:type"


def _check_med_refs(d):
    for mol in d.molecules:
        _require(mol, "Molecule")
    for p in d.indications:
        _require(p, "Pathologie")


def create_medicament(t: Trace, d):
    mid = make_id(f"{d.nomCommercial} {d.dosage}") if store.exists(make_id(d.nomCommercial)) else make_id(d.nomCommercial)
    if store.exists(mid):
        raise Conflict(f"La ressource {mid} existe déjà")
    _check_med_refs(d)
    t.update("Création (INSERT DATA)", f"INSERT DATA {{\n  {_medicament_triples(mid, d)}\n}}")
    return get_medicament(t, mid)


def update_medicament(t: Trace, mid: str, d):
    _require(mid, "Medicament")
    _check_med_refs(d)
    m = uri(mid)
    t.update("Modification (DELETE / INSERT WHERE)", f"""DELETE {{ {m} ?p ?o }}
INSERT {{
  {_medicament_triples(mid, d)}
}}
WHERE {{ OPTIONAL {{ {m} ?p ?o . VALUES ?p {{ {MEDICAMENT_OWNED} }} }} }}""")
    return get_medicament(t, mid)


def delete_medicament(t: Trace, mid: str):
    _require(mid, "Medicament")
    m = uri(mid)
    used = t.select("Vérification : médicament prescrit ?", render("""
SELECT ?label WHERE { ?p :prescritMedicament {{m}} ; rdfs:label ?label }""", m=m))
    if used:
        raise Conflict("Suppression impossible : le médicament figure dans " + ", ".join(r["label"] for r in used))
    t.update("Suppression (DELETE WHERE)", f"DELETE WHERE {{ {m} ?p ?o }} ;\nDELETE WHERE {{ ?s ?p {m} }}")
    return {"supprime": mid}


# ===========================================================================
#  Valeurs ajoutées : comparateur, interactions, graphe
# ===========================================================================
def alternatives(t: Trace, mid: str):
    ref = get_medicament(Trace(), mid)
    rows = t.select(Q.CATALOGUE["Q06_alternatives_generiques"]["titre"], Q.catalogue_entry("Q06_alternatives_generiques", medicament=uri(mid)))
    moins_cheres = [r for r in rows if (r["economie"] or 0) > 0]
    best = max(moins_cheres, key=lambda r: r["economie"], default=None)
    return {
        "reference": {k: ref[k] for k in ("id", "label", "prixDT", "classes", "molecules")},
        "alternatives": [{
            "id": r["alternative"], "label": r["label"], "type": r["type"], "prixDT": r["prix"],
            "economie": round(r["economie"], 2) if r["economie"] is not None else None,
            "economiePct": r["economiePct"],
        } for r in rows],
        "meilleure": best and {"id": best["alternative"], "label": best["label"], "economie": round(best["economie"], 2), "economiePct": best["economiePct"]},
    }


def verifier_interactions(t: Trace, meds: list[str]):
    for m in meds:
        _require(m, "Medicament")
    values = " ".join(uri(m) for m in dict.fromkeys(meds))
    inter = t.select(Q.CATALOGUE["Q07_interactions"]["titre"], Q.catalogue_entry("Q07_interactions", medicaments=values))
    doublons = t.select(Q.CATALOGUE["Q07b_doublons_molecule"]["titre"], Q.catalogue_entry("Q07b_doublons_molecule", medicaments=values))
    alertes = [{
        "niveau": "interaction", "medicaments": [r["labelA"], r["labelB"]], "molecules": [r["molALabel"], r["molBLabel"]],
        "message": f"{r['labelA']} et {r['labelB']} : interaction entre {r['molALabel']} et {r['molBLabel']}.",
    } for r in inter] + [{
        "niveau": "doublon", "medicaments": [r["labelA"], r["labelB"]], "molecules": [r["molLabel"]],
        "message": f"{r['labelA']} et {r['labelB']} contiennent tous deux {r['molLabel']} : risque de surdosage.",
    } for r in doublons]
    return {"medicaments": meds, "alertes": alertes, "sur": not alertes}


def graphe_medicament(t: Trace, mid: str):
    _require(mid, "Medicament")
    g = t.construct(Q.CATALOGUE["Q13_fiche_graphe"]["titre"], Q.catalogue_entry("Q13_fiche_graphe", medicament=uri(mid)))
    from ...graph_store import to_python
    from rdflib.namespace import RDFS
    nodes, edges = {}, []

    def node(term):
        nid = to_python(term)
        if nid not in nodes:
            label = store.ds.value(term, RDFS.label)
            kind = None
            for cls in ("Medicament", "Molecule", "EffetSecondaire", "ContreIndication", "Pathologie"):
                if store.exists(nid, cls):
                    kind = cls
                    break
            nodes[nid] = {"id": nid, "label": str(label) if label else nid, "type": kind}
        return nid

    for s, p, o in g:
        edges.append({"source": node(s), "cible": node(o), "relation": to_python(p)})
    return {"centre": mid, "noeuds": list(nodes.values()), "aretes": edges}


# ===========================================================================
#  Hiérarchie, stats, référentiels
# ===========================================================================
def hierarchie(t: Trace):
    rows = t.select("Hiérarchie Molecule / Medicament (graphe déclaré)", """
SELECT ?classe ?label ?parent ?racine (COUNT(DISTINCT ?ind) AS ?nb) WHERE {
  VALUES ?racine { :Molecule :Medicament }
  GRAPH <urn:pharma:base> { ?classe rdfs:subClassOf* ?racine . }
  ?classe a owl:Class ; rdfs:label ?label .
  OPTIONAL { GRAPH <urn:pharma:base> { ?classe rdfs:subClassOf ?parent . FILTER(isIRI(?parent)) } }
  OPTIONAL { ?ind a ?classe . ?ind a owl:NamedIndividual }
} GROUP BY ?classe ?label ?parent ?racine ORDER BY ?racine ?label""")
    by_id = {}
    for r in rows:
        by_id.setdefault(r["classe"], {"id": r["classe"], "label": r["label"], "parent": r["parent"], "racine": r["racine"], "nbIndividus": r["nb"], "enfants": []})
    roots = []
    for n in by_id.values():
        if n["parent"] in by_id and n["id"] != n["racine"]:
            by_id[n["parent"]]["enfants"].append(n)
        elif n["id"] == n["racine"]:
            roots.append(n)
    return roots


def stats(t: Trace):
    par_type = t.select(Q.CATALOGUE["Q10_stats_par_type"]["titre"], Q.catalogue_entry("Q10_stats_par_type"))
    par_classe = t.select("Nombre de molécules par famille", """
SELECT ?famille ?label (COUNT(DISTINCT ?m) AS ?nombre) WHERE {
  VALUES ?famille { :Penicilline :Macrolide :AntalgiqueNonOpioide :AntalgiqueOpioide }
  ?famille rdfs:label ?label . OPTIONAL { ?m a ?famille }
} GROUP BY ?famille ?label ORDER BY DESC(?nombre)""")
    totaux = t.select("Totaux", """
SELECT (COUNT(DISTINCT ?mol) AS ?molecules) (COUNT(DISTINCT ?med) AS ?medicaments) WHERE {
  { ?mol a :Molecule } UNION { ?med a :Medicament }
}""")[0]
    orphelines = t.select(Q.CATALOGUE["Q11_molecules_orphelines"]["titre"], Q.catalogue_entry("Q11_molecules_orphelines"))
    return {"totaux": totaux, "parType": par_type, "parFamille": par_classe, "moleculesOrphelines": orphelines, "graphe": store.stats()}


def referentiels(t: Trace):
    """Listes pour les formulaires (effets, contre-indications, pathologies, molécules, formes)."""
    def lst(titre, cls):
        return t.select(titre, render("SELECT ?id ?label WHERE { ?id a {{c}} ; rdfs:label ?label } ORDER BY ?label", c=uri(cls)))
    formes = t.select("Formes galéniques utilisées", "SELECT DISTINCT ?forme WHERE { ?m :formeGalenique ?forme } ORDER BY ?forme")
    classes = t.select("Classes de molécules", render("""
SELECT ?id ?label WHERE { ?id rdfs:subClassOf* :Molecule ; rdfs:label ?label . FILTER(isIRI(?id)) } ORDER BY ?label"""))
    return {
        "molecules": lst("Molécules", "Molecule"), "effets": lst("Effets secondaires", "EffetSecondaire"),
        "contreIndications": lst("Contre-indications", "ContreIndication"), "pathologies": lst("Pathologies", "Pathologie"),
        "medicaments": lst("Médicaments", "Medicament"),
        "formes": [r["forme"] for r in formes], "classesMolecule": [c for c in classes if c["id"] in Q.MOLECULE_CLASSES],
    }
