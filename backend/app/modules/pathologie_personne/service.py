"""Logique métier Pathologie / Personne au-dessus des requêtes nommées."""
from __future__ import annotations

from .mapping import (AGE_ADULTE, C, P, PATHOLOGY_FAMILY, PATHOLOGY_TYPES,
                                         URI_PREFIX, cls, iri, prop)
from .text import normalize, pascal_case, sparql_norm
from .client import StoreClient
from .templates import check_local, escape_literal, fmt, render


class NotFound(Exception):
    pass


class Conflict(Exception):
    def __init__(self, message: str, details=None):
        super().__init__(message)
        self.details = details


def _text_filter(q: str | None, *vars_: str) -> str:
    if not q:
        return ""
    parts = ", \" \", ".join(f'COALESCE(STR({v}), "")' for v in vars_)
    return f"FILTER(CONTAINS({sparql_norm(f'CONCAT({parts})')}, {escape_literal(normalize(q))}))"


class Repository:
    def __init__(self, client: StoreClient):
        self.sparql = client

    # ---------- utilitaires ----------
    def _select(self, name, **params):
        return self.sparql.select(render(name, **params)).rows

    def _ask(self, name, **params) -> bool:
        return self.sparql.ask(render(name, **params))

    def _update(self, name, **params):
        self.sparql.update(render(name, **params))

    def _total(self, name, **params) -> int:
        rows = self._select(name, **params)
        return int(rows[0]["total"]) if rows else 0

    def exists(self, local: str) -> bool:
        return self._ask("ask_exists", s=local)

    def _new_id(self, local: str) -> str:
        check_local(local)
        if self.exists(local):
            raise Conflict(f"L'identifiant {local} existe déjà", {"id": local})
        return local

    def _references(self, local: str) -> list[dict]:
        return [{"id": r["id"], "label": r.get("label"), "relation": r["prop"]}
                for r in self._select("entity_graph", s=local) if r["dir"] == "in"]

    # ---------- patients ----------
    def _patient_filters(self, q=None, sexe=None, age_min=None, age_max=None, pathologie=None, classe=None):
        f = [_text_filter(q, "?label", "?nom")]
        if sexe:
            f.append(f"FILTER(?sexe = {escape_literal(sexe)})")
        if age_min is not None:
            f.append(f"FILTER(?age >= {fmt(age_min, 'int')})")
        if age_max is not None:
            f.append(f"FILTER(?age <= {fmt(age_max, 'int')})")
        if pathologie:
            f.append(f"FILTER EXISTS {{ ?p {prop('souffreDe')} {iri(check_local(pathologie))} }}")
        if classe == C["PatientEnfant"]:
            f.append(f"FILTER(?age < {AGE_ADULTE})")
        elif classe == C["PatientAdulte"]:
            f.append(f"FILTER(?age >= {AGE_ADULTE})")
        return "\n  ".join(x for x in f if x)

    def list_patients(self, limit=20, offset=0, **filters):
        flt = self._patient_filters(**filters)
        items = self._select("list_patients", filters=flt, limit=limit, offset=offset)
        return items, self._total("count_patients", filters=flt)

    def get_patient(self, pid: str) -> dict:
        rows = self._select("patient_detail", s=check_local(pid))
        if not rows:
            raise NotFound(f"Patient {pid} introuvable")
        return {"id": pid, **rows[0],
                "pathologies": self._select("patient_pathologies", s=pid),
                "prescriptions": self._select("patient_prescriptions", s=pid),
                "alertes": self.alertes(patient=pid)}

    def create_patient(self, prenom: str, nom: str, age: int, sexe: str, pathologies=()) -> str:
        pid = self._new_id(URI_PREFIX["Patient"] + pascal_case(prenom))
        for patho in pathologies:
            self.get_pathologie(patho)
        self._update("create_patient", s=pid, label=f"{prenom} {nom}".strip(), nom=nom, age=age, sexe=sexe)
        for patho in pathologies:
            self._update("add_souffre_de", s=pid, patho=patho)
        return pid

    def update_patient(self, pid: str, label=None, nom=None, age=None, sexe=None):
        self.get_patient(pid)
        if label is not None:
            self._update("update_label", s=pid, label=label)
        if nom is not None:
            self._update("update_value", s=pid, p=P["nom"], value=fmt(nom, "lit"))
        if age is not None:
            self._update("update_value", s=pid, p=P["age"], value=fmt(age, "int"))
        if sexe is not None:
            self._update("update_value", s=pid, p=P["sexe"], value=fmt(sexe, "lit"))

    def add_patient_pathology(self, pid: str, patho: str):
        self.get_patient(pid)
        self.get_pathologie(patho)
        self._update("add_souffre_de", s=pid, patho=patho)

    def remove_patient_pathology(self, pid: str, patho: str):
        self.get_patient(pid)
        self._update("remove_souffre_de", s=check_local(pid), patho=check_local(patho))

    def delete_patient(self, pid: str):
        self.get_patient(pid)
        if self._ask("ask_patient_references", s=pid):
            raise Conflict("Suppression refusée : le patient est lié à une prescription ou à une donnée clinique",
                           self._references(pid))
        self._update("delete_entity", s=pid)

    # ---------- professionnels de santé ----------
    def _pro_class(self, classe: str) -> str:
        if classe not in (C["Medecin"], C["Pharmacien"]):
            raise NotFound(f"Classe inconnue : {classe}")
        return classe

    def list_professionnels(self, classe: str, limit=20, offset=0, q=None, specialite=None):
        self._pro_class(classe)
        flt = [_text_filter(q, "?label", "?nom", "?specialite")]
        if specialite:
            flt.append(f"FILTER(CONTAINS({sparql_norm('STR(?specialite)')}, {escape_literal(normalize(specialite))}))")
        flt = "\n  ".join(x for x in flt if x)
        items = self._select("list_professionnels", classe=classe, filters=flt, limit=limit, offset=offset)
        return items, self._total("count_professionnels", classe=classe, filters=flt)

    def get_professionnel(self, classe: str, pid: str) -> dict:
        rows = self._select("professionnel_detail", s=check_local(pid))
        if not rows or rows[0]["classe"] != self._pro_class(classe):
            raise NotFound(f"{classe} {pid} introuvable")
        first = rows[0]
        prescriptions = [{"id": r["prescId"], "label": r["prescLabel"], "patient": r.get("patient"),
                          "patientId": r.get("patientId"), "role": r["role"]}
                         for r in rows if r.get("prescId")]
        return {"id": pid, "label": first["label"], "nom": first.get("nom"),
                "specialite": first.get("specialite"), "classe": classe, "prescriptions": prescriptions}

    def create_professionnel(self, classe: str, nom: str, specialite: str, label: str | None = None) -> str:
        self._pro_class(classe)
        pid = self._new_id(URI_PREFIX[classe] + pascal_case(nom))
        if not label:
            label = f"Dr {nom}" if classe == C["Medecin"] else f"Pharmacien {nom}"
        self._update("create_professionnel", s=pid, classe=classe, label=label, nom=nom, specialite=specialite)
        return pid

    def update_professionnel(self, classe: str, pid: str, label=None, nom=None, specialite=None):
        self.get_professionnel(classe, pid)
        if label is not None:
            self._update("update_label", s=pid, label=label)
        if nom is not None:
            self._update("update_value", s=pid, p=P["nom"], value=fmt(nom, "lit"))
        if specialite is not None:
            self._update("update_value", s=pid, p=P["specialite"], value=fmt(specialite, "lit"))

    def delete_professionnel(self, classe: str, pid: str):
        self.get_professionnel(classe, pid)
        if self._ask("ask_professionnel_references", s=pid):
            raise Conflict("Suppression refusée : ce professionnel a prescrit ou délivré une ordonnance",
                           self._references(pid))
        self._update("delete_entity", s=pid)

    # ---------- pathologies ----------
    def list_pathologies(self, limit=50, offset=0, q=None, famille=None, type=None):
        flt = [_text_filter(q, "?label", "?code")]
        for t in (famille, type):
            if t:
                if t not in PATHOLOGY_FAMILY:
                    raise NotFound(f"Type de pathologie inconnu : {t}")
                flt.append(f"FILTER EXISTS {{ ?p a/rdfs:subClassOf* {cls(t)} }}")
        flt = "\n  ".join(x for x in flt if x)
        items = self._select("list_pathologies", filters=flt, limit=limit, offset=offset)
        return items, self._total("count_pathologies", filters=flt)

    def get_pathologie(self, pid: str) -> dict:
        rows = self._select("pathologie_detail", s=check_local(pid))
        if not rows:
            raise NotFound(f"Pathologie {pid} introuvable")
        meds = self._select("pathologie_medicaments", s=pid)
        return {"id": pid, **rows[0],
                "indiques": [m for m in meds if m["relation"] == "indiqué"],
                "contreIndiques": [m for m in meds if m["relation"] == "contre-indiqué"],
                "patients": self._select("pathologie_patients", s=pid)}

    def create_pathologie(self, label: str, type: str, code: str) -> str:
        if type not in PATHOLOGY_TYPES:
            raise NotFound(f"Type de pathologie inconnu : {type}")
        pid = self._new_id(pascal_case(label))
        self._update("create_pathologie", s=pid, classe=C[type], label=label, code=code)
        return pid

    def update_pathologie(self, pid: str, label=None, code=None):
        self.get_pathologie(pid)
        if label is not None:
            self._update("update_label", s=pid, label=label)
        if code is not None:
            self._update("update_value", s=pid, p=P["codeCIM10"], value=fmt(code, "lit"))

    def delete_pathologie(self, pid: str):
        self.get_pathologie(pid)
        if self._ask("ask_pathologie_references", s=pid):
            raise Conflict("Suppression refusée : la pathologie est référencée (patient, contre-indication, "
                           "médicament ou antécédent)", self._references(pid))
        self._update("delete_entity", s=pid)

    # ---------- transversal ----------
    def alertes(self, patient: str | None = None) -> list[dict]:
        flt = f"FILTER(?pat = {iri(check_local(patient))})" if patient else ""
        return self._select("alertes", filters=flt)

    def stats(self) -> dict:
        return {"compteurs": self._select("stats_compteurs")[0],
                "patientsParPathologie": self._select("stats_patients_par_pathologie", min=1),
                "tranchesAge": self._select("stats_tranches_age"),
                "specialites": self._select("stats_specialites"),
                "alertes": len(self.alertes())}

    def search(self, q: str) -> list[dict]:
        return self._select("search", q=normalize(q))

    def describe_patient(self, pid: str) -> str:
        self.get_patient(pid)
        return self.sparql.graph(render("describe_patient", s=pid))
