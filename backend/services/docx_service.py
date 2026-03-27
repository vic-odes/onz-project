from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime
import io


BLEU_MARINE = RGBColor(0x1B, 0x3A, 0x5C)
VERT_SAUGE = RGBColor(0x4A, 0x7C, 0x59)
GRIS_CLAIR = RGBColor(0xF0, 0xF0, 0xF0)


def _set_cell_bg(cell, hex_color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _add_header_footer(doc: Document, project_name: str):
    section = doc.sections[0]

    # En-tête
    header = section.header
    header.is_linked_to_previous = False
    p = header.paragraphs[0]
    p.text = f"ONZ Projet — {project_name}"
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.runs[0]
    run.font.size = Pt(9)
    run.font.color.rgb = BLEU_MARINE
    run.font.name = "Calibri"

    # Pied de page avec numérotation
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.font.size = Pt(9)
    run.font.name = "Calibri"
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)


def _add_title(doc: Document, text: str, level: int = 1):
    p = doc.add_paragraph()
    p.style = f"Heading {level}"
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(14 if level == 1 else 12)
    run.font.color.rgb = BLEU_MARINE if level == 1 else VERT_SAUGE
    run.bold = True
    return p


def _add_paragraph(doc: Document, text: str):
    p = doc.add_paragraph(text)
    for run in p.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(11)
    return p


def _add_table_with_headers(doc: Document, headers: list[str], rows: list[list[str]]):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # En-tête du tableau
    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr_cells[i].text = header
        _set_cell_bg(hdr_cells[i], "1B3A5C")
        run = hdr_cells[i].paragraphs[0].runs[0]
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(10)

    # Lignes de données
    for row_data in rows:
        row_cells = table.add_row().cells
        for i, cell_text in enumerate(row_data):
            row_cells[i].text = str(cell_text)
            run = row_cells[i].paragraphs[0].runs[0] if row_cells[i].paragraphs[0].runs else row_cells[i].paragraphs[0].add_run(str(cell_text))
            run.font.name = "Calibri"
            run.font.size = Pt(10)

    doc.add_paragraph()
    return table


