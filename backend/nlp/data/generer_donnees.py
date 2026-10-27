"""Génère intents_train.json à partir de gabarits de questions ÉCRITS À LA MAIN (ci-dessous).

Chaque gabarit est instancié avec des noms tirés de l'ontologie ({MOL}, {MED}, {PATHO}, {CLASSE}, {N}).
Le jeu de TEST (intents_test.json) est écrit séparément, avec d'autres formulations et des fautes :
il n'est jamais généré par ce script.

Usage : python nlp/data/generer_donnees.py
"""
import json
import random
from pathlib import Path

random.seed(42)
OUT = Path(__file__).resolve().parent / "intents_train.json"
REPETITIONS = 2  # nombre d'instanciations par gabarit

POOLS = {
    "MOL": ["paracétamol", "ibuprofène", "aspirine", "tramadol", "codéine", "amoxicilline", "azithromycine", "metformine"],
    "MOL2": ["aspirine", "ibuprofène", "paracétamol", "tramadol"],
    "MED": ["Doliprane", "Advil", "Aspégic", "Contramal", "Clamoxyl", "Zithromax", "Glucophage", "Ibuprofène Mylan", "Amoxicilline Biogaran"],
    "MED2": ["Aspégic", "Doliprane", "Advil", "Contramal"],
    "PATHO_CI": ["ulcère", "insuffisance rénale", "insuffisance hépatique", "ulcère gastrique", "problèmes de reins", "problème de foie"],
    "PATHO": ["migraine", "angine", "pneumonie", "douleur dentaire", "diabète", "mal de tête", "mal de gorge"],
    "CLASSE": ["antibiotiques", "antalgiques", "pénicillines", "macrolides", "antalgiques opioïdes", "antalgiques non opioïdes", "antidouleurs", "opioïdes"],
    "N": ["3", "5", "7.5", "10", "4", "8", "6"],
    "N2": ["9", "12", "15"],
}

