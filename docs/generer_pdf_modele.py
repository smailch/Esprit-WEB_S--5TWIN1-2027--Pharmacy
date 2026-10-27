"""Génère docs/Modele_IA_PharmaNLU-A.pdf (1 page A4) : pages du module A + outils du modèle PharmaNLU-A.

Usage : python docs/generer_pdf_modele.py   (nécessite reportlab ; polices Segoe UI de Windows)
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

OUT = Path(__file__).resolve().parent / "Modele_IA_PharmaNLU-A.pdf"
FONTS = Path("C:/Windows/Fonts")
for name, file in (("UI", "segoeui.ttf"), ("UI-B", "segoeuib.ttf"), ("UI-SB", "seguisb.ttf"), ("UI-L", "segoeuil.ttf")):
    pdfmetrics.registerFont(TTFont(name, FONTS / file))
pdfmetrics.registerFontFamily("UI", normal="UI", bold="UI-B", italic="UI", boldItalic="UI-B")

FOREST = colors.HexColor("#1E3227")
GREEN = colors.HexColor("#3F5447")
GOLD = colors.HexColor("#9B8A3E")
SAGE = colors.HexColor("#CBCFB8")
SAGE_L = colors.HexColor("#E3E6D6")
IVORY = colors.HexColor("#F2F0EC")
LINE = colors.HexColor("#B9BEA3")

W, H = A4
M = 16 * mm

TXT = ParagraphStyle("t", fontName="UI", fontSize=9.2, leading=12.6, textColor=FOREST)
TXT_S = ParagraphStyle("ts", fontName="UI", fontSize=8.6, leading=11.4, textColor=GREEN)
TOOL = ParagraphStyle("tool", fontName="UI-SB", fontSize=9.6, leading=12.4, textColor=FOREST)

PAGES = [
    ("Molécules", "Liste filtrable (classe via la hiérarchie, code ATC, recherche sans accents), arbre à 3 niveaux, fiche détaillée, CRUD."),
    ("Médicaments", "Cartes filtrables (type, ordonnance, forme, prix), statistiques, fiche détaillée, graphe CONSTRUCT, CRUD."),
    ("Comparateur", "Princeps ↔ génériques de même composition, économie calculée en DT et en %."),
    ("Interactions", "Interactions (propriété symétrique) et doublons de principe actif entre plusieurs médicaments."),
    ("Assistant IA", "Question en français → requête SPARQL → réponse, grâce au modèle PharmaNLU-A."),
    ("Console SPARQL", "Les 16 requêtes du catalogue en un clic, plus un éditeur libre (lecture seule)."),
]

STEPS = [
    ("Normalisation, tokenisation, lemmatisation", "spaCy 3.8 + fr_core_news_sm"),
    ("Reconnaissance des entités (dictionnaire généré depuis l’ontologie)", "spaCy EntityRuler"),
    ("Correction des fautes de frappe", "RapidFuzz (distance de Levenshtein)"),
    ("Classification de l’intention (12 intentions)", "scikit-learn : TF-IDF mots + caractères → régression logistique"),
    ("Génération et exécution de la requête", "gabarits SPARQL + rdflib"),
]


def para(c, text, style, x, y_top, width):
    """Dessine un paragraphe dont le haut est à y_top ; renvoie sa hauteur."""
    p = Paragraph(text, style)
    _, h = p.wrap(width, 1000)
    p.drawOn(c, x, y_top - h)
    return h


def section_title(c, y, num, title, subtitle):
    c.setFillColor(GOLD)
    c.setFont("UI-SB", 9)
    c.drawString(M, y, num)
    c.setFillColor(FOREST)
    c.setFont("UI-SB", 15)
    c.drawString(M + 8 * mm, y - 1, title)
    c.setFillColor(GREEN)
    c.setFont("UI", 8.6)
    c.drawString(M + 8 * mm, y - 6.2 * mm, subtitle)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(M, y - 9.5 * mm, W - M, y - 9.5 * mm)
    return y - 14 * mm


def draw():
    c = rl_canvas.Canvas(str(OUT), pagesize=A4)
    c.setTitle("Module A — Molécule + Médicament : pages et modèle PharmaNLU-A")
    c.setAuthor("Chemlali Ismail (NeoCoders)")

    # Fond et bandeau
    c.setFillColor(IVORY)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(FOREST)
    c.rect(0, H - 44 * mm, W, 44 * mm, stroke=0, fill=1)
    c.setFillColor(GOLD)
    c.setFont("UI-SB", 8)
    c.drawString(M, H - 13 * mm, "WEB SÉMANTIQUE  ·  ESPRIT 5 TWIN  ·  2026–2027  ·  PHARMASÉMANTIQUE")
    c.setFillColor(IVORY)
    c.setFont("UI-L", 27)
    c.drawString(M, H - 26 * mm, "Module A — Molécule + Médicament")
    c.setFont("UI", 10.5)
    c.drawString(M, H - 34 * mm, "Chemlali Ismail  ·  équipe NeoCoders")
    # Emblème : cercle + croix
    cx, cy, r = W - M - 11 * mm, H - 22 * mm, 11 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.1)
    c.circle(cx, cy, r, stroke=1, fill=0)
    c.circle(cx, cy, r - 3 * mm, stroke=1, fill=0)
    a, b = 2.2 * mm, 5.4 * mm
    path = c.beginPath()
    for px, py in [(-a, b), (a, b), (a, a), (b, a), (b, -a), (a, -a), (a, -b), (-a, -b), (-a, -a), (-b, -a), (-b, a), (-a, a)]:
        (path.lineTo if path.getCode() else path.moveTo)(cx + px, cy + py)
    path.close()
    c.drawPath(path, stroke=1, fill=0)

    # ----------------------------------------------------------- Section 1 : pages
    y = section_title(c, H - 56 * mm, "01", "Les pages de l’application", "Six écrans, chacun alimenté par des requêtes SPARQL sur l’ontologie")
    cols, gap = 3, 5 * mm
    cw = (W - 2 * M - gap * (cols - 1)) / cols
    ch = 31 * mm
    for i, (title, desc) in enumerate(PAGES):
        col, row = i % cols, i // cols
        x = M + col * (cw + gap)
        top = y - row * (ch + gap)
        highlight = title == "Assistant IA"
        c.setFillColor(FOREST if highlight else colors.white)
        c.setStrokeColor(FOREST if highlight else LINE)
        c.setLineWidth(0.7)
        c.roundRect(x, top - ch, cw, ch, 3.5 * mm, stroke=1, fill=1)
        c.setFillColor(GOLD)
        c.setFont("UI-SB", 8)
        c.drawString(x + 5 * mm, top - 7 * mm, f"{i + 1:02d}")
        c.setFillColor(IVORY if highlight else FOREST)
        c.setFont("UI-SB", 12)
        c.drawString(x + 12 * mm, top - 7.4 * mm, title)
        style = ParagraphStyle("d", parent=TXT_S, textColor=SAGE if highlight else GREEN)
        para(c, desc, style, x + 5 * mm, top - 11.5 * mm, cw - 10 * mm)
    y = y - 2 * (ch + gap) - 6 * mm

    # ----------------------------------------------------------- Section 2 : pipeline
    y = section_title(c, y, "02", "Assistant IA — modèle PharmaNLU-A", "Question en français → requête SPARQL, en 5 étapes · aucune API de LLM, tout est exécuté en local")
    row_h = 15.5 * mm
    badge = 9 * mm
    tool_x = M + 104 * mm
    for i, (step, tool) in enumerate(STEPS):
        top = y - i * (row_h + 2.4 * mm)
        c.setFillColor(colors.white)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.roundRect(M, top - row_h, W - 2 * M, row_h, 3 * mm, stroke=1, fill=1)
        c.setFillColor(SAGE_L)
        c.roundRect(tool_x - 3 * mm, top - row_h + 1.6 * mm, W - M - tool_x + 1.4 * mm, row_h - 3.2 * mm, 2.4 * mm, stroke=0, fill=1)
        c.setFillColor(FOREST)
        c.circle(M + 4 * mm + badge / 2, top - row_h / 2, badge / 2, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.setFont("UI-B", 10)
        c.drawCentredString(M + 4 * mm + badge / 2, top - row_h / 2 - 3.4, str(i + 1))
        p = Paragraph(step, TXT)
        _, ph = p.wrap(tool_x - M - 22 * mm, 100)
        p.drawOn(c, M + 17 * mm, top - row_h / 2 - ph / 2)
        t = Paragraph(tool, TOOL)
        _, th = t.wrap(W - M - tool_x - 4 * mm, 100)
        t.drawOn(c, tool_x, top - row_h / 2 - th / 2)
        if i < len(STEPS) - 1:
            c.setStrokeColor(GOLD)
            c.setLineWidth(1.2)
            x0 = M + 4 * mm + badge / 2
            c.line(x0, top - row_h - 0.2 * mm, x0, top - row_h - 2.2 * mm)
    c.setFillColor(GREEN)
    c.setFont("UI", 7.6)
    c.drawString(tool_x, y + 2.2 * mm, "OUTIL")
    c.drawString(M + 17 * mm, y + 2.2 * mm, "ÉTAPE")

    # Pied de page
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(M, 12 * mm, W - M, 12 * mm)
    c.setFillColor(GREEN)
    c.setFont("UI", 7.2)
    c.drawString(M, 8 * mm, "github.com/smailch/Esprit-WEB_S--5TWIN1-2027--Pharmacy  ·  branche Molecule-Medicament")
    c.drawRightString(W - M, 8 * mm, "Données fictives — aucun conseil médical")
    c.showPage()
    c.save()
    print(OUT)


if __name__ == "__main__":
    draw()
