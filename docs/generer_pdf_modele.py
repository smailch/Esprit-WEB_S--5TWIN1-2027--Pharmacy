"""Génère docs/Modele_IA_PharmaNLU-A.pdf (1 page A4) — le modèle IA expliqué côté fonctionnalités.

Usage : python docs/generer_pdf_modele.py   (nécessite reportlab ; polices Segoe UI de Windows)
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent / "Modele_IA_PharmaNLU-A.pdf"
FONTS = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("UI", FONTS / "segoeui.ttf"))
pdfmetrics.registerFont(TTFont("UI-B", FONTS / "segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("UI-SB", FONTS / "seguisb.ttf"))
pdfmetrics.registerFont(TTFont("UI-L", FONTS / "segoeuil.ttf"))
pdfmetrics.registerFontFamily("UI", normal="UI", bold="UI-B", italic="UI", boldItalic="UI-B")

FOREST = colors.HexColor("#1E3227")
GREEN = colors.HexColor("#3F5447")
GOLD = colors.HexColor("#9B8A3E")
SAGE = colors.HexColor("#CBCFB8")
SAGE_L = colors.HexColor("#E6E8DC")
IVORY = colors.HexColor("#F2F0EC")
LINE = colors.HexColor("#B9BEA3")

S = {
    "body": ParagraphStyle("body", fontName="UI", fontSize=8.4, leading=11.2, textColor=FOREST),
    "small": ParagraphStyle("small", fontName="UI", fontSize=7.6, leading=9.8, textColor=GREEN),
    "cell": ParagraphStyle("cell", fontName="UI", fontSize=7.7, leading=9.8, textColor=FOREST),
    "cellb": ParagraphStyle("cellb", fontName="UI-SB", fontSize=7.7, leading=9.8, textColor=FOREST),
    "h2": ParagraphStyle("h2", fontName="UI-SB", fontSize=10, leading=12.5, textColor=FOREST, spaceBefore=6, spaceAfter=3),
    "step": ParagraphStyle("step", fontName="UI-SB", fontSize=8, leading=10, textColor=IVORY, alignment=1),
    "stepd": ParagraphStyle("stepd", fontName="UI", fontSize=7, leading=8.8, textColor=FOREST, alignment=1),
    "kpi": ParagraphStyle("kpi", fontName="UI-L", fontSize=15, leading=17, textColor=FOREST),
    "kpil": ParagraphStyle("kpil", fontName="UI", fontSize=7, leading=8.6, textColor=GREEN),
}


def p(text, style="body"):
    return Paragraph(text, S[style])


def h2(num, text):
    return Paragraph(f'<font color="#9B8A3E">{num}</font>&nbsp;&nbsp;{text}', S["h2"])


def table(rows, widths, header=True):
    data = [[p(c, "cellb" if (header and i == 0) or j == 0 else "cell") for j, c in enumerate(r)] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), SAGE), ("LINEBELOW", (0, 0), (-1, 0), 0.8, GREEN)]
    for i in range(1 if header else 0, len(rows)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), SAGE_L))
    t.setStyle(TableStyle(style))
    return t


def pipeline(width):
    """Schéma horizontal : 6 étapes de la question à la réponse."""
    steps = [
        ("Question", "texte libre en français, fautes acceptées"),
        ("1. Normaliser", "spaCy : tokens, lemmes, sans accents"),
        ("2. Reconnaître", "EntityRuler + RapidFuzz : médicaments, molécules, maladies"),
        ("3. Comprendre", "scikit-learn : laquelle des 12 intentions ?"),
        ("4. Traduire", "gabarit SPARQL rempli avec les URI"),
        ("Réponse", "phrase + tableau + requête affichée"),
    ]
    n = len(steps)
    gap = 3 * mm
    cw = (width - gap * (n - 1)) / n
    top, bottom, widths = [], [], []
    for i, (t, d) in enumerate(steps):
        top.append(p(t, "step"))
        bottom.append(p(d, "stepd"))
        widths.append(cw)
        if i < n - 1:
            top.append(p("→", "step"))
            bottom.append("")
            widths.append(gap)
    tbl = Table([top, bottom], colWidths=widths)
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for i in range(0, len(widths), 2):
        bg = GOLD if i in (0, len(widths) - 1) else FOREST
        style += [("BACKGROUND", (i, 0), (i, 0), bg), ("BACKGROUND", (i, 1), (i, 1), IVORY), ("BOX", (i, 0), (i, 1), 0.6, bg)]
    for i in range(1, len(widths), 2):
        style.append(("TEXTCOLOR", (i, 0), (i, 0), GOLD))
    tbl.setStyle(TableStyle(style))
    # La flèche entre deux cases doit être dorée et non blanche : on la réécrit avec une couleur explicite.
    for i in range(1, len(widths), 2):
        tbl._cellvalues[0][i] = Paragraph('<font color="#9B8A3E"><b>→</b></font>', S["stepd"])
    return tbl


def kpis(items, width):
    t = Table([[p(v, "kpi") for v, _ in items], [p(l, "kpil") for _, l in items]], colWidths=[width / len(items)] * len(items))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), IVORY), ("BOX", (0, 0), (-1, -1), 0.6, LINE), ("LINEBEFORE", (1, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 1), (-1, 1), 5),
    ]))
    return t


def header_footer(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(FOREST)
    canvas.rect(0, h - 27 * mm, w, 27 * mm, stroke=0, fill=1)
    canvas.setFillColor(GOLD)
    canvas.setFont("UI-SB", 7.3)
    canvas.drawString(15 * mm, h - 9.5 * mm, "WEB SÉMANTIQUE  ·  ESPRIT 5 TWIN 2026–2027  ·  MODULE A — MOLÉCULE + MÉDICAMENT  ·  CRITÈRE « API IA »")
    canvas.setFillColor(IVORY)
    canvas.setFont("UI-L", 19)
    canvas.drawString(15 * mm, h - 18.5 * mm, "PharmaNLU-A — poser une question, obtenir la requête SPARQL")
    canvas.setFont("UI", 8.5)
    canvas.drawString(15 * mm, h - 24 * mm, "Modèle de traitement du langage naturel développé par l’équipe NeoCoders (Chemlali Ismail) · 100 % local · aucune API de LLM")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(15 * mm, 11 * mm, w - 15 * mm, 11 * mm)
    canvas.setFillColor(GREEN)
    canvas.setFont("UI", 6.8)
    canvas.drawString(15 * mm, 7.5 * mm, "Code : backend/nlp/  ·  dépôt github.com/smailch/Esprit-WEB_S--5TWIN1-2027--Pharmacy (branche Molecule-Medicament)  ·  données fictives, aucun conseil médical")
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=31 * mm, bottomMargin=14 * mm,
                            title="PharmaNLU-A — modèle IA du module A", author="Chemlali Ismail (NeoCoders)")
    W = A4[0] - 30 * mm
    st = []

    st.append(p("<b>À quoi sert le modèle ?</b> L’utilisateur tape une question en français dans la page <b>Assistant IA</b>, sans connaître SPARQL. "
                "Le modèle comprend ce qu’il demande, reconnaît les médicaments, molécules et maladies cités, <b>écrit la requête SPARQL</b>, "
                "l’exécute sur l’ontologie et répond par une phrase, un tableau de résultats et la requête générée. "
                "Il remplace la console SPARQL pour un utilisateur non spécialiste."))
    st.append(Spacer(1, 5))
    st.append(pipeline(W))

    st.append(h2("1", "Ce que l’on peut demander : 12 types de questions (intentions)"))
    st.append(table([
        ["Intention", "Exemple de question", "Ce que fait la requête générée"],
        ["Lister une classe", "« Liste des antibiotiques »", "molécules de la classe, sous-classes incluses (inférence)"],
        ["Filtrer les médicaments", "« Sans ordonnance à moins de 5 dinars »", "filtres prix / ordonnance / type / forme ; « le plus cher »"],
        ["Médicaments contenant", "« Quels médicaments contiennent de l’ibuprofène ? »", "propriété inverse estContenuDans"],
        ["Composition", "« Que contient le Doliprane ? »", "molécules du médicament"],
        ["Effets secondaires", "« Effets graves de l’Advil »", "chemin médicament → molécule → effet, filtre gravité"],
        ["Contre-indications", "« Contre-indications de l’aspirine »", "chemin molécule → contre-indication → pathologie"],
        ["À éviter si maladie", "« Quels médicaments éviter en cas d’ulcère ? »", "propriété estContreIndiquePour déduite par la chaîne OWL"],
        ["Générique moins cher", "« Un générique moins cher que le Clamoxyl ? »", "même composition + économie calculée (BIND)"],
        ["Interactions", "« Advil et Aspégic interagissent-ils ? »", "propriété symétrique interagitAvec"],
        ["Attribut", "« Code ATC du paracétamol » · « Prix du Zithromax »", "lecture d’une donnée ; « sur ordonnance ? » → requête ASK"],
        ["Indication", "« Que prendre contre la migraine ? »", "médicaments indiqués, sauf ceux contre-indiqués"],
        ["Statistiques", "« Combien de médicaments génériques ? »", "COUNT, AVG, MIN, MAX"],
    ], [31 * mm, 62 * mm, W - 93 * mm]))

    st.append(h2("2", "Exemple pas à pas : « Quels médicaments contiennent de l’ibuprophène ? » (faute volontaire)"))
    st.append(table([
        ["Normalisation", "quels medicaments contiennent de l’ ibuprophene  — lemmes : contiennent → contenir"],
        ["Entités", "« ibuprophene » n’existe pas dans l’ontologie → RapidFuzz trouve <b>Ibuprofène</b> (similarité 86 %, badge « corrigé »)"],
        ["Délexicalisation", "quel medicament contenir de le <b>xmol</b> — le nom est remplacé par son type : le modèle apprend la forme de la question"],
        ["Intention", "<b>medicaments_contenant</b>, confiance 97 % (2e hypothèse affichée si elle dépasse 8 %)"],
        ["Requête", "SELECT ?medicament ?label ?prix WHERE { :Ibuprofene :estContenuDans ?medicament . … } ORDER BY ?prix"],
        ["Réponse", "« Ibuprofène se trouve dans : Ibuprofène Mylan 400 mg et Advil 400 mg. » + tableau exportable en CSV"],
    ], [27 * mm, W - 27 * mm], header=False))

    st.append(h2("3", "Fonctionnalités qui le rendent fiable"))
    st.append(table([
        ["Tolère les fautes", "« dolipran », « amoxiciline », « zitromax », « advill » sont corrigés automatiquement (RapidFuzz)."],
        ["Synonymes métier", "« antidouleur » → Antalgique, « mal de tête » → Migraine, « problème de reins » → Insuffisance rénale…"],
        ["Apprend les nouvelles données", "Le dictionnaire est relu dans l’ontologie : un médicament créé via le CRUD est reconnu tout de suite, sans ré-entraînement."],
        ["Ne devine jamais", "Confiance < 40 % → « je n’ai pas compris » + exemples ; entité manquante → « Précisez le médicament… »."],
        ["Requête toujours valide", "La requête vient d’un gabarit écrit à la main, pas d’un texte généré : pas d’erreur de syntaxe possible."],
        ["Explicable", "Intention, confiance, entités, filtres, étapes et requête commentée sont affichés ; historique et suggestions cliquables."],
    ], [37 * mm, W - 37 * mm], header=False))

    st.append(h2("4", "Comment il a été construit et évalué"))
    st.append(kpis([("96,9 %", "questions de test bien comprises (93 / 96)"), ("100 %", "entités reconnues sur le test"),
                    ("314 / 96", "questions d’entraînement / de test"), ("253 Ko", "taille du modèle, commité dans Git")], W))
    st.append(Spacer(1, 3))
    st.append(p("<b>Bibliothèques :</b> spaCy 3.8 + fr_core_news_sm (tokenisation, lemmes, EntityRuler) · scikit-learn 1.9 (TF-IDF mots 1–2-grammes et "
                "caractères 3–5-grammes → régression logistique) · RapidFuzz 3.14 (distance de Levenshtein) · rdflib 7.6 (exécution SPARQL). "
                "<b>Données :</b> questions d’entraînement issues de gabarits écrits à la main ; jeu de test écrit séparément, avec d’autres formulations et des fautes. "
                "<b>Reproductible :</b> graine 42, <font face='UI-SB'>python -m nlp.train</font> ré-entraîne et réécrit la carte du modèle, 16 tests automatiques.", "small"))

    doc.build(st, onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUT)


if __name__ == "__main__":
    build()
