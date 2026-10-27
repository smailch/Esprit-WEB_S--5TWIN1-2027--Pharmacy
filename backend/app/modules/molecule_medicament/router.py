"""Routes REST du module A. Chaque réponse : {"data": ..., "sparql": [{titre, requete}, ...]}."""
from fastapi import APIRouter, HTTPException, Query

from ...graph_store import store
from . import service as S
from .queries import CATALOGUE, catalogue_entry
from .schemas import InteractionsIn, MedicamentIn, MoleculeIn, SparqlIn

router = APIRouter(tags=["Module A — Molécule + Médicament"])


def run(fn, *args, **kwargs):
    t = S.Trace()
    try:
        data = fn(t, *args, **kwargs)
    except S.NotFound as e:
        raise HTTPException(404, str(e))
    except S.Conflict as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"data": data, "sparql": t.items}


# ---------- Molécules ----------
@router.get("/molecules")
def molecules(classe: str | None = None, q: str | None = None, atc: str | None = None, tri: str = "label"):
    return run(S.list_molecules, classe=classe, q=q, atc=atc, tri=tri)


@router.get("/molecules/{mid}")
def molecule(mid: str):
    return run(S.get_molecule, mid)


@router.post("/molecules", status_code=201)
def molecule_create(body: MoleculeIn):
    return run(S.create_molecule, body)


@router.put("/molecules/{mid}")
def molecule_update(mid: str, body: MoleculeIn):
    return run(S.update_molecule, mid, body)


@router.delete("/molecules/{mid}")
def molecule_delete(mid: str):
    return run(S.delete_molecule, mid)


# ---------- Médicaments ----------
@router.get("/medicaments")
def medicaments(
    type: str | None = None, ordonnance: bool | None = None, forme: str | None = None,
    prixMin: float | None = Query(None, ge=0), prixMax: float | None = Query(None, ge=0),
    molecule: str | None = None, q: str | None = None, tri: str = "label",
):
    return run(S.list_medicaments, type=type, ordonnance=ordonnance, forme=forme, prixMin=prixMin, prixMax=prixMax, molecule=molecule, q=q, tri=tri)


@router.get("/medicaments/{mid}")
def medicament(mid: str):
    return run(S.get_medicament, mid)


@router.post("/medicaments", status_code=201)
def medicament_create(body: MedicamentIn):
    return run(S.create_medicament, body)


@router.put("/medicaments/{mid}")
def medicament_update(mid: str, body: MedicamentIn):
    return run(S.update_medicament, mid, body)


@router.delete("/medicaments/{mid}")
def medicament_delete(mid: str):
    return run(S.delete_medicament, mid)


@router.get("/medicaments/{mid}/alternatives")
def medicament_alternatives(mid: str):
    return run(S.alternatives, mid)


@router.get("/medicaments/{mid}/graphe")
def medicament_graphe(mid: str):
    return run(S.graphe_medicament, mid)


@router.post("/interactions/verifier")
def interactions(body: InteractionsIn):
    return run(S.verifier_interactions, body.medicaments)


# ---------- Référentiels, hiérarchie, stats ----------
@router.get("/hierarchie")
def hierarchie():
    return run(S.hierarchie)


@router.get("/stats")
def stats():
    return run(S.stats)


@router.get("/referentiels")
def referentiels():
    return run(S.referentiels)


# ---------- Catalogue SPARQL & console ----------
@router.get("/requetes")
def requetes():
    return {"data": [{
        "nom": nom, "titre": e["titre"], "notion": e["notion"], "requete": catalogue_entry(nom),
        "lectureSeule": e.get("lecture_seule", True),
    } for nom, e in CATALOGUE.items()], "sparql": []}


def _execute(sparql: str):
    head = " ".join(line for line in sparql.splitlines() if not line.strip().startswith(("#", "PREFIX", "prefix"))).strip().upper()
    if head.startswith("ASK"):
        return {"type": "ask", "resultat": store.ask(sparql)}
    if head.startswith("CONSTRUCT") or head.startswith("DESCRIBE"):
        g = store.construct(sparql)
        return {"type": "graphe", "triplets": len(g), "turtle": g.serialize(format="turtle")}
    rows = store.select(sparql)
    return {"type": "select", "colonnes": list(rows[0].keys()) if rows else [], "lignes": rows}


@router.post("/requetes/{nom}/executer")
def requete_executer(nom: str):
    if nom not in CATALOGUE:
        raise HTTPException(404, "Requête inconnue")
    if not CATALOGUE[nom].get("lecture_seule", True):
        raise HTTPException(400, "Requête de mise à jour : utilisez les formulaires CRUD (exemple affiché à titre pédagogique).")
    sparql = catalogue_entry(nom)
    return {"data": _execute(sparql), "sparql": [{"titre": CATALOGUE[nom]["titre"], "requete": sparql}]}


FORBIDDEN = ("INSERT", "DELETE", "LOAD", "CLEAR", "DROP", "CREATE", "ADD", "MOVE", "COPY", "SERVICE")


@router.post("/sparql")
def sparql_console(body: SparqlIn):
    upper = body.requete.upper()
    if any(f"{kw} " in upper or f"{kw}\n" in upper or f"{kw}{{" in upper for kw in FORBIDDEN):
        raise HTTPException(400, "La console est en lecture seule (SELECT, ASK, CONSTRUCT). Utilisez les formulaires pour modifier les données.")
    try:
        data = _execute(body.requete)
    except Exception as e:  # erreur de syntaxe SPARQL → message lisible
        raise HTTPException(400, f"Requête invalide : {e}")
    return {"data": data, "sparql": [{"titre": "Console", "requete": body.requete}]}
