"""Génère docs/Presentation_Module_A.pdf (2 pages A4) — fiche de présentation du module A.

Usage : python docs/generer_pdf.py   (nécessite reportlab ; polices Segoe UI de Windows)
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

OUT = Path(__file__).resolve().parent / "Presentation_Module_A.pdf"
FONTS = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("UI", FONTS / "segoeui.ttf"))
pdfmetrics.registerFont(TTFont("UI-B", FONTS / "segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("UI-SB", FONTS / "seguisb.ttf"))
pdfmetrics.registerFont(TTFont("UI-L", FONTS / "segoeuil.ttf"))
pdfmetrics.registerFont(TTFont("Mono", FONTS / "consola.ttf") if (FONTS / "consola.ttf").exists() else TTFont("Mono", FONTS / "segoeui.ttf"))
pdfmetrics.registerFontFamily("UI", normal="UI", bold="UI-B", italic="UI", boldItalic="UI-B")

FOREST = colors.HexColor("#1E3227")
GREEN = colors.HexColor("#3F5447")
GOLD = colors.HexColor("#9B8A3E")
SAGE = colors.HexColor("#CBCFB8")
SAGE_L = colors.HexColor("#E6E8DC")
IVORY = colors.HexColor("#F2F0EC")
LINE = colors.HexColor("#B9BEA3")

S = {
    "body": ParagraphStyle("body", fontName="UI", fontSize=8.6, leading=11.6, textColor=FOREST),
    "small": ParagraphStyle("small", fontName="UI", fontSize=7.8, leading=10.2, textColor=GREEN),
    "cell": ParagraphStyle("cell", fontName="UI", fontSize=7.9, leading=10.2, textColor=FOREST),
    "cellb": ParagraphStyle("cellb", fontName="UI-SB", fontSize=7.9, leading=10.2, textColor=FOREST),
    "h2": ParagraphStyle("h2", fontName="UI-SB", fontSize=10.5, leading=13, textColor=FOREST, spaceBefore=7, spaceAfter=3),
    "kpi": ParagraphStyle("kpi", fontName="UI-L", fontSize=17, leading=19, textColor=FOREST),
    "kpil": ParagraphStyle("kpil", fontName="UI", fontSize=7.2, leading=9, textColor=GREEN),
}


def p(text, style="body"):
    return Paragraph(text, S[style])


def h2(num, text):
    return Paragraph(f'<font color="#9B8A3E">{num}</font>&nbsp;&nbsp;{text}', S["h2"])


def table(rows, widths, header=True, zebra=True):
    data = [[p(c, "cellb" if (header and i == 0) or j == 0 else "cell") if isinstance(c, str) else c for j, c in enumerate(r)] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), SAGE), ("LINEBELOW", (0, 0), (-1, 0), 0.8, GREEN)]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), SAGE_L))
    t.setStyle(TableStyle(style))
    return t


def kpis(items, width):
    cells = [[Paragraph(v, S["kpi"]), ] for v, _ in items]
    row1 = [Paragraph(v, S["kpi"]) for v, _ in items]
    row2 = [Paragraph(l, S["kpil"]) for _, l in items]
    t = Table([row1, row2], colWidths=[width / len(items)] * len(items))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), IVORY),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
    ]))
    del cells
    return t


def header_footer(canvas, doc):
    w, h = A4
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(FOREST)
        canvas.rect(0, h - 34 * mm, w, 34 * mm, stroke=0, fill=1)
        canvas.setFillColor(GOLD)
        canvas.setFont("UI-SB", 7.5)
        canvas.drawString(16 * mm, h - 11 * mm, "WEB SÉMANTIQUE  ·  ESPRIT 5 TWIN  ·  2026–2027  ·  VALIDATION FINALE")
        canvas.setFillColor(IVORY)
        canvas.setFont("UI-L", 21)
        canvas.drawString(16 * mm, h - 21 * mm, "Module A — Molécule + Médicament")
        canvas.setFont("UI", 9)
        canvas.drawString(16 * mm, h - 28 * mm, "Projet PharmaSémantique · Ontologie Pharmaceutique et Santé · équipe NeoCoders · réalisé par Chemlali Ismail")
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.2)
        canvas.circle(w - 26 * mm, h - 17 * mm, 8 * mm, stroke=1, fill=0)
        canvas.setFillColor(GOLD)
        canvas.setFont("UI-B", 13)
        canvas.drawCentredString(w - 26 * mm, h - 19.2 * mm, "A")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(16 * mm, 12 * mm, w - 16 * mm, 12 * mm)
    canvas.setFillColor(GREEN)
    canvas.setFont("UI", 7)
    canvas.drawString(16 * mm, 8 * mm, "Dépôt : github.com/smailch/Esprit-WEB_S--5TWIN1-2027--Pharmacy  ·  données fictives, aucune recommandation médicale")
    canvas.drawRightString(w - 16 * mm, 8 * mm, f"{doc.page} / 2")
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Module A — Molécule + Médicament", author="Chemlali Ismail (NeoCoders)", subject="PharmaSémantique — Web Sémantique 5 TWIN")
    W = A4[0] - 32 * mm
    st = [Spacer(1, 23 * mm)]  # place réservée au bandeau de titre de la page 1

    # ---------------------------------------------------------------- page 1
    st.append(p("<b>Objectif.</b> Exploiter la partie <b>Molécule</b> et <b>Médicament</b> de l’ontologie à travers une application web complète : "
                "back-end SPARQL avec inférence OWL, interface graphique, CRUD, et un <b>assistant qui traduit une question en français en requête SPARQL</b> "
                "à l’aide de bibliothèques de NLP (spaCy, scikit-learn, RapidFuzz) — <b>sans aucune API de LLM</b>."))

    st.append(h2("1", "Partie de l’ontologie couverte"))
    st.append(table([
        ["Élément", "Contenu (ontologie/pharma.ttl)"],
        ["Classes (3 niveaux)", "Molecule → Antibiotique (Pénicilline, Macrolide) · Antalgique (non opioïde, opioïde) — Medicament → Princeps · Générique → …SurOrdonnance / …SansOrdonnance"],
        ["Object properties", "contientMolecule ↔ estContenuDans (inverses) · interagitAvec (symétrique) · peutProvoquer · aContreIndication · estIndiquePour · estContreIndiquePour (chaîne OWL)"],
        ["Data properties", "codeATC, doseMaxJourMg (molécule) · nomCommercial, dosage, formeGalenique, surOrdonnance, prixDT (médicament)"],
        ["Axiomes exploités", "classes définies (owl:equivalentClass) Princeps/Générique sur/sans ordonnance · ≥ 1 molécule par médicament · disjonctions"],
        ["Individus", "8 molécules (Paracétamol, Ibuprofène, Aspirine, Tramadol, Codéine, Amoxicilline, Azithromycine, Metformine) · 9 médicaments"],
    ], [30 * mm, W - 30 * mm]))

    st.append(h2("2", "Architecture et communication back-end ↔ front-end"))
    st.append(table([
        ["Couche", "Technologies", "Rôle"],
        ["Données", "RDF/OWL (Turtle), owlrl", "Ontologie chargée en mémoire ; le raisonneur OWL 2 RL écrit les faits déduits dans un <b>graphe nommé séparé</b> (déclaré vs inféré)"],
        ["Back-end", "Python, FastAPI, rdflib", "API REST JSON (19 routes) ; <b>chaque réponse renvoie les requêtes SPARQL exécutées</b> ; paramètres échappés, identifiants validés"],
        ["Front-end", "React 18, Vite, React Router", "Site vitrine + 6 pages ; appels via un client HTTP unique (proxy /api) ; états chargement / erreur / vide"],
        ["IA", "spaCy, scikit-learn, RapidFuzz", "Modèle local PharmaNLU-A (253 Ko) exposé par POST /api/nlp/ask"],
    ], [20 * mm, 40 * mm, W - 60 * mm]))
    st.append(Spacer(1, 2))
    st.append(p("Le CRUD écrit dans <font face='Mono'>backend/data/runtime.ttl</font> : l’ontologie commune de l’équipe n’est jamais modifiée (bouton « Réinitialiser »).", "small"))

    st.append(h2("3", "Requêtes SPARQL — 16 requêtes nommées, exécutables depuis la console"))
    q = [
        ("Q01 / Q02", "Hiérarchie <i>rdfs:subClassOf+</i> ; appartenance indirecte <i>rdf:type/rdfs:subClassOf*</i>"),
        ("Q03 / Q04", "FILTER numérique + booléen, ORDER BY ; recherche REGEX insensible à la casse + UNION"),
        ("Q05", "Propriété inverse <i>estContenuDans</i> (déduite par le raisonneur)"),
        ("Q06", "Génériques de même composition : double FILTER NOT EXISTS + économie calculée (BIND)"),
        ("Q07 / Q07b", "Interactions (propriété symétrique) et doublons de principe actif, VALUES"),
        ("Q08", "Chaîne contientMolecule/aContreIndication/concernePathologie (≡ owl:propertyChainAxiom)"),
        ("Q09 / Q10", "OPTIONAL + FILTER ; agrégats COUNT, AVG, MIN, MAX, GROUP BY, HAVING"),
        ("Q11 / Q12 / Q13", "Négation FILTER NOT EXISTS ; requête ASK ; requête CONSTRUCT (graphe affiché)"),
        ("Q14", "CRUD : INSERT DATA, DELETE/INSERT WHERE, DELETE WHERE"),
        ("Q15", "Types inférés non déclarés : comparaison de graphes nommés (GRAPH)"),
    ]
    half = (len(q) + 1) // 2
    left = table([["Requêtes", "Notion SPARQL"]] + [list(x) for x in q[:half]], [19 * mm, W / 2 - 21 * mm])
    right = table([["Requêtes", "Notion SPARQL"]] + [list(x) for x in q[half:]], [22 * mm, W / 2 - 24 * mm])
    two = Table([[left, right]], colWidths=[W / 2, W / 2])
    two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 4), ("LEFTPADDING", (1, 0), (1, 0), 4)]))
    st.append(two)

    st.append(h2("4", "Interfaces graphiques"))
    st.append(table([
        ["Page", "Fonctionnalités"],
        ["Molécules", "Tableau filtrable (classe via la hiérarchie, code ATC, recherche avec ou sans accents), arbre à 3 niveaux, fiche détaillée, création / modification / suppression"],
        ["Médicaments", "Cartes filtrables (type, ordonnance, forme, curseur de prix), statistiques SPARQL, fiche avec contre-indications déduites et graphe interactif, CRUD"],
        ["Comparateur · Interactions", "Princeps ↔ génériques avec économie en DT et % · vérification d’une association de 2 à 10 médicaments"],
        ["Assistant IA · Console", "Questions en langage naturel · catalogue des 16 requêtes en un clic + éditeur (lecture seule), export CSV"],
    ], [34 * mm, W - 34 * mm]))
    st.append(Spacer(1, 2))
    st.append(p("Sur chaque page, un panneau « Requêtes SPARQL exécutées » montre exactement ce qui a été envoyé au serveur. Badges « inféré » sur les faits déduits.", "small"))

    st.append(PageBreak())

    # ---------------------------------------------------------------- page 2
    st.append(h2("5", "Module IA — modèle « PharmaNLU-A » : question en français → requête SPARQL"))
    st.append(p("Modèle <b>hybride</b> développé par nous : classifieur supervisé + règles linguistiques. Il n’utilise <b>aucun LLM</b> (ni OpenAI, ni Gemini) : "
                "tout est exécuté localement et le modèle entraîné est versionné dans le dépôt Git."))
    st.append(Spacer(1, 4))
    st.append(table([
        ["Étape", "Bibliothèque", "Traitement — exemple « Quels médicaments contiennent de l’ibuprophène ? »"],
        ["1. Normalisation", "spaCy 3.8 + fr_core_news_sm", "minuscules, accents, tokenisation, lemmatisation (contiennent → contenir)"],
        ["2. Entités", "spaCy EntityRuler", "dictionnaire <b>généré automatiquement depuis l’ontologie</b> (un médicament ajouté par le CRUD est reconnu sans ré-entraîner)"],
        ["3. Fautes de frappe", "RapidFuzz 3.14", "« ibuprophene » → <b>Ibuprofène</b> (similarité 86 %)"],
        ["4. Délexicalisation", "—", "les entités deviennent xmol / xmed / xpatho / xclasse : « quel medicament contenir de le xmol »"],
        ["5. Intention", "scikit-learn 1.9", "TF-IDF mots (1–2-grammes) + caractères (3–5) → régression logistique : 12 intentions, confiance 97 %"],
        ["6. Filtres", "règles (regex)", "prix (« moins de 5 dinars »), ordonnance, générique/princeps, forme, gravité, attribut demandé"],
        ["7. SPARQL", "gabarits + rdflib", "gabarit de l’intention rempli avec l’URI :Ibuprofene → exécution → réponse en français + requête affichée"],
    ], [27 * mm, 37 * mm, W - 64 * mm]))
    st.append(Spacer(1, 5))
    st.append(kpis([("96,9 %", "intentions correctes sur 96 questions de test jamais vues"), ("100 %", "entités reconnues sur le jeu de test"),
                    ("314", "questions d’entraînement (gabarits écrits à la main)"), ("12", "intentions → 12 gabarits SPARQL")], W))
    st.append(Spacer(1, 3))
    st.append(p("Sécurité : sous 40 % de confiance, aucune requête n’est générée (« je n’ai pas compris ») ; s’il manque une entité, l’assistant le dit précisément. "
                "La page « À propos du modèle » affiche les bibliothèques, la précision et le F1 par intention. Entraînement reproductible (graine 42) : "
                "<font face='Mono'>python -m nlp.train</font>.", "small"))

    st.append(h2("6", "Valeur ajoutée"))
    st.append(table([
        ["Comparateur princeps / générique", "Trouve les médicaments de composition identique et calcule l’économie : Advil 6,50 DT → Ibuprofène Mylan 3,90 DT (−40 %)."],
        ["Vérificateur d’interactions", "Détecte les interactions (déclarées dans un seul sens, déduites dans l’autre grâce à la symétrie OWL) et les doublons de principe actif."],
        ["IA explicable", "Intention, confiance, entités corrigées, étapes du pipeline et requête SPARQL commentée affichées pour chaque question."],
        ["Inférence visible", "Badges « inféré » : classes définies, propriétés inverses et symétriques, contre-indications déduites par la chaîne de propriétés."],
        ["Qualité", "36 tests automatisés (API, requêtes, NLP), graphe CONSTRUCT interactif, export CSV, historique des questions, responsive mobile."],
    ], [44 * mm, W - 44 * mm], header=False))

    st.append(h2("7", "Scénario de démonstration (≈ 5 minutes)"))
    steps = [
        "Accueil (site vitrine) → « Ouvrir l’application » : l’API affiche le nombre de triplets déclarés et inférés.",
        "Assistant : « quels médicaments contiennent de l’ibuprophene » (faute volontaire) → Advil, Ibuprofène Mylan ; intention, confiance, requête générée.",
        "Comparateur : Advil → Ibuprofène Mylan, économie de 40 %.",
        "Interactions : Advil + Aspégic → interaction ibuprofène ↔ aspirine ; + Ibuprofène Mylan → alerte doublon.",
        "CRUD : création de « Paracétamol Biogaran » (générique, sans ordonnance) → classé automatiquement <i>GeneriqueSansOrdonnance</i> (inféré) et reconnu par l’assistant.",
        "Console SPARQL : chaîne de propriétés (Q08), agrégats + HAVING (Q10), NOT EXISTS (Q11), types inférés (Q15) — puis « Réinitialiser les données ».",
    ]
    st.append(table([[f"{i}", s] for i, s in enumerate(steps, 1)], [7 * mm, W - 7 * mm], header=False))

    st.append(h2("8", "Installation et portabilité"))
    inst = table([
        ["Installer", "<font face='Mono'>git clone …</font> puis <font face='Mono'>scripts\\setup.bat</font> (Windows) ou <font face='Mono'>scripts/setup.sh</font>"],
        ["Lancer", "<font face='Mono'>scripts\\start.bat</font> → site http://localhost:5173 · API documentée http://localhost:8000/docs"],
        ["Garanties", "Versions épinglées, modèle spaCy et modèle entraîné inclus dans le dépôt, aucune clé API, chemins relatifs ; testé sur un clone neuf (36 tests verts)."],
    ], [20 * mm, W - 20 * mm], header=False)
    st.append(KeepTogether([inst]))

    doc.build(st, onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUT)


if __name__ == "__main__":
    build()
