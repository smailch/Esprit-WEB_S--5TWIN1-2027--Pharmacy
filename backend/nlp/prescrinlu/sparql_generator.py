"""Étape 5 — Génération SPARQL : un gabarit prédéfini par intention.

Seules des valeurs validées sont insérées :
- URI d'individus réellement présents dans l'ontologie (issus du dictionnaire), revérifiées par `uri()` ;
- littéraux sérialisés par rdflib (`lit`, `date_lit`) : guillemets et caractères spéciaux sont échappés ;
- opérateurs de comparaison pris dans une liste blanche.
Le texte de la question n'est donc jamais copié dans la requête (pas d'injection possible).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.prescription_clinique import queries as QD
from app.modules.prescription_clinique.common import date_lit, lit, render, uri

from .entity_extractor import Entity, Period, Threshold, first, of_type

OPERATORS = {"<", "<=", ">", ">="}


@dataclass
class Generated:
    sparql: str | None
    kind: str = "select"                      # select | ask
    explanation: list[str] = field(default_factory=list)
    filters: dict = field(default_factory=dict)


def _period_lines(period: Period | None, var: str, expl: list, filters: dict, attribut: str) -> list[str]:
    lines = []
    if period and (period.debut or period.fin):
        if period.debut:
            lines.append(f"FILTER({var} >= {date_lit(period.debut)})")
        if period.fin:
            lines.append(f"FILTER({var} <= {date_lit(period.fin)})")
        expl.append(f"FILTER sur {attribut} (xsd:date) : {period.debut or '…'} → {period.fin or '…'}")
        filters["periode"] = period.as_dict()
    return lines


def _prescription_filters(entities: list[Entity], period: Period | None, var: str = "?prescription"):
    """Lignes de filtre communes (type, patient, médecin, pharmacien, médicament, molécule, période) + explication."""
    lines, expl, filters = [], [], {}
    t = first(entities, "TYPE_PRESCRIPTION")
    if t:
        lines.append(f"{var} a {uri(t.id)} .")
        expl.append(f"{var} a :{t.id} — type de prescription (classes inférées comprises)")
        filters["type"] = t.id
    for kind, prop, key in (("PATIENT", ":concernePatient", "patient"), ("MEDECIN", ":prescritPar", "medecin"),
                            ("PHARMACIEN", ":estDelivreePar", "pharmacien")):
        e = first(entities, kind)
        if e:
            lines.append(f"{var} {prop} {uri(e.id)} .")
            expl.append(f"{var} {prop} :{e.id} — {e.label}")
            filters[key] = e.id
    for m in of_type(entities, "MEDICAMENT"):
        lines.append(f"{var} :prescritMedicament {uri(m.id)} .")
        expl.append(f"{var} :prescritMedicament :{m.id} — {m.label}")
        filters.setdefault("medicaments", []).append(m.id)
    mol = first(entities, "MOLECULE")
    if mol:
        lines.append(f"{var} :prescritMedicament/:contientMolecule {uri(mol.id)} .")
        expl.append(f"{var} :prescritMedicament/:contientMolecule :{mol.id} (chemin de propriétés)")
        filters["molecule"] = mol.id
    lines += _period_lines(period, "?date", expl, filters, ":datePrescription")
    return lines, expl, filters


def _donnee_filters(entities: list[Entity], period: Period | None):
    lines, expl, filters = [], [], {}
    t = first(entities, "TYPE_DONNEE")
    if t and t.id != "DonneeClinique":
        lines.append(f"?donnee a {uri(t.id)} .")
        expl.append(f"?donnee a :{t.id} — type de donnée clinique (sous-classes comprises)")
        filters["type"] = t.id
    pat = first(entities, "PATIENT")
    if pat:
        lines.append(f"?donnee :estDonneeDe {uri(pat.id)} .")
        expl.append(f"?donnee :estDonneeDe :{pat.id} — {pat.label}")
        filters["patient"] = pat.id
    mol = first(entities, "MOLECULE")
    if mol:
        lines.append(f"?donnee :allergiqueA {uri(mol.id)} .")
        expl.append(f"?donnee :allergiqueA :{mol.id} — allergie à {mol.label}")
        filters["molecule"] = mol.id
    patho = first(entities, "PATHOLOGIE")
    if patho:
        lines.append(f"?donnee :porteSur {uri(patho.id)} .")
        expl.append(f"?donnee :porteSur :{patho.id} — antécédent de {patho.label}")
        filters["pathologie"] = patho.id
    lines += _period_lines(period, "?date", expl, filters, ":dateMesure")
    return lines, expl, filters


def _mesure_query(mesure: Entity, patient: Entity | None, threshold: Threshold | None):
    lines, expl = [f"FILTER(STR(?examen) = {lit(mesure.id)})"], [f"examen clinique de libellé « {mesure.id} »"]
    if patient:
        lines.append(f"?donnee :estDonneeDe {uri(patient.id)} .")
        expl.append(f"?donnee :estDonneeDe :{patient.id}")
    if threshold:
        if threshold.op not in OPERATORS:
            raise ValueError("Opérateur non autorisé")
        lines.append(f"FILTER(?valeur {threshold.op} {lit(float(threshold.valeur))})")
        expl.append(f"FILTER(?valeur {threshold.op} {threshold.valeur:g}) — seuil extrait de « {threshold.texte} »")
    where = "\n  ".join(lines)
    return f"""SELECT ?patient ?nom ?donnee ?examen ?valeur ?unite ?date WHERE {{
  ?donnee a :ExamenClinique ; rdfs:label ?examen ; :valeur ?valeur ; :estDonneeDe ?patient .
  ?patient rdfs:label ?nom .
  OPTIONAL {{ ?donnee :unite ?unite }} OPTIONAL {{ ?donnee :dateMesure ?date }}
  {where}
}} ORDER BY ?nom DESC(?date)""", expl


def generate(intent: str, family: str, entities: list[Entity], period: Period | None,
             threshold: Threshold | None = None) -> Generated:
    P, PAT, MED = first(entities, "PRESCRIPTION"), first(entities, "PATIENT"), first(entities, "MEDICAMENT")

    if family in ("lister_prescriptions", "compter_prescriptions"):
        lines, expl, filters = _prescription_filters(entities, period)
        where = "\n  ".join(lines)
        if family == "compter_prescriptions":
            sparql = f"""SELECT (COUNT(DISTINCT ?prescription) AS ?nombre) WHERE {{
  ?prescription a :Prescription ; :datePrescription ?date .
  {where}
}}"""
            return Generated(sparql, explanation=["COUNT(DISTINCT ?prescription) sur les individus de type :Prescription"] + expl, filters=filters)
        sparql = f"""SELECT ?prescription ?label ?date ?patient ?medecin (GROUP_CONCAT(DISTINCT ?medLabel; separator=", ") AS ?medicaments) WHERE {{
  ?prescription a :Prescription ; rdfs:label ?label ; :datePrescription ?date ;
                :concernePatient/rdfs:label ?patient ; :prescritPar/rdfs:label ?medecin ;
                :prescritMedicament/rdfs:label ?medLabel .
  {where}
}} GROUP BY ?prescription ?label ?date ?patient ?medecin ORDER BY ?date"""
        return Generated(sparql, explanation=["Liste des ordonnances avec patient, médecin et médicaments (GROUP_CONCAT)"] + expl, filters=filters)

    if family == "prescripteur":
        if P:
            sparql = render("""SELECT ?medecin ?nom ?specialite WHERE {
  {{p}} :prescritPar ?medecin .
  ?medecin rdfs:label ?nom . OPTIONAL { ?medecin :specialite ?specialite }
}""", p=uri(P.id))
            return Generated(sparql, explanation=[f":{P.id} :prescritPar ?medecin (propriété fonctionnelle : un seul médecin)"])
        target = PAT or MED
        prop = ":concernePatient" if PAT else ":prescritMedicament"
        sparql = render("""SELECT DISTINCT ?medecin ?nom ?specialite ?prescription WHERE {
  ?prescription {{prop}} {{x}} ; :prescritPar ?medecin .
  ?medecin rdfs:label ?nom . OPTIONAL { ?medecin :specialite ?specialite }
} ORDER BY ?nom""", prop=prop, x=uri(target.id))
        return Generated(sparql, explanation=[f"?prescription {prop} :{target.id}", "?prescription :prescritPar ?medecin"])

    if family == "patient_prescription":
        sparql = render("""SELECT ?patient ?nom ?age ?sexe (GROUP_CONCAT(DISTINCT COALESCE(?patho, ""); separator=", ") AS ?pathologies) WHERE {
  {{p}} :concernePatient ?patient .
  ?patient rdfs:label ?nom .
  OPTIONAL { ?patient :age ?age } OPTIONAL { ?patient :sexe ?sexe }
  OPTIONAL { ?patient :souffreDe/rdfs:label ?patho }
} GROUP BY ?patient ?nom ?age ?sexe""", p=uri(P.id))
        return Generated(sparql, explanation=[f":{P.id} :concernePatient ?patient (propriété fonctionnelle)", "OPTIONAL : âge, sexe, pathologies"])

    if family == "patients_medicament":
        sparql = render("""SELECT DISTINCT ?patient ?nom ?prescription ?date WHERE {
  ?prescription :prescritMedicament {{m}} ; :concernePatient ?patient ; :datePrescription ?date .
  ?patient rdfs:label ?nom .
} ORDER BY ?date""", m=uri(MED.id))
        return Generated(sparql, explanation=[f"?prescription :prescritMedicament :{MED.id}", "?prescription :concernePatient ?patient"])

    if family == "pharmacien_prescription":
        sparql = render("""SELECT ?pharmacien ?nom ?specialite WHERE {
  {{p}} :estDelivreePar ?pharmacien .
  ?pharmacien rdfs:label ?nom . OPTIONAL { ?pharmacien :specialite ?specialite }
}""", p=uri(P.id))
        return Generated(sparql, explanation=[f":{P.id} :estDelivreePar ?pharmacien"])

    if family == "medicaments_prescription":
        sparql = render("""SELECT ?medicament ?label ?dosage WHERE {
  {{p}} :prescritMedicament ?medicament .
  ?medicament rdfs:label ?label . OPTIONAL { ?medicament :dosage ?dosage }
} ORDER BY ?label""", p=uri(P.id))
        return Generated(sparql, explanation=[f":{P.id} :prescritMedicament ?medicament"])

    if family == "verifier_medicament_prescription":
        sparql = render("ASK { {{p}} :prescritMedicament {{m}} }", p=uri(P.id), m=uri(MED.id))
        return Generated(sparql, "ask", [f"ASK : le triplet :{P.id} :prescritMedicament :{MED.id} existe-t-il ?"])

    if family == "verifier_medicament_patient":
        sparql = render("ASK { ?prescription :concernePatient {{x}} ; :prescritMedicament {{m}} }", x=uri(PAT.id), m=uri(MED.id))
        return Generated(sparql, "ask", [f"ASK : une ordonnance de :{PAT.id} contient-elle :{MED.id} ?"])

    if family == "verifier_type_prescription":
        t = first(entities, "TYPE_PRESCRIPTION")
        sparql = render("ASK { {{p}} a {{t}} }", p=uri(P.id), t=uri(t.id))
        return Generated(sparql, "ask", [f"ASK : :{P.id} est-elle de type :{t.id} ?",
                                         "Le type peut être déclaré ou inféré (sous-classe, ou estRenouvelable via la classe définie)"])

    if family == "details_prescription":
        sparql = render("""SELECT ?label ?date ?duree ?posologie ?renouvelable ?patient ?medecin ?pharmacien
       (GROUP_CONCAT(DISTINCT ?medLabel; separator=", ") AS ?medicaments) WHERE {
  {{p}} rdfs:label ?label ; :prescritMedicament/rdfs:label ?medLabel .
  OPTIONAL { {{p}} :datePrescription ?date } OPTIONAL { {{p}} :dureeJours ?duree }
  OPTIONAL { {{p}} :posologie ?posologie } OPTIONAL { {{p}} :estRenouvelable ?renouvelable }
  OPTIONAL { {{p}} :concernePatient/rdfs:label ?patient } OPTIONAL { {{p}} :prescritPar/rdfs:label ?medecin }
  OPTIONAL { {{p}} :estDelivreePar/rdfs:label ?pharmacien }
} GROUP BY ?label ?date ?duree ?posologie ?renouvelable ?patient ?medecin ?pharmacien""", p=uri(P.id))
        return Generated(sparql, explanation=[f"Tous les attributs et relations de :{P.id} (OPTIONAL + GROUP_CONCAT)"])

    if family == "medicaments_patient":
        lines, expl, filters = _prescription_filters([PAT], period)
        where = "\n  ".join(lines)
        sparql = f"""SELECT DISTINCT ?medicament ?label ?prescription ?date WHERE {{
  ?prescription :prescritMedicament ?medicament ; :datePrescription ?date .
  ?medicament rdfs:label ?label .
  {where}
}} ORDER BY ?date ?label"""
        return Generated(sparql, explanation=expl + ["?prescription :prescritMedicament ?medicament"], filters=filters)

    if family == "verifier_contre_indication":
        expl = ["UNION de 4 raisonnements : pathologie déclarée, allergie, antécédent, clairance de la créatinine < 60"]
        filters, restriction = {}, ""
        if PAT:
            restriction = f"FILTER(?pat = {uri(PAT.id)})"
            expl.append(f"FILTER(?pat = :{PAT.id}) — restreint au patient")
            filters["patient"] = PAT.id
        elif P:
            restriction = f"FILTER(?presc = {uri(P.id)})"
            expl.append(f"FILTER(?presc = :{P.id}) — restreint à l'ordonnance")
            filters["prescription"] = P.id
        return Generated(QD.catalogue_entry("D06_alertes_prescriptions", restriction=restriction), explanation=expl, filters=filters)

    if family == "chaine_patient":
        return Generated(QD.catalogue_entry("D07_chaine_patient", patient=uri(PAT.id)),
                         explanation=[f"Parcours :{PAT.id} ← concernePatient ← ?prescription → prescritMedicament → contientMolecule → aContreIndication → concernePathologie",
                                      "BIND(EXISTS { pathologie actuelle ou antécédent du patient }) marque le conflit"])

    # ---------------- Données cliniques ----------------
    if family in ("lister_donnees", "compter_donnees"):
        lines, expl, filters = _donnee_filters(entities, period)
        where = "\n  ".join(lines)
        if family == "compter_donnees":
            sparql = f"""SELECT (COUNT(DISTINCT ?donnee) AS ?nombre) WHERE {{
  ?donnee a :DonneeClinique .
  OPTIONAL {{ ?donnee :dateMesure ?date }}
  {where}
}}"""
            return Generated(sparql, explanation=["COUNT(DISTINCT ?donnee) sur les individus de type :DonneeClinique"] + expl, filters=filters)
        sparql = f"""SELECT ?donnee ?label ?patient ?valeur ?unite ?date ?detail WHERE {{
  ?donnee a :DonneeClinique ; rdfs:label ?label ; :estDonneeDe/rdfs:label ?patient .
  OPTIONAL {{ ?donnee :valeur ?valeur }} OPTIONAL {{ ?donnee :unite ?unite }} OPTIONAL {{ ?donnee :dateMesure ?date }}
  OPTIONAL {{ ?donnee :allergiqueA/rdfs:label ?molDetail }} OPTIONAL {{ ?donnee :porteSur/rdfs:label ?pathoDetail }}
  BIND(COALESCE(?molDetail, ?pathoDetail) AS ?detail)
  {where}
}} ORDER BY ?patient DESC(?date)"""
        return Generated(sparql, explanation=["Données cliniques avec patient (estDonneeDe), valeur, unité, date et détail "
                                              "(allergiqueA / porteSur)"] + expl, filters=filters)

    if family in ("valeur_mesure", "seuil_mesure"):
        sparql, expl = _mesure_query(first(entities, "MESURE"), PAT, threshold if family == "seuil_mesure" else None)
        return Generated(sparql, explanation=expl, filters={"seuil": threshold.as_dict()} if threshold and family == "seuil_mesure" else {})

    if family == "verifier_allergie":
        mol = first(entities, "MOLECULE")
        if mol:
            sparql = render("ASK { ?allergie a :Allergie ; :estDonneeDe {{p}} ; :allergiqueA {{m}} }", p=uri(PAT.id), m=uri(mol.id))
            return Generated(sparql, "ask", [f"ASK : une :Allergie de :{PAT.id} porte-t-elle sur :{mol.id} ?"])
        sparql = render("ASK { ?allergie a :Allergie ; :estDonneeDe {{p}} ; :allergiqueA ?mol . {{m}} :contientMolecule ?mol }",
                        p=uri(PAT.id), m=uri(MED.id))
        return Generated(sparql, "ask", [f"ASK : :{PAT.id} est-il allergique à une molécule contenue dans :{MED.id} ?"])

    raise ValueError(f"Intention sans gabarit : {family}")