GABARITS = {
    "lister_molecules_classe": [
        "liste des {CLASSE}", "quels sont les {CLASSE}", "donne moi tous les {CLASSE}", "affiche les {CLASSE}",
        "quelles molécules sont des {CLASSE}", "montre les {CLASSE} de l'ontologie", "je veux la liste des {CLASSE}",
        "quelles sont les molécules", "liste de toutes les molécules", "quels principes actifs existent",
        "énumère les {CLASSE}", "les {CLASSE} disponibles", "quelles substances actives sont des {CLASSE}",
        "affiche toutes les molécules", "quelles molécules appartiennent à la famille des {CLASSE}", "{CLASSE} ?",
    ],
    "lister_medicaments_filtre": [
        "médicaments sans ordonnance", "quels médicaments sont vendus sans ordonnance", "liste des médicaments à moins de {N} dinars",
        "médicaments sans ordonnance à moins de {N} DT", "quels sont les médicaments génériques", "affiche les génériques",
        "médicaments sur ordonnance", "quels médicaments coûtent moins de {N} dinars", "liste des princeps",
        "médicaments en gélule", "quels médicaments existent en comprimé", "les médicaments pas chers sous {N} dt",
        "liste de tous les médicaments", "médicaments génériques sans ordonnance", "médicaments entre {N} et {N2} dinars",
        "quels médicaments coûtent plus de {N} dt", "donne les médicaments qui nécessitent une ordonnance",
        "affiche les médicaments en sachet", "quel est le médicament le plus cher", "le générique le moins cher",
        "montre moi les médicaments", "médicaments disponibles en vente libre",
    ],
    "medicaments_contenant": [
        "quels médicaments contiennent du {MOL}", "dans quels médicaments trouve t on du {MOL}", "médicaments à base de {MOL}",
        "quels produits contiennent de la {MOL}", "où trouver du {MOL}", "liste des médicaments avec {MOL}",
        "quel médicament contient du {MOL}", "le {MOL} est présent dans quels médicaments", "médicaments contenant {MOL}",
        "quels médicaments ont pour principe actif le {MOL}", "les médicaments composés de {MOL}",
        "je cherche un médicament avec du {MOL}", "quelles spécialités contiennent {MOL}", "{MOL} se trouve dans quoi",
    ],
    "molecules_de_medicament": [
        "que contient le {MED}", "quelle est la composition du {MED}", "quelle molécule contient {MED}",
        "quel est le principe actif du {MED}", "de quoi est composé le {MED}", "quelles substances actives dans {MED}",
        "{MED} contient quelle molécule", "composition du {MED}", "principe actif de {MED}",
        "quelles molécules y a t il dans le {MED}", "qu'y a t il dans le {MED}", "le {MED} est fait avec quelle molécule",
    ],
    "effets_secondaires": [
        "quels sont les effets secondaires du {MED}", "effets indésirables du {MOL}", "quels effets graves peut provoquer le {MOL}",
        "est ce que le {MED} a des effets secondaires", "effets secondaires graves du {MED}", "quels risques avec le {MOL}",
        "que peut provoquer le {MOL}", "le {MED} peut provoquer quoi", "liste des effets indésirables du {MED}",
        "les effets du {MOL}", "quels effets secondaires a le {MED}", "effets secondaires {MOL}",
        "quels sont les effets légers du {MED}", "le {MOL} provoque t il des effets graves",
    ],
    "contre_indications": [
        "quelles sont les contre indications du {MED}", "contre indications du {MOL}", "quand ne pas prendre le {MED}",
        "dans quels cas éviter le {MOL}", "le {MED} est contre indiqué dans quels cas", "qui ne doit pas prendre de {MED}",
        "précautions avec le {MOL}", "contre indication {MOL}", "quelles sont les contre indications de l'{MOL}",
        "situations où le {MED} est interdit", "le {MOL} est déconseillé quand", "{MED} contre indications",
    ],
    "contre_indiques_pour_pathologie": [
        "quels médicaments sont contre indiqués en cas de {PATHO_CI}", "médicaments à éviter avec {PATHO_CI}",
        "que ne pas prendre si j'ai un {PATHO_CI}", "médicaments déconseillés pour {PATHO_CI}", "quels médicaments éviter en cas d'{PATHO_CI}",
        "médicaments interdits avec une {PATHO_CI}", "patient avec {PATHO_CI} quels médicaments éviter",
        "quels produits sont dangereux en cas de {PATHO_CI}", "médicaments contre indiqués {PATHO_CI}",
        "liste des médicaments interdits si {PATHO_CI}", "j'ai une {PATHO_CI} que dois je éviter",
        "quels médicaments ne pas donner à un patient qui a {PATHO_CI}",
    ],
    "generique_alternative": [
        "y a t il un générique moins cher que le {MED}", "existe t il un générique du {MED}", "quelle alternative moins chère au {MED}",
        "générique du {MED}", "équivalent moins cher du {MED}", "par quoi remplacer le {MED}", "quel est le générique de {MED}",
        "le {MED} a t il un générique", "comparer le prix du {MED} avec ses génériques", "alternative au {MED}",
        "médicament équivalent au {MED}", "comment économiser sur le {MED}", "un autre médicament comme le {MED} mais moins cher",
    ],
    "interaction": [
        "{MED} et {MED2} interagissent ils", "peut on prendre {MED} avec {MED2}", "interaction entre {MOL} et {MOL2}",
        "est ce dangereux de mélanger {MED} et {MED2}", "le {MOL} interagit avec quoi", "quelles interactions pour le {MOL}",
        "puis je associer {MED} et {MED2}", "y a t il une interaction entre {MED} et {MED2}", "avec quoi le {MOL} interagit il",
        "association {MED} {MED2} risquée", "prendre {MED} en même temps que {MED2}", "interactions médicamenteuses du {MED}",
        "{MOL} et {MOL2} ensemble c'est risqué", "peut on combiner {MOL} et {MOL2}",
    ],
    "info_attribut": [
        "quel est le prix du {MED}", "combien coûte le {MED}", "quel est le code ATC du {MOL}", "code atc du {MOL}",
        "dose maximale de {MOL} par jour", "quelle est la dose max du {MOL}", "quel est le dosage du {MED}",
        "sous quelle forme est vendu le {MED}", "le {MED} est il sur ordonnance", "faut il une ordonnance pour le {MED}",
        "prix du {MED}", "le {MED} coûte combien", "forme galénique du {MED}", "le {MED} est vendu sans ordonnance",
        "donne moi les informations sur le {MED}", "fiche du {MOL}",
    ],
    "indication": [
        "pour quoi est indiqué le {MED}", "à quoi sert le {MED}", "le {MED} soigne quoi", "quelles maladies traite le {MED}",
        "quel médicament pour la {PATHO}", "quels médicaments sont indiqués pour la {PATHO}", "que prendre contre la {PATHO}",
        "médicament pour soigner une {PATHO}", "indications du {MED}", "dans quel cas utiliser le {MED}",
        "quel traitement pour la {PATHO}", "le {MED} est utilisé pour quoi", "j'ai une {PATHO} que prendre",
        "que me conseilles tu pour une {PATHO}",
    ],
    "statistiques": [
        "combien de médicaments génériques", "combien de molécules dans l'ontologie", "nombre de médicaments",
        "combien y a t il de princeps", "prix moyen des médicaments", "statistiques des médicaments",
        "combien de médicaments sans ordonnance", "quel est le prix moyen des génériques", "combien d'{CLASSE}",
        "nombre de {CLASSE}", "combien de médicaments sur ordonnance", "combien de molécules existent",
        "quel est le nombre total de médicaments", "moyenne des prix des princeps",
    ],
}


def fill(template: str) -> str:
    out = template
    for key in sorted(POOLS, key=len, reverse=True):
        token = "{" + key + "}"
        while token in out:
            out = out.replace(token, random.choice(POOLS[key]), 1)
    return out


def main():
    data = []
    seen = set()
    for intent, templates in GABARITS.items():
        for t in templates:
            wanted = REPETITIONS if "{" in t else 1
            made = tries = 0
            while made < wanted and tries < 30:
                tries += 1
                s = fill(t)
                if s not in seen:
                    seen.add(s)
                    data.append({"texte": s, "intention": intent})
                    made += 1
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {i: sum(1 for d in data if d["intention"] == i) for i in GABARITS}
    print(f"{len(data)} questions écrites dans {OUT.name}")
    print(counts)

if __name__ == "__main__":
    main()
