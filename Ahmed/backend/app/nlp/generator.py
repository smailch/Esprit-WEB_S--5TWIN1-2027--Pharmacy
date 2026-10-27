"""Étape 6 — Génération SPARQL : un gabarit paramétré par intention, remplis avec des slots sûrs.

Aucune requête n'est produite par un modèle de langage : les valeurs viennent de l'entity linking
(IRI validés) et des contraintes (entiers, « M »/« F »), formatées par templates.fmt.
"""
from __future__ import annotations

from app.config.ontology_mapping import AGE_ADULTE, PREFIXES, cls, iri, prop
from app.sparql.templates import escape_literal, fmt, render


class MissingSlot(Exception):
    pass


def _first(entities, *types):
    return next((e for e in entities if e.type in types), None)


def _person_filters(c: dict, var="?p", age="?age", sexe="?sexe") -> str:
    f = []
    if "age_min" in c:
        f.append(f"FILTER({age} >= {fmt(c['age_min'], 'int')})")
    if "age_max" in c:
        f.append(f"FILTER({age} <= {fmt(c['age_max'], 'int')})")
    if "sexe" in c:
        f.append(f"FILTER({sexe} = {escape_literal(c['sexe'])})")
    if c.get("classe") == "PatientEnfant":
        f.append(f"FILTER({age} < {AGE_ADULTE})")
    elif c.get("classe") == "PatientAdulte":
        f.append(f"FILTER({age} >= {AGE_ADULTE})")
    return "\n  ".join(f)


PATIENT_BASE = f"""?p a/rdfs:subClassOf* {cls('Patient')} ; rdfs:label ?patient ; {prop('age')} ?age .
  OPTIONAL {{ ?p {prop('sexe')} ?sexe }}"""


def _patho_clause(ents, c, var="?p") -> str:
    """Pathologie (ou type, sous-types compris) dans ?m ; FILTER NOT EXISTS si la question est négative."""
    patho, typ = _first(ents, "PATHOLOGIE"), _first(ents, "TYPE")
    if patho:
        clause = f"{var} {prop('souffreDe')} ?m . FILTER(?m = {iri(patho.id)})"
    elif typ:
        clause = f"{var} {prop('souffreDe')} ?m . ?m a/rdfs:subClassOf* {iri(typ.id)} ."
    else:
        return ""
    return f"FILTER NOT EXISTS {{ {clause} }}" if c.get("negation") else clause