def create_word_document(project_data: dict, generated: dict) -> bytes:
    doc = Document()

    # Marges
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2.5)

    project_name = project_data.get("nom", "Projet")
    _add_header_footer(doc, project_name)

    # ------------------------------------------------------------------ #
    # PAGE DE GARDE
    # ------------------------------------------------------------------ #
    doc.add_paragraph()
    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("ONZ PROJET")
    run.font.name = "Calibri"
    run.font.size = Pt(14)
    run.font.color.rgb = VERT_SAUGE
    run.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(project_name.upper())
    run.font.name = "Calibri"
    run.font.size = Pt(22)
    run.font.color.rgb = BLEU_MARINE
    run.bold = True

    doc.add_paragraph()

    infos = [
        ("Pays / Zone d'intervention", project_data.get("pays", "")),
        ("Secteur", project_data.get("secteur", "")),
        ("Bailleur cible", project_data.get("bailleur", "")),
        ("Durée", f"{project_data.get('duree_mois', 'N/A')} mois"),
        ("Budget estimé", f"${project_data.get('budget_total', 'N/A'):,} USD" if project_data.get("budget_total") else "N/A"),
        ("Date de génération", datetime.now().strftime("%d/%m/%Y")),
    ]
    for label, value in infos:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{label} : ")
        run.font.name = "Calibri"
        run.font.size = Pt(12)
        run.font.color.rgb = BLEU_MARINE
        run.bold = True
        run2 = p.add_run(str(value))
        run2.font.name = "Calibri"
        run2.font.size = Pt(12)

    doc.add_page_break()

    # ------------------------------------------------------------------ #
    # I. INTRODUCTION
    # ------------------------------------------------------------------ #
    _add_title(doc, "I. Introduction", 1)
    _add_paragraph(doc, generated.get("introduction", ""))
    doc.add_paragraph()

    # ------------------------------------------------------------------ #
    # II. CADRE LOGIQUE
    # ------------------------------------------------------------------ #
    _add_title(doc, "II. Cadre Logique", 1)
    cadre = generated.get("cadre_logique", {})

    _add_title(doc, "Objectif Global", 2)
    _add_paragraph(doc, cadre.get("objectif_global", ""))

    _add_title(doc, "Objectifs Spécifiques", 2)
    for obj in cadre.get("objectifs_specifiques", []):
        p = doc.add_paragraph(obj, style="List Bullet")
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(11)

    _add_title(doc, "Résultats Attendus", 2)
    for res in cadre.get("resultats", []):
        p = doc.add_paragraph(res, style="List Bullet")
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(11)

    _add_title(doc, "Activités Principales", 2)
    for act in cadre.get("activites", []):
        p = doc.add_paragraph(act, style="List Bullet")
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(11)

    _add_title(doc, "Indicateurs SMART", 2)
    indicators = cadre.get("indicateurs_smart", [])
    if indicators:
        _add_table_with_headers(
            doc,
            ["Indicateur"],
            [[ind] for ind in indicators],
        )

    _add_title(doc, "Sources de Vérification", 2)
    for sv in cadre.get("sources_verification", []):
        p = doc.add_paragraph(sv, style="List Bullet")
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(11)

    _add_title(doc, "Hypothèses et Conditions Préalables", 2)
    for hyp in cadre.get("hypotheses", []):
        p = doc.add_paragraph(hyp, style="List Bullet")
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(11)

    doc.add_page_break()

    # ------------------------------------------------------------------ #
    # III. PARTIES PRENANTES
    # ------------------------------------------------------------------ #
    _add_title(doc, "III. Analyse des Parties Prenantes", 1)
    parties = generated.get("parties_prenantes", [])
    if parties:
        rows = [
            [
                p.get("nom", ""),
                p.get("role", ""),
                p.get("interet", ""),
                p.get("influence", ""),
            ]
            for p in parties
        ]
        _add_table_with_headers(doc, ["Acteur", "Rôle", "Intérêt", "Influence"], rows)

    # ------------------------------------------------------------------ #
    # IV. PLANIFICATION DES ACTIVITÉS
    # ------------------------------------------------------------------ #
    _add_title(doc, "IV. Planification des Activités", 1)
    activites = generated.get("activites_detaillees", [])
    if activites:
        rows = [
            [
                a.get("titre", ""),
                a.get("description", ""),
                a.get("responsable", ""),
                a.get("duree", ""),
                a.get("objectif_lie", ""),
            ]
            for a in activites
        ]
        _add_table_with_headers(
            doc,
            ["Activité", "Description", "Responsable", "Durée", "Objectif lié"],
            rows,
        )

    _add_title(doc, "Chronogramme Trimestriel", 2)
    chrono = generated.get("chronogramme", [])
    if chrono:
        rows = [
            [c.get("trimestre", ""), " / ".join(c.get("activites", []))]
            for c in chrono
        ]
        _add_table_with_headers(doc, ["Trimestre", "Activités"], rows)

    doc.add_page_break()

    # ------------------------------------------------------------------ #
    # V. BUDGET
    # ------------------------------------------------------------------ #
    _add_title(doc, "V. Budget Prévisionnel", 1)
    budget = generated.get("budget", {})
    lignes = budget.get("lignes", [])
    if lignes:
        rows = [
            [
                l.get("categorie", ""),
                l.get("description", ""),
                f"${l.get('montant_usd', 0):,.0f}",
                f"{l.get('pourcentage', 0):.1f}%",
            ]
            for l in lignes
        ]
        _add_table_with_headers(
            doc,
            ["Catégorie", "Description", "Montant (USD)", "% du total"],
            rows,
        )

    p = doc.add_paragraph()
    run = p.add_run(
        f"Total budget : ${budget.get('total_usd', 0):,.0f} USD  |  "
        f"Coûts directs : ${budget.get('couts_directs', 0):,.0f}  |  "
        f"Coûts indirects : ${budget.get('couts_indirects', 0):,.0f}"
    )
    run.font.name = "Calibri"
    run.font.size = Pt(11)
    run.bold = True
    run.font.color.rgb = BLEU_MARINE

    doc.add_paragraph()

    # ------------------------------------------------------------------ #
    # VI. ANALYSE COÛT-BÉNÉFICE
    # ------------------------------------------------------------------ #
    _add_title(doc, "VI. Analyse Coût-Bénéfice", 1)
    acb = generated.get("analyse_cout_benefice", {})
    _add_table_with_headers(
        doc,
        ["Indicateur", "Valeur"],
        [
            ["Valeur Actuelle Nette (VAN)", f"${acb.get('van', 0):,.0f} USD"],
            ["Ratio Coût-Bénéfice", f"{acb.get('ratio_cout_benefice', 0):.2f}"],
            ["Scénario central", acb.get("scenario_central", "")],
            ["Scénario pessimiste", acb.get("scenario_pessimiste", "")],
        ],
    )
    _add_title(doc, "Justification économique", 2)
    _add_paragraph(doc, acb.get("justification", ""))

    doc.add_page_break()

    # ------------------------------------------------------------------ #
    # VII. GESTION DES RISQUES
    # ------------------------------------------------------------------ #
    _add_title(doc, "VII. Gestion des Risques", 1)
    risques = generated.get("risques", [])
    if risques:
        rows = [
            [
                r.get("risque", ""),
                r.get("probabilite", ""),
                r.get("impact", ""),
                r.get("mitigation", ""),
            ]
            for r in risques
        ]
        _add_table_with_headers(
            doc,
            ["Risque", "Probabilité", "Impact", "Mesure d'atténuation"],
            rows,
        )

    # ------------------------------------------------------------------ #
    # VIII. STRATÉGIE DE COMMUNICATION
    # ------------------------------------------------------------------ #
    _add_title(doc, "VIII. Stratégie de Communication", 1)
    _add_paragraph(doc, generated.get("communication", ""))

    # ------------------------------------------------------------------ #
    # NOTE CONCEPTUELLE (optionnelle)
    # ------------------------------------------------------------------ #
    note = generated.get("note_conceptuelle", "")
    if note and note.strip():
        doc.add_page_break()
        _add_title(doc, "Note Conceptuelle", 1)
        _add_paragraph(doc, note)

    # ------------------------------------------------------------------ #
    # RÉSUMÉ EXÉCUTIF (optionnel)
    # ------------------------------------------------------------------ #
    resume = generated.get("resume_executif", "")
    if resume and resume.strip():
        doc.add_page_break()
        _add_title(doc, "Résumé Exécutif", 1)
        _add_paragraph(doc, resume)

    # Sérialisation en bytes
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
