"""
report_service.py
Génère un rapport PDF professionnel pour l'étudiant.
Utilise reportlab.

Installation : pip install reportlab
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ─── Couleurs SIMCO ───────────────────────────────────────────────────────────
COLOR_PRIMARY   = colors.HexColor('#1a6b5a')
COLOR_TEAL      = colors.HexColor('#4ecdc4')
COLOR_DARK      = colors.HexColor('#0d1117')
COLOR_LIGHT     = colors.HexColor('#f8fffe')
COLOR_SUCCESS   = colors.HexColor('#2ecc71')
COLOR_WARNING   = colors.HexColor('#f39c12')
COLOR_DANGER    = colors.HexColor('#e74c3c')
COLOR_BLUE      = colors.HexColor('#3498db')
COLOR_GRAY      = colors.HexColor('#8b949e')
COLOR_LIGHTGRAY = colors.HexColor('#f5f5f5')


def generate_report_pdf(
    student_name: str,
    subject: str,
    results: dict,
    notions: dict,
    dk: dict
) -> bytes:
    """
    Génère le rapport PDF complet et retourne les bytes.

    Sections :
    1. En-tête SIMCO
    2. Informations étudiant
    3. Score et performance
    4. Profil Dunning-Kruger
    5. Notions à réviser
    6. Compétences maîtrisées sous-estimées
    7. Recommandations personnalisées
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story  = []

    # ─── Styles personnalisés ─────────────────────────────────────────────────
    style_title = ParagraphStyle(
        'Title', parent=styles['Normal'],
        fontSize=24, fontName='Helvetica-Bold',
        textColor=COLOR_PRIMARY, spaceAfter=4,
        alignment=TA_CENTER
    )
    style_subtitle = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica',
        textColor=COLOR_GRAY, spaceAfter=2,
        alignment=TA_CENTER
    )
    style_section = ParagraphStyle(
        'Section', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold',
        textColor=COLOR_PRIMARY, spaceBefore=16, spaceAfter=8,
        borderPad=4
    )
    style_body = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica',
        textColor=COLOR_DARK, spaceAfter=4, leading=14
    )
    style_small = ParagraphStyle(
        'Small', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=COLOR_GRAY, spaceAfter=2
    )
    style_bold = ParagraphStyle(
        'Bold', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        textColor=COLOR_DARK, spaceAfter=4
    )
    style_center = ParagraphStyle(
        'Center', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica',
        alignment=TA_CENTER, textColor=COLOR_DARK
    )

    # ─── 1. EN-TÊTE ──────────────────────────────────────────────────────────
    story.append(Paragraph("SIMCO", style_title))
    story.append(Paragraph("Système Intelligent Multimodal d'Évaluation Cognitive", style_subtitle))
    story.append(Spacer(1, 0.2*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_TEAL))
    story.append(Spacer(1, 0.3*cm))

    # Date et rapport
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    story.append(Paragraph(f"Rapport d'évaluation — {date_str}", style_small))
    story.append(Spacer(1, 0.5*cm))

    # ─── 2. INFORMATIONS ÉTUDIANT ────────────────────────────────────────────
    story.append(Paragraph("👤 Informations", style_section))

    info_data = [
        ["Étudiant", student_name or "Non renseigné"],
        ["Sujet évalué", subject or "Non renseigné"],
        ["Date", date_str],
        ["Nombre de questions", str(results.get("total_questions", 0))],
    ]
    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), COLOR_PRIMARY),
        ('TEXTCOLOR', (1, 0), (1, -1), COLOR_DARK),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [COLOR_LIGHTGRAY, colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # ─── 3. SCORE ET PERFORMANCE ─────────────────────────────────────────────
    story.append(Paragraph("📊 Score et Performance", style_section))

    score       = results.get("score", 0)
    total       = results.get("total_questions", 0)
    percentage  = results.get("percentage", 0)
    level       = results.get("level", "")
    message     = results.get("message", "")

    # Couleur du score
    if percentage >= 80:
        score_color = COLOR_SUCCESS
    elif percentage >= 60:
        score_color = COLOR_BLUE
    elif percentage >= 40:
        score_color = COLOR_WARNING
    else:
        score_color = COLOR_DANGER

    score_style = ParagraphStyle(
        'Score', fontSize=36, fontName='Helvetica-Bold',
        textColor=score_color, alignment=TA_CENTER, spaceAfter=4
    )
    story.append(Paragraph(f"{percentage:.0f}%", score_style))
    story.append(Paragraph(f"{score} bonne(s) réponse(s) sur {total} questions", style_center))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"<b>Niveau :</b> {level} — {message}", style_body))
    story.append(Spacer(1, 0.4*cm))

    # ─── 4. PROFIL DUNNING-KRUGER ─────────────────────────────────────────────
    if dk:
        story.append(Paragraph("🧠 Profil Dunning-Kruger", style_section))

        profil_ml  = dk.get("profil_ml", "Non déterminé")
        zone_label = dk.get("zone_label", "")
        dk_message = dk.get("message", "")
        dk_reco    = dk.get("recommendation", "")

        # Tableau des métriques DK
        dk_data = [
            ["Métrique", "Valeur", "Interprétation"],
            ["Score réel", f"{dk.get('actual_score', 0)}%", "Performance objective"],
            ["Confiance déclarée", f"{dk.get('declared_confidence', 0)}%", "Ce que l'étudiant pense"],
            ["Confiance observée", f"{dk.get('observed_confidence', 'N/A')}%", "Ce que le visage révèle"],
            ["Indice DK", str(dk.get("dk_index", 0)), "Écart confiance/performance"],
            ["Calibration", f"{dk.get('calibration_score', 0)}%", "Précision d'auto-évaluation"],
            ["Profil ML", profil_ml.upper(), "Profil cognitif détecté"],
        ]
        dk_table = Table(dk_data, colWidths=[5*cm, 4*cm, 8*cm])
        dk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_LIGHTGRAY, colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('PADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ]))
        story.append(dk_table)
        story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph(f"<b>Zone :</b> {zone_label}", style_body))
        story.append(Paragraph(f"<b>Diagnostic :</b> {dk_message}", style_body))
        story.append(Paragraph(f"<b>Recommandation :</b> {dk_reco}", style_body))
        story.append(Spacer(1, 0.4*cm))

    # ─── 5. NOTIONS À RÉVISER ────────────────────────────────────────────────
    notions_to_revise = notions.get("notions_to_revise", [])
    if notions_to_revise:
        story.append(Paragraph("📚 Notions à Réviser", style_section))
        story.append(Paragraph(
            f"Les {len(notions_to_revise)} concept(s) suivants ont été identifiés "
            f"comme nécessitant une révision approfondie :", style_body
        ))
        story.append(Spacer(1, 0.2*cm))

        revise_data = [["#", "Notion", "Confiance déclarée", "Confiance observée"]]
        for i, n in enumerate(notions_to_revise, 1):
            revise_data.append([
                str(i),
                n.get("notion", ""),
                f"{n.get('declared_confidence', 0)}%",
                f"{n.get('confidence_observed', 0)}%",
            ])

        revise_table = Table(revise_data, colWidths=[1*cm, 9*cm, 4*cm, 3*cm])
        revise_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_DANGER),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fff5f5'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('PADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (3, -1), 'CENTER'),
        ]))
        story.append(revise_table)
        story.append(Spacer(1, 0.4*cm))

    # ─── 6. COMPÉTENCES MAÎTRISÉES MAIS SOUS-ESTIMÉES ────────────────────────
    mastered_notions = notions.get("mastered_notions", [])
    if mastered_notions:
        story.append(Paragraph("💪 Compétences Maîtrisées mais Sous-Estimées", style_section))
        story.append(Paragraph(
            f"Vous maîtrisez les {len(mastered_notions)} compétence(s) suivantes "
            f"mais vous n'en êtes pas conscient. Faites confiance à vos acquis !", style_body
        ))
        story.append(Spacer(1, 0.2*cm))

        mastered_data = [["#", "Notion maîtrisée", "Confiance déclarée", "Réalité"]]
        for i, n in enumerate(mastered_notions, 1):
            mastered_data.append([
                str(i),
                n.get("notion", ""),
                f"{n.get('declared_confidence', 0)}%",
                "✓ Réussi"
            ])

        mastered_table = Table(mastered_data, colWidths=[1*cm, 9*cm, 4*cm, 3*cm])
        mastered_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_SUCCESS),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f0fff4'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('PADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (3, -1), 'CENTER'),
        ]))
        story.append(mastered_table)
        story.append(Spacer(1, 0.4*cm))

    # ─── 7. RECOMMANDATIONS ──────────────────────────────────────────────────
    recommendations = results.get("recommendations", [])
    if recommendations:
        story.append(Paragraph("💡 Recommandations Personnalisées", style_section))
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", style_body))
        story.append(Spacer(1, 0.4*cm))

    # ─── PIED DE PAGE ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_TEAL))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "© 2026 Projet SIMCO — Système Intelligent Multimodal d'Évaluation Cognitive",
        style_small
    ))

    # ─── Construire le PDF ────────────────────────────────────────────────────
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes