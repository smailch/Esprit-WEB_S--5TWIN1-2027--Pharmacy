"""Étape 4 — Contraintes : âge (plus de / moins de / entre), sexe, négation, cible d'un comptage."""
import re

SENIOR_AGE = 65


def extract(norm: str) -> dict:
    t = " " + re.sub(r"\s+", " ", norm) + " "
    c: dict = {}

    if m := re.search(r" entre (\d{1,3}) (?:ans )?et (\d{1,3})", t):
        c["age_min"], c["age_max"] = sorted((int(m.group(1)), int(m.group(2))))
    else:
        if m := re.search(r" (?:plus de|au dessus de|superieur a|depassant|over) (\d{1,3})", t):
            c["age_min"] = int(m.group(1)) + 1
        if m := re.search(r" (?:au moins|minimum) (\d{1,3})| (\d{1,3}) ans et plus", t):
            c["age_min"] = int(m.group(1) or m.group(2))
        if m := re.search(r" (?:moins de|en dessous de|inferieur a) (\d{1,3})", t):
            c["age_max"] = int(m.group(1)) - 1
        if m := re.search(r" (?:au plus|maximum) (\d{1,3})", t):
            c["age_max"] = int(m.group(1))
        if not c and (m := re.search(r" (?:de|ont|a|age de|agee? de) (\d{1,3}) ans ", t)):
            c["age_min"] = c["age_max"] = int(m.group(1))
    if re.search(r" (seniors?|personnes? agees?|vieux|ages|agees|3e age|troisieme age) ", t) and "age_min" not in c:
        c["age_min"] = SENIOR_AGE

    if re.search(r" (femmes?|patientes?|feminin|filles?|sexe f) ", t):
        c["sexe"] = "F"
    elif re.search(r" (hommes?|masculin|garcons?|sexe m) ", t):
        c["sexe"] = "M"

    if re.search(r" (sans|aucune?|ne \w+ pas|n \w+ pas|pas de) ", t):
        c["negation"] = True

    if re.search(r" (medecins?|docteurs?) ", t):
        c["cible"] = "Medecin"
    elif re.search(r" (pharmaciens?|pharmaciennes?|pharma) ", t):
        c["cible"] = "Pharmacien"
    elif re.search(r" (pathologies?|maladies?) ", t) and not re.search(r" (patients?|patientes?) ", t):
        c["cible"] = "Pathologie"
    return c
