"""Logique métier du module D (Prescription + Donnée clinique). Toute lecture/écriture passe par SPARQL.

Seules les classes Prescription et DonneeClinique sont créées / modifiées / supprimées ici ;
les patients, médecins, pharmaciens, médicaments, molécules et pathologies (autres modules) sont seulement lus.
"""
from __future__ import annotations

import re

from rdflib.namespace import RDFS

from ...graph_store import PH, RDF, store, to_python
from . import queries as Q
from .common import Conflict, NotFound, Trace, date_lit, lit, make_id, render, strip_accents, uri  # noqa: F401


def _require(local_id: str, cls: str):
    uri(local_id)  # valide le format avant toute requête
    if not store.exists(local_id, cls):
        raise NotFound(f"{cls} introuvable : {local_id}")


def _declared_class(local_id: str, allowed) -> str | None:
    for o in store.base.objects(PH[local_id], RDF.type):
        name = str(o).rsplit("#", 1)[-1]
        if name in allowed:
            return name
    return None


def _declared(subject: str, predicate, obj: str) -> bool:
    return (PH[subject], predicate, PH[obj]) in store.base


def _split(value) -> list[str]:
    return [v for v in (value or "").split("|") if v]


def _ref(row: dict, key: str):
    return {"id": row[key], "label": row.get(key + "Label")} if row.get(key) else None


def _categorie(pid: str) -> str | None:
    """Catégorie de niveau 2 (déclarée ou déduite par le raisonneur)."""
    if store.exists(pid, "PrescriptionRenouvelable"):
        return "PrescriptionRenouvelable"
    if store.exists(pid, "PrescriptionSimple"):
        return "PrescriptionSimple"
    return None


def _date_filters(filters, params, dateMin, dateMax, var="?date"):
    if dateMin and dateMax and dateMin > dateMax:
        raise ValueError("La date de début doit précéder la date de fin")
    if dateMin:
        filters.append(f"FILTER({var} >= {{{{dateMin}}}})")
        params["dateMin"] = date_lit(dateMin)
    if dateMax:
        filters.append(f"FILTER({var} <= {{{{dateMax}}}})")
        params["dateMax"] = date_lit(dateMax)


def _splice_from_lists(x: str) -> str:
    """Retire proprement un individu des listes RDF (ex. owl:AllDifferent) au lieu de les casser."""
    return f"""DELETE {{ ?prev ?lien ?noeud . ?noeud rdf:first {x} ; rdf:rest ?suite }}
INSERT {{ ?prev ?lien ?suite }}
WHERE {{ ?noeud rdf:first {x} ; rdf:rest ?suite . ?prev ?lien ?noeud . FILTER(?lien IN (rdf:rest, owl:distinctMembers, owl:members)) }}"""


def _paginate(total: int, page: int, taille: int, elements: list) -> dict:
    return {"elements": elements, "total": total, "page": page, "taille": taille, "pages": max(1, -(-total // taille))}


# ===========================================================================
#  Prescriptions : liste (filtres, recherche, tri, pagination)
# ===========================================================================
PRESC_SORTS = {
    "date": "?date ?p", "date_desc": "DESC(?date) ?p", "id": "?p",
    "patient": "?patientLabel ?p", "medecin": "?medecinLabel ?p", "duree": "DESC(?duree) ?p",
}


def list_prescriptions(t: Trace, type=None, patient=None, medecin=None, pharmacien=None, medicament=None,
                       dateMin=None, dateMax=None, q=None, tri="date", page=1, taille=20):
    filters, params = [], {}
    if type:
        if type not in Q.PRESCRIPTION_TYPES:
            raise ValueError(f"Type inconnu. Valeurs possibles : {', '.join(Q.PRESCRIPTION_TYPES)}")
        filters.append("?p a {{type}} .")
        params["type"] = uri(type)
    for key, value, cls, prop in (
        ("patient", patient, "Patient", ":concernePatient"),
        ("medecin", medecin, "Medecin", ":prescritPar"),
        ("pharmacien", pharmacien, "Pharmacien", ":estDelivreePar"),
        ("medicament", medicament, "Medicament", ":prescritMedicament"),
    ):
        if value:
            _require(value, cls)
            filters.append(f"?p {prop} {{{{{key}}}}} .")
            params[key] = uri(value)
    _date_filters(filters, params, dateMin, dateMax)
    if q:
        filters.append('FILTER(REGEX(STR(?label), {{motif}}, "i") || REGEX(STR(?patientLabel), {{motif}}, "i") '
                       '|| REGEX(STR(?medecinLabel), {{motif}}, "i") || REGEX(?medLabels, {{motif}}, "i") '
                       '|| REGEX(?medIds, {{motifSansAccent}}, "i") || REGEX(STRAFTER(STR(?p), "#"), {{motifSansAccent}}, "i"))')
        params["motif"] = lit(re.escape(q))
        params["motifSansAccent"] = lit(re.escape(strip_accents(q)))
    if tri not in PRESC_SORTS:
        raise ValueError(f"Tri inconnu. Valeurs possibles : {', '.join(PRESC_SORTS)}")

    body = """
  {
    SELECT ?p (GROUP_CONCAT(DISTINCT ?ml; separator="|") AS ?medLabels) (GROUP_CONCAT(DISTINCT STRAFTER(STR(?m), "#"); separator="|") AS ?medIds) WHERE {
      ?p a :Prescription ; :prescritMedicament ?m . ?m rdfs:label ?ml .
    } GROUP BY ?p
  }
  ?p rdfs:label ?label .
  OPTIONAL { ?p :datePrescription ?date } OPTIONAL { ?p :dureeJours ?duree }
  OPTIONAL { ?p :posologie ?posologie } OPTIONAL { ?p :estRenouvelable ?renouvelable }
  OPTIONAL { ?p :concernePatient ?patient . ?patient rdfs:label ?patientLabel }
  OPTIONAL { ?p :prescritPar ?medecin . ?medecin rdfs:label ?medecinLabel }
  OPTIONAL { ?p :estDelivreePar ?pharmacien . ?pharmacien rdfs:label ?pharmacienLabel }
  """ + "\n  ".join(filters)

    total = t.select("Nombre de prescriptions correspondant aux filtres (COUNT)",
                     render("SELECT (COUNT(DISTINCT ?p) AS ?total) WHERE {" + body + "\n}", **params))[0]["total"]
    rows = t.select("Prescriptions (filtres, tri, pagination LIMIT/OFFSET)", render(
        "SELECT DISTINCT ?p ?label ?date ?duree ?posologie ?renouvelable ?patient ?patientLabel ?medecin ?medecinLabel "
        "?pharmacien ?pharmacienLabel ?medLabels ?medIds WHERE {" + body
        + f"\n}} ORDER BY {PRESC_SORTS[tri]}\nLIMIT {int(taille)} OFFSET {int((page - 1) * taille)}", **params))
    return _paginate(total, page, taille, [{
        "id": r["p"], "label": r["label"], "datePrescription": r["date"], "dureeJours": r["duree"],
        "posologie": r["posologie"], "estRenouvelable": r["renouvelable"],
        "type": _declared_class(r["p"], Q.PRESCRIPTION_TYPES), "categorie": _categorie(r["p"]),
        "patient": _ref(r, "patient"), "medecin": _ref(r, "medecin"), "pharmacien": _ref(r, "pharmacien"),
        "medicaments": [{"id": i, "label": lbl} for i, lbl in zip(_split(r["medIds"]), _split(r["medLabels"]))],
    } for r in rows])


# ===========================================================================
#  Prescription : fiche détaillée et graphe
# ===========================================================================
def get_prescription(t: Trace, pid: str):
    _require(pid, "Prescription")
    p = uri(pid)
    info = t.select("Attributs et relations de l'ordonnance", render("""
SELECT ?label ?date ?duree ?posologie ?renouvelable ?patient ?patientLabel ?medecin ?medecinLabel ?specialite ?pharmacien ?pharmacienLabel WHERE {
  {{p}} rdfs:label ?label .
  OPTIONAL { {{p}} :datePrescription ?date } OPTIONAL { {{p}} :dureeJours ?duree }
  OPTIONAL { {{p}} :posologie ?posologie } OPTIONAL { {{p}} :estRenouvelable ?renouvelable }
  OPTIONAL { {{p}} :concernePatient ?patient . ?patient rdfs:label ?patientLabel }
  OPTIONAL { {{p}} :prescritPar ?medecin . ?medecin rdfs:label ?medecinLabel . OPTIONAL { ?medecin :specialite ?specialite } }
  OPTIONAL { {{p}} :estDelivreePar ?pharmacien . ?pharmacien rdfs:label ?pharmacienLabel }
}""", p=p))[0]
    types = t.select("Classes déclarées et inférées", render("""
SELECT DISTINCT ?classe ?label WHERE {
  {{p}} rdf:type ?classe . ?classe rdfs:subClassOf* :Prescription ; rdfs:label ?label .
}""", p=p))
    meds = t.select("Médicaments prescrits (prescritMedicament)", render("""
SELECT ?id ?label ?dosage ?forme (GROUP_CONCAT(DISTINCT COALESCE(?molLabel, ""); separator="|") AS ?molecules) WHERE {
  {{p}} :prescritMedicament ?id . ?id rdfs:label ?label .
  OPTIONAL { ?id :dosage ?dosage } OPTIONAL { ?id :formeGalenique ?forme }
  OPTIONAL { ?id :contientMolecule/rdfs:label ?molLabel }
} GROUP BY ?id ?label ?dosage ?forme ORDER BY ?label""", p=p))
    patient = None
    if info["patient"]:
        pat = uri(info["patient"])
        pinfo = t.select("Profil du patient (lecture seule)", render("""
SELECT ?age ?sexe (GROUP_CONCAT(DISTINCT COALESCE(?patho, ""); separator="|") AS ?pathologies) WHERE {
  OPTIONAL { {{pat}} :age ?age } OPTIONAL { {{pat}} :sexe ?sexe }
  OPTIONAL { {{pat}} :souffreDe/rdfs:label ?patho }
} GROUP BY ?age ?sexe""", pat=pat))[0]
        patient = {"id": info["patient"], "label": info["patientLabel"], "age": pinfo["age"], "sexe": pinfo["sexe"],
                   "pathologies": _split(pinfo["pathologies"]),
                   "donneesCliniques": _dossier_clinique(t, info["patient"])}
    return {
        "id": pid, "label": info["label"], "datePrescription": info["date"], "dureeJours": info["duree"],
        "posologie": info["posologie"], "estRenouvelable": info["renouvelable"],
        "type": _declared_class(pid, Q.PRESCRIPTION_TYPES), "categorie": _categorie(pid),
        "classes": [{"id": r["classe"], "label": r["label"], "inferee": not _declared(pid, RDF.type, r["classe"])} for r in types],
        "patient": patient,
        "medecin": info["medecin"] and {"id": info["medecin"], "label": info["medecinLabel"], "specialite": info["specialite"]},
        "pharmacien": _ref(info, "pharmacien"),
        "medicaments": [{**m, "molecules": _split(m["molecules"])} for m in meds],
        "alertes": alertes(t, prescription=pid),
    }


GRAPH_KINDS = ("Prescription", "Patient", "Medecin", "Pharmacien", "DonneeClinique", "Medicament", "Molecule",
               "ContreIndication", "Pathologie")


def graphe_prescription(t: Trace, pid: str):
    _require(pid, "Prescription")
    g = t.construct(Q.CATALOGUE["D12_graphe_prescription"]["titre"], Q.catalogue_entry("D12_graphe_prescription", prescription=uri(pid)))
    nodes, edges = {}, []

    def node(term):
        nid = to_python(term)
        if nid not in nodes:
            label = store.ds.value(term, RDFS.label)
            kind = next((k for k in GRAPH_KINDS if store.exists(nid, k)), None)
            nodes[nid] = {"id": nid, "label": str(label) if label else nid, "type": kind}
        return nid

    for s, p, o in g:
        edges.append({"source": node(s), "cible": node(o), "relation": to_python(p)})
    return {"centre": pid, "noeuds": list(nodes.values()), "aretes": edges, "triplets": len(g)}


# ===========================================================================
#  Prescription : CRUD
# ===========================================================================
def _next_id(prefix: str) -> str:
    nums = [int(m.group(1)) for s in set(store.base.subjects())
            if (m := re.fullmatch(re.escape(str(PH)) + re.escape(prefix) + r"(\d+)", str(s)))]
    return f"{prefix}{max(nums, default=0) + 1:03d}"


def _check_prescription_refs(d):
    _require(d.medecin, "Medecin")
    _require(d.patient, "Patient")
    if d.pharmacien:
        _require(d.pharmacien, "Pharmacien")
    for m in d.medicaments:
        _require(m, "Medicament")


def _prescription_triples(pid: str, d, label: str) -> str:
    p = uri(pid)
    lines = [
        f"{p} a owl:NamedIndividual , {uri(d.type)} ; rdfs:label {lit(label, lang='fr')} ;",
        f"   :datePrescription {date_lit(d.datePrescription)} ; :dureeJours {lit(int(d.dureeJours))} ;",
        f"   :posologie {lit(d.posologie)} ; :estRenouvelable {lit(Q.PRESCRIPTION_TYPES[d.type])} ;",
        f"   :prescritPar {uri(d.medecin)} ; :concernePatient {uri(d.patient)} .",
    ]
    lines += [f"{p} :prescritMedicament {uri(m)} ." for m in d.medicaments]
    if d.pharmacien:
        lines.append(f"{p} :estDelivreePar {uri(d.pharmacien)} .")
    return "\n  ".join(lines)


PRESCRIPTION_OWNED = (":datePrescription :dureeJours :posologie :estRenouvelable :prescritPar :concernePatient "
                      ":prescritMedicament :estDelivreePar rdfs:label rdf:type")


def create_prescription(t: Trace, d):
    _check_prescription_refs(d)
    pid = _next_id("Presc_")
    label = d.libelle or f"Ordonnance {pid.split('_')[1]}"
    t.update("Création (INSERT DATA)", f"INSERT DATA {{\n  {_prescription_triples(pid, d, label)}\n}}")
    return get_prescription(t, pid)


def update_prescription(t: Trace, pid: str, d):
    _require(pid, "Prescription")
    _check_prescription_refs(d)
    label = d.libelle or str(store.base.value(PH[pid], RDFS.label) or f"Ordonnance {pid}")
    p = uri(pid)
    t.update("Modification (DELETE / INSERT WHERE)", f"""DELETE {{ {p} ?p ?o }}
INSERT {{
  {_prescription_triples(pid, d, label)}
}}
WHERE {{ OPTIONAL {{ {p} ?p ?o . VALUES ?p {{ {PRESCRIPTION_OWNED} }} }} }}""")
    return get_prescription(t, pid)


def delete_prescription(t: Trace, pid: str):
    _require(pid, "Prescription")
    p = uri(pid)
    t.update("Suppression (DELETE WHERE)", f"{_splice_from_lists(p)} ;\nDELETE WHERE {{ {p} ?p ?o }} ;\nDELETE WHERE {{ ?s ?p {p} }}")
    return {"supprime": pid}


# ===========================================================================
#  Données cliniques : liste, fiche, CRUD
# ===========================================================================
DONNEE_SORTS = {"date_desc": "DESC(?date) ?d", "date": "?date ?d", "patient": "?patientLabel ?d", "type": "?type ?d", "label": "?label ?d"}

DONNEE_BODY = """
  ?d a :DonneeClinique ; rdfs:label ?label ; :estDonneeDe ?patient .
  ?patient rdfs:label ?patientLabel .
  GRAPH <urn:pharma:base> { ?d a ?type . }
  FILTER(?type IN (:SigneVital, :AnalyseBiologique, :Allergie, :Antecedent, :ExamenClinique, :HistoriqueMedical, :DonneeClinique))
  OPTIONAL { ?d :valeur ?valeur } OPTIONAL { ?d :unite ?unite } OPTIONAL { ?d :dateMesure ?date }
  OPTIONAL { ?d :allergiqueA ?molecule . ?molecule rdfs:label ?moleculeLabel }
  OPTIONAL { ?d :porteSur ?pathologie . ?pathologie rdfs:label ?pathologieLabel }
  """


def _donnee_row(r: dict) -> dict:
    return {
        "id": r["d"], "label": r["label"], "type": r["type"], "categorie": Q.DONNEE_LEAVES.get(r["type"]),
        "patient": _ref(r, "patient"), "valeur": r["valeur"], "unite": r["unite"], "dateMesure": r["date"],
        "molecule": _ref(r, "molecule"), "pathologie": _ref(r, "pathologie"),
    }


def list_donnees(t: Trace, type=None, patient=None, dateMin=None, dateMax=None, q=None, tri="date_desc", page=1, taille=20):
    filters, params = [], {}
    if type:
        if type not in Q.DONNEE_TYPES:
            raise ValueError(f"Type inconnu. Valeurs possibles : {', '.join(Q.DONNEE_TYPES)}")
        filters.append("?d a {{filtreType}} .")
        params["filtreType"] = uri(type)
    if patient:
        _require(patient, "Patient")
        filters.append("?d :estDonneeDe {{filtrePatient}} .")
        params["filtrePatient"] = uri(patient)
    _date_filters(filters, params, dateMin, dateMax)
    if q:
        filters.append('FILTER(REGEX(STR(?label), {{motif}}, "i") || REGEX(STR(?patientLabel), {{motif}}, "i") '
                       '|| REGEX(COALESCE(STR(?moleculeLabel), ""), {{motif}}, "i") || REGEX(COALESCE(STR(?pathologieLabel), ""), {{motif}}, "i") '
                       '|| REGEX(STRAFTER(STR(?d), "#"), {{motifSansAccent}}, "i"))')
        params["motif"] = lit(re.escape(q))
        params["motifSansAccent"] = lit(re.escape(strip_accents(q)))
    if tri not in DONNEE_SORTS:
        raise ValueError(f"Tri inconnu. Valeurs possibles : {', '.join(DONNEE_SORTS)}")
    body = DONNEE_BODY + "\n  ".join(filters)
    total = t.select("Nombre de données cliniques (COUNT)", render("SELECT (COUNT(DISTINCT ?d) AS ?total) WHERE {" + body + "\n}", **params))[0]["total"]
    rows = t.select("Données cliniques (filtres, tri, pagination)", render(
        "SELECT DISTINCT ?d ?label ?type ?patient ?patientLabel ?valeur ?unite ?date ?molecule ?moleculeLabel ?pathologie ?pathologieLabel WHERE {"
        + body + f"\n}} ORDER BY {DONNEE_SORTS[tri]}\nLIMIT {int(taille)} OFFSET {int((page - 1) * taille)}", **params))
    return _paginate(total, page, taille, [_donnee_row(r) for r in rows])


def get_donnee(t: Trace, did: str):
    _require(did, "DonneeClinique")
    rows = t.select("Attributs de la donnée clinique", render(
        "SELECT ?d ?label ?type ?patient ?patientLabel ?valeur ?unite ?date ?molecule ?moleculeLabel ?pathologie ?pathologieLabel WHERE {"
        + DONNEE_BODY + "FILTER(?d = {{d}})\n}", d=uri(did)))
    if not rows:
        raise NotFound(f"DonneeClinique introuvable : {did}")
    out = _donnee_row(rows[0])
    types = t.select("Classes déclarées et inférées", render("""
SELECT DISTINCT ?classe ?label WHERE { {{d}} rdf:type ?classe . ?classe rdfs:subClassOf* :DonneeClinique ; rdfs:label ?label . }""", d=uri(did)))
    out["classes"] = [{"id": r["classe"], "label": r["label"], "inferee": not _declared(did, RDF.type, r["classe"])} for r in types]
    return out


def _check_donnee_refs(d):
    _require(d.patient, "Patient")
    if d.molecule:
        _require(d.molecule, "Molecule")
    if d.pathologie:
        _require(d.pathologie, "Pathologie")


def _donnee_id(d) -> str:
    """Convention de l'ontologie : <Mesure>_<Patient> (ex. Glycemie_Ali, Allergie_Sara)."""
    head = d.type if d.type in ("Allergie", "Antecedent") else make_id(d.libelle.split()[0])
    base = f"{head}_{d.patient.split('_', 1)[-1]}"
    n = 2
    candidate = base
    while store.exists(candidate):
        candidate = f"{base}{n}"
        n += 1
    return candidate


def _donnee_triples(did: str, d) -> str:
    x = uri(did)
    lines = [f"{x} a owl:NamedIndividual , {uri(d.type)} ; rdfs:label {lit(d.libelle, lang='fr')} ;",
             f"   :dateMesure {date_lit(d.dateMesure)} ; :estDonneeDe {uri(d.patient)} ."]
    if d.valeur is not None:
        lines.append(f"{x} :valeur {lit(float(d.valeur))} ; :unite {lit(d.unite)} .")
    if d.molecule:
        lines.append(f"{x} :allergiqueA {uri(d.molecule)} .")
    if d.pathologie:
        lines.append(f"{x} :porteSur {uri(d.pathologie)} .")
    return "\n  ".join(lines)


DONNEE_OWNED = ":dateMesure :estDonneeDe :valeur :unite :allergiqueA :porteSur rdfs:label rdf:type"


def create_donnee(t: Trace, d):
    _check_donnee_refs(d)
    did = _donnee_id(d)
    t.update("Création (INSERT DATA)", f"INSERT DATA {{\n  {_donnee_triples(did, d)}\n}}")
    return get_donnee(t, did)


def update_donnee(t: Trace, did: str, d):
    _require(did, "DonneeClinique")
    _check_donnee_refs(d)
    x = uri(did)
    t.update("Modification (DELETE / INSERT WHERE)", f"""DELETE {{ {x} ?p ?o }}
INSERT {{
  {_donnee_triples(did, d)}
}}
WHERE {{ OPTIONAL {{ {x} ?p ?o . VALUES ?p {{ {DONNEE_OWNED} }} }} }}""")
    return get_donnee(t, did)


def delete_donnee(t: Trace, did: str):
    _require(did, "DonneeClinique")
    x = uri(did)
    t.update("Suppression (DELETE WHERE)", f"{_splice_from_lists(x)} ;\nDELETE WHERE {{ {x} ?p ?o }} ;\nDELETE WHERE {{ ?s ?p {x} }}")
    return {"supprime": did}


def _dossier_clinique(t: Trace, pid: str) -> list[dict]:
    rows = t.select(Q.CATALOGUE["D15_dossier_clinique"]["titre"], render(
        "SELECT ?d ?label ?type ?patient ?patientLabel ?valeur ?unite ?date ?molecule ?moleculeLabel ?pathologie ?pathologieLabel WHERE {"
        + DONNEE_BODY + "FILTER(?patient = {{p}})\n} ORDER BY DESC(?date)", p=uri(pid)))
    return [_donnee_row(r) for r in rows]


# ===========================================================================
#  Alertes et dossier patient (scénario Patient → … → Contre-indication)
# ===========================================================================
def alertes(t: Trace, patient: str | None = None, prescription: str | None = None):
    restriction = ""
    if patient:
        _require(patient, "Patient")
        restriction = f"FILTER(?pat = {uri(patient)})"
    if prescription:
        _require(prescription, "Prescription")
        restriction = f"FILTER(?presc = {uri(prescription)})"
    rows = t.select(Q.CATALOGUE["D06_alertes_prescriptions"]["titre"],
                    Q.catalogue_entry("D06_alertes_prescriptions", restriction=restriction))
    return [{
        "prescription": {"id": r["presc"], "label": r["ordonnance"]}, "patient": {"id": r["pat"], "label": r["patient"]},
        "medicament": {"id": r["med"], "label": r["medicament"]}, "molecule": {"id": r["mol"], "label": r["molecule"]},
        "type": r["type"], "source": r["source"], "motif": r["motif"],
    } for r in rows]


def dossier_patient(t: Trace, pid: str):
    """Chaîne complète Patient → Prescription → Médicament → Molécule → Contre-indication → Pathologie + données cliniques."""
    _require(pid, "Patient")
    pat = uri(pid)
    info = t.select("Profil du patient (lecture seule)", render("""
SELECT ?label ?age ?sexe (GROUP_CONCAT(DISTINCT COALESCE(CONCAT(STRAFTER(STR(?patho), "#"), "=", STR(?pathoLabel)), ""); separator="|") AS ?pathologies) WHERE {
  {{pat}} rdfs:label ?label .
  OPTIONAL { {{pat}} :age ?age } OPTIONAL { {{pat}} :sexe ?sexe }
  OPTIONAL { {{pat}} :souffreDe ?patho . ?patho rdfs:label ?pathoLabel }
} GROUP BY ?label ?age ?sexe""", pat=pat))[0]
    donnees = _dossier_clinique(t, pid)
    allergenes = {d["molecule"]["id"] for d in donnees if d["molecule"]}
    rows = t.select(Q.CATALOGUE["D07_chaine_patient"]["titre"], Q.catalogue_entry("D07_chaine_patient", patient=pat))
    danger_ci = t.ask(Q.CATALOGUE["D11_patient_en_danger"]["titre"], Q.catalogue_entry("D11_patient_en_danger", patient=pat))
    alerts = alertes(t, patient=pid)

    prescriptions: dict[str, dict] = {}
    seen = set()
    for r in rows:
        pr = prescriptions.setdefault(r["prescription"], {"id": r["prescription"], "label": r["prescLabel"], "medicaments": {}})
        med = pr["medicaments"].setdefault(r["medicament"], {"id": r["medicament"], "label": r["medLabel"], "molecules": {}})
        mol = med["molecules"].setdefault(r["molecule"], {"id": r["molecule"], "label": r["molLabel"], "contreIndications": [],
                                                          "allergie": r["molecule"] in allergenes})
        key = (r["prescription"], r["medicament"], r["molecule"], r["ci"], r["pathologie"])
        if r["ci"] and key not in seen:
            seen.add(key)
            ci = {"id": r["ci"], "label": r["ciLabel"], "risque": r["risque"], "conflit": bool(r["conflit"])}
            if r["pathologie"]:
                ci["pathologie"] = {"id": r["pathologie"], "label": r["pathoLabel"]}
            mol["contreIndications"].append(ci)

    out = []
    for pr in prescriptions.values():
        meds = []
        for med in pr["medicaments"].values():
            mols = list(med["molecules"].values())
            meds.append({**med, "molecules": mols,
                         "conflit": any(m["allergie"] or any(c["conflit"] for c in m["contreIndications"]) for m in mols)})
        out.append({**pr, "medicaments": meds, "conflit": any(m["conflit"] for m in meds)})
    pair = lambda s: [{"id": k, "label": v} for k, v in (x.split("=", 1) for x in _split(s))]  # noqa: E731
    return {
        "patient": {"id": pid, "label": info["label"], "age": info["age"], "sexe": info["sexe"], "pathologies": pair(info["pathologies"])},
        "donneesCliniques": donnees,
        "prescriptions": out,
        "danger": bool(alerts) or any(p["conflit"] for p in out),
        "contreIndicationDetectee": danger_ci,
        "alertes": alerts,
    }


# ===========================================================================
#  Référentiels, statistiques, ontologie
# ===========================================================================
def referentiels(t: Trace):
    def lst(titre, cls):
        return t.select(titre, render("SELECT ?id ?label WHERE { ?id a {{c}} ; rdfs:label ?label } ORDER BY ?label", c=uri(cls)))

    def subclasses(titre, root, allowed):
        rows = t.select(titre, render("""
SELECT ?id ?label ?parent WHERE { GRAPH <urn:pharma:base> { ?id rdfs:subClassOf+ {{r}} . ?id rdfs:subClassOf ?parent }
  ?id rdfs:label ?label . FILTER(isIRI(?id) && isIRI(?parent)) } ORDER BY ?parent ?label""", r=uri(root)))
        return [r for r in rows if r["id"] in allowed]
    return {
        "patients": lst("Patients (lecture seule)", "Patient"), "medecins": lst("Médecins (lecture seule)", "Medecin"),
        "pharmaciens": lst("Pharmaciens (lecture seule)", "Pharmacien"), "medicaments": lst("Médicaments (lecture seule)", "Medicament"),
        "molecules": lst("Molécules (lecture seule)", "Molecule"), "pathologies": lst("Pathologies (lecture seule)", "Pathologie"),
        "typesPrescription": [dict(r, renouvelable=Q.PRESCRIPTION_TYPES[r["id"]])
                              for r in subclasses("Sous-classes de Prescription", "Prescription", Q.PRESCRIPTION_TYPES)],
        "typesDonnee": subclasses("Sous-classes de DonneeClinique", "DonneeClinique", Q.DONNEE_TYPES),
    }


def stats(t: Trace):
    totaux = t.select("Totaux du module D", """
SELECT (COUNT(DISTINCT ?p) AS ?prescriptions) (COUNT(DISTINCT ?r) AS ?renouvelables) (COUNT(DISTINCT ?s) AS ?simples)
       (COUNT(DISTINCT ?d) AS ?donneesCliniques) (COUNT(DISTINCT ?e) AS ?examens) (COUNT(DISTINCT ?h) AS ?historiques) WHERE {
  { ?p a :Prescription } UNION { ?r a :PrescriptionRenouvelable } UNION { ?s a :PrescriptionSimple }
  UNION { ?d a :DonneeClinique } UNION { ?e a :ExamenClinique } UNION { ?h a :HistoriqueMedical }
}""")[0]
    par_mois = t.select("Prescriptions par mois", """
SELECT ?mois (COUNT(?p) AS ?nombre) WHERE { ?p a :Prescription ; :datePrescription ?d . BIND(SUBSTR(STR(?d), 1, 7) AS ?mois) }
GROUP BY ?mois ORDER BY ?mois""")
    par_type = t.select("Prescriptions par type déclaré", """
SELECT ?type ?label (COUNT(DISTINCT ?p) AS ?nombre) WHERE {
  VALUES ?type { :PrescriptionNormale :PrescriptionUrgente :RenouvellementCourt :RenouvellementLong }
  ?type rdfs:label ?label . OPTIONAL { ?p a ?type }
} GROUP BY ?type ?label ORDER BY ?type""")
    donnees = t.select(Q.CATALOGUE["D13_donnees_par_type"]["titre"], Q.catalogue_entry("D13_donnees_par_type"))
    medecins = t.select(Q.CATALOGUE["D08_stats_medecins"]["titre"], Q.catalogue_entry("D08_stats_medecins"))
    non_delivrees = t.select(Q.CATALOGUE["D09_ordonnances_non_delivrees"]["titre"], Q.catalogue_entry("D09_ordonnances_non_delivrees"))
    nb_alertes = len({(a["prescription"]["id"], a["medicament"]["id"]) for a in alertes(t)})
    return {"totaux": {**totaux, "alertes": nb_alertes}, "parMois": par_mois, "parType": par_type, "donneesParType": donnees,
            "medecins": medecins, "nonDelivrees": non_delivrees, "graphe": store.stats()}


def ontology_stats(t: Trace):
    modules = t.select("Individus par classe principale", """
SELECT ?classe ?label (COUNT(DISTINCT ?i) AS ?individus) WHERE {
  VALUES ?classe { :Prescription :DonneeClinique :Personne :Medicament :Molecule :Pathologie :EffetSecondaire :ContreIndication }
  ?classe rdfs:label ?label .
  OPTIONAL { ?i a ?classe , owl:NamedIndividual }
} GROUP BY ?classe ?label ORDER BY DESC(?individus)""")
    return {"graphe": store.stats(), "modules": modules,
            "espacesDeNoms": {"": str(PH), "rdf": str(RDF), "rdfs": str(RDFS), "owl": "http://www.w3.org/2002/07/owl#",
                              "xsd": "http://www.w3.org/2001/XMLSchema#"}}
