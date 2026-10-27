"""Extraction des filtres (« slots ») par règles : prix, ordonnance, type, forme, gravité, attribut demandé."""
import re

NUM = r"(\d+(?:\.\d+)?)"


def extract_slots(text: str) -> dict:
    """`text` : question normalisée (minuscules, sans accents)."""
    s: dict = {}

    m = re.search(rf"entre\s*{NUM}\s*(?:dt|dinars?)?\s*et\s*{NUM}", text)
    if m:
        s["prixMin"], s["prixMax"] = float(m.group(1)), float(m.group(2))
    else:
        m = re.search(rf"(?:moins de|inferieure? a|en dessous de|sous|<|maximum|max|pas plus de|au plus)\s*{NUM}", text)
        if m:
            s["prixMax"] = float(m.group(1))
        m = re.search(rf"(?:plus de|superieure? a|au dessus de|>|au moins|minimum)\s*{NUM}", text)
        if m:
            s["prixMin"] = float(m.group(1))

    if re.search(r"\bsans ordonnance\b|\ben vente libre\b|\bsans prescription\b", text):
        s["ordonnance"] = False
    elif re.search(r"\b(sur|avec) ordonnance\b|\bnecessit\w* (une )?ordonnance\b|\bbesoin d'?\s?une ordonnance\b|\bsoumis a prescription\b", text):
        s["ordonnance"] = True

    if re.search(r"\bgeneriques?\b", text):
        s["type"] = "Generique"
    elif re.search(r"\bprinceps\b|\bmedicaments? d'? ?origine\b|\bmarque\b", text):
        s["type"] = "Princeps"

    m = re.search(r"\b(comprimes?|gelules?|sachets?|sirops?|injectables?)\b", text)
    if m:
        s["forme"] = {"comprime": "comprimé", "gelule": "gélule"}.get(m.group(1).rstrip("s"), m.group(1).rstrip("s"))

    if re.search(r"\bgraves?\b|\bdangereux\b|\bserieux\b|\bsevere", text):
        s["gravite"] = "grave"
    elif re.search(r"\blegers?\b|\bbenins?\b", text):
        s["gravite"] = "léger"

    if re.search(r"\ble plus cher\b|\bles plus chers\b|\bplus couteux\b", text):
        s["superlatif"] = "max"
    elif re.search(r"\ble moins cher\b|\bles moins chers\b|\bmoins couteux\b", text) and not re.search(r"moins cher (que|qu)", text):
        s["superlatif"] = "min"

    if re.search(r"\bcode atc\b|\batc\b", text):
        s["attribut"] = "codeATC"
    elif re.search(r"\bdose\b|\bposologie max", text):
        s["attribut"] = "doseMaxJourMg"
    elif re.search(r"\bdosage\b|\bcombien de mg\b", text):
        s["attribut"] = "dosage"
    elif re.search(r"\bprix\b|\bcoute\w*\b|\bcout\b|\bcombien\b.*\b(dt|dinars?)\b|\btarif\b", text):
        s["attribut"] = "prixDT"
    elif re.search(r"\bforme\b|\bgalenique\b|\bpresentation\b", text):
        s["attribut"] = "formeGalenique"
    elif re.search(r"\bordonnance\b", text):
        s["attribut"] = "surOrdonnance"

    if re.search(r"\bprix moyen\b|\bmoyenne\b", text):
        s["moyenne"] = True
    return s