def generate(intent: str, ents: list, c: dict) -> str:
    classe = _first(ents, "CLASSE")
    if classe:
        c = {**c, "classe": classe.id}

    if intent == "patients_par_pathologie":
        if not _first(ents, "PATHOLOGIE", "TYPE"):
            raise MissingSlot("une pathologie (ex. diabète) ou un type (ex. chronique)")
        if c.get("negation"):
            return PREFIXES + f"""SELECT ?patient ?age ?sexe WHERE {{
  {PATIENT_BASE}
  {_patho_clause(ents, c)}
  {_person_filters(c)}
}} ORDER BY ?patient"""
        return PREFIXES + f"""SELECT ?patient ?age ?sexe (GROUP_CONCAT(DISTINCT ?pl; separator=", ") AS ?pathologies) WHERE {{
  {PATIENT_BASE}
  {_patho_clause(ents, c)}
  ?m rdfs:label ?pl .
  {_person_filters(c)}
}} GROUP BY ?patient ?age ?sexe ORDER BY ?patient"""

    if intent == "pathologies_patient":
        pat = _first(ents, "PATIENT")
        if not pat:
            raise MissingSlot("un patient (ex. Sara Jlassi)")
        return PREFIXES + f"""SELECT ?pathologie ?code ?type WHERE {{
  {iri(pat.id)} {prop('souffreDe')} ?m .
  ?m rdfs:label ?pathologie ; a ?t . ?t rdfs:subClassOf* {cls('Pathologie')} ; rdfs:label ?type .
  OPTIONAL {{ ?m {prop('codeCIM10')} ?code }}
}} ORDER BY ?pathologie"""

    if intent == "patients_filtre":
        neg = (f"FILTER NOT EXISTS {{ ?p {prop('souffreDe')} ?x }}"
               if c.get("negation") and not _first(ents, "PATHOLOGIE", "TYPE") else _patho_clause(ents, c))
        return PREFIXES + f"""SELECT ?patient ?age ?sexe ?classe WHERE {{
  {PATIENT_BASE}
  BIND(IF(?age < {AGE_ADULTE}, "Enfant", "Adulte") AS ?classe)
  {neg}
  {_person_filters(c)}
}} ORDER BY ?age"""

    if intent == "compter":
        cible = c.get("cible")
        spec = _first(ents, "SPECIALITE")
        if cible in ("Medecin", "Pharmacien"):
            f = f"?x {prop('specialite')} {escape_literal(spec.id)} ." if spec else ""
            return PREFIXES + f"SELECT (COUNT(DISTINCT ?x) AS ?nombre) WHERE {{ ?x a {cls(cible)} . {f} }}"
        if cible == "Pathologie" and not _first(ents, "PATHOLOGIE"):
            typ = _first(ents, "TYPE")
            target = iri(typ.id) if typ else cls("Pathologie")
            return PREFIXES + f"SELECT (COUNT(DISTINCT ?x) AS ?nombre) WHERE {{ ?x a/rdfs:subClassOf* {target} }}"
        return PREFIXES + f"""SELECT (COUNT(DISTINCT ?p) AS ?nombre) WHERE {{
  {PATIENT_BASE}
  {_patho_clause(ents, c)}
  {_person_filters(c)}
}}"""

    if intent == "pathologies_par_type":
        typ = _first(ents, "TYPE")
        target = iri(typ.id) if typ else cls("Pathologie")
        return PREFIXES + f"""SELECT ?pathologie ?code ?type WHERE {{
  ?m a ?t ; rdfs:label ?pathologie . ?t rdfs:subClassOf* {target} ; rdfs:label ?type .
  OPTIONAL {{ ?m {prop('codeCIM10')} ?code }}
}} ORDER BY ?type ?pathologie"""

    if intent == "code_cim10":
        patho, typ = _first(ents, "PATHOLOGIE"), _first(ents, "TYPE")
        if patho:
            where = f"BIND({iri(patho.id)} AS ?m) ?m rdfs:label ?pathologie ."
        elif typ:
            where = f"?m a/rdfs:subClassOf* {iri(typ.id)} ; rdfs:label ?pathologie ."
        else:
            raise MissingSlot("une pathologie (ex. diabète)")
        return PREFIXES + f"""SELECT ?pathologie ?code WHERE {{
  {where}
  OPTIONAL {{ ?m {prop('codeCIM10')} ?code }}
}} ORDER BY ?pathologie"""

    if intent == "medicaments_indiques":
        patho = _first(ents, "PATHOLOGIE")
        if not patho:
            raise MissingSlot("une pathologie (ex. migraine)")
        return PREFIXES + f"""SELECT ?medicament ?molecule WHERE {{
  ?med {prop('estIndiquePour')} {iri(patho.id)} ; rdfs:label ?medicament .
  OPTIONAL {{ ?med {prop('contientMolecule')}/rdfs:label ?molecule }}
}} ORDER BY ?medicament"""

    if intent == "medicaments_contre_indiques":
        patho, typ = _first(ents, "PATHOLOGIE"), _first(ents, "TYPE")
        if patho:
            target = f"{iri(patho.id)} . BIND({iri(patho.id)} AS ?m)"
        elif typ:
            target = f"?m . ?m a/rdfs:subClassOf* {iri(typ.id)} ."
        else:
            raise MissingSlot("une pathologie (ex. insuffisance rénale)")
        return PREFIXES + f"""SELECT DISTINCT ?medicament ?molecule ?contreIndication ?pathologie WHERE {{
  ?med {prop('contientMolecule')} ?mol .
  ?mol {prop('aContreIndication')} ?ci . ?ci {prop('concernePathologie')} {target}
  ?med rdfs:label ?medicament . ?mol rdfs:label ?molecule . ?ci rdfs:label ?contreIndication .
  ?m rdfs:label ?pathologie .
}} ORDER BY ?medicament"""

    if intent == "medecins_par_specialite":
        pro = _first(ents, "MEDECIN", "PHARMACIEN")
        spec = _first(ents, "SPECIALITE")
        target = "Pharmacien" if (c.get("cible") == "Pharmacien" or (pro and pro.type == "PHARMACIEN")) else "Medecin"
        f = ""
        if pro:
            f = f"FILTER(?s = {iri(pro.id)})"
        elif spec:
            f = f"FILTER(?specialite = {escape_literal(spec.id)})"
        return PREFIXES + f"""SELECT ?nom ?specialite WHERE {{
  ?s a {cls(target)} ; rdfs:label ?nom ; {prop('specialite')} ?specialite .
  {f}
}} ORDER BY ?nom"""

    if intent == "patients_medecin":
        pro = _first(ents, "MEDECIN", "PHARMACIEN")
        if not pro:
            raise MissingSlot("un médecin ou un pharmacien (ex. Dr Benali)")
        link = prop("prescritPar") if pro.type == "MEDECIN" else prop("estDelivreePar")
        return PREFIXES + f"""SELECT DISTINCT ?patient ?ordonnance WHERE {{
  ?presc {link} {iri(pro.id)} ; {prop('concernePatient')} ?p ; rdfs:label ?ordonnance .
  ?p rdfs:label ?patient .
}} ORDER BY ?patient"""

    if intent == "intervenants_prescription":
        presc = _first(ents, "PRESCRIPTION")
        if not presc:
            raise MissingSlot("une ordonnance (ex. ordonnance 003)")
        return PREFIXES + f"""SELECT ?ordonnance ?patient ?medecin ?pharmacien
       (GROUP_CONCAT(DISTINCT ?med; separator=", ") AS ?medicaments) WHERE {{
  {iri(presc.id)} rdfs:label ?ordonnance ; {prop('concernePatient')}/rdfs:label ?patient .
  OPTIONAL {{ {iri(presc.id)} {prop('prescritPar')}/rdfs:label ?medecin }}
  OPTIONAL {{ {iri(presc.id)} {prop('estDelivreePar')}/rdfs:label ?pharmacien }}
  OPTIONAL {{ {iri(presc.id)} {prop('prescritMedicament')}/rdfs:label ?med }}
}} GROUP BY ?ordonnance ?patient ?medecin ?pharmacien"""

    if intent == "alertes":
        pat = _first(ents, "PATIENT")
        return render("alertes", filters=f"FILTER(?pat = {iri(pat.id)})" if pat else "")

    if intent == "ask_patient_classe":
        pat = _first(ents, "PATIENT")
        if not pat or not classe:
            raise MissingSlot("un patient et une classe (enfant ou adulte)")
        op = "<" if classe.id == "PatientEnfant" else ">="
        return PREFIXES + f"""ASK {{
  {iri(pat.id)} a/rdfs:subClassOf* {cls('Patient')} ; {prop('age')} ?age .
  FILTER(?age {op} {AGE_ADULTE})
}}"""

    raise MissingSlot("une question sur les pathologies ou les personnes")
