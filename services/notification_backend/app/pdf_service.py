from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from .schemas import NotificationRequest


def _safe(value, default="N/A"):
    return default if value is None else str(value)


def _clamp_percent(value):
    if value is None:
        return 0.0
    try:
        return max(0.0, min(100.0, float(value)))
    except Exception:
        return 0.0


def _draw_score_bar(c, x, y, w, h, score_percent):
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.rect(x, y, w, h, fill=1, stroke=1)
    fill_w = w * (_clamp_percent(score_percent) / 100.0)
    c.setFillColor(colors.HexColor("#22C55E") if score_percent >= 60 else colors.HexColor("#F59E0B") if score_percent >= 40 else colors.HexColor("#EF4444"))
    c.rect(x, y, fill_w, h, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 4, y + h + 4, f"Score: {round(score_percent, 1)}%")


def _draw_confidence_comparison(c, x, y, w, row_h, declared_conf, estimated_conf, actual_score):
    rows = [
        ("Confiance declaree", _clamp_percent(declared_conf), colors.HexColor("#3B82F6")),
        ("Confiance estimee", _clamp_percent(estimated_conf), colors.HexColor("#8B5CF6")),
        ("Score reel", _clamp_percent(actual_score), colors.HexColor("#22C55E")),
    ]

    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y + row_h + 18, "Comparaison des niveaux (%)")

    for idx, (label, value, color) in enumerate(rows):
        ry = y - idx * (row_h + 8)
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.rect(x, ry, w, row_h, fill=1, stroke=0)
        c.setFillColor(color)
        c.rect(x, ry, w * (value / 100.0), row_h, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawString(x + 4, ry + 3, f"{label}: {round(value, 1)}%")


def _draw_confidence_histogram(c, x, y, w, h, question_results):
    values = []
    for q in question_results or []:
        if q.face_confidence is not None:
            values.append(_clamp_percent(q.face_confidence))

    bins = [
        ("0-20", 0, 20, 0),
        ("21-40", 21, 40, 0),
        ("41-60", 41, 60, 0),
        ("61-80", 61, 80, 0),
        ("81-100", 81, 100, 0),
    ]

    mutable_bins = [list(b) for b in bins]
    for v in values:
        for b in mutable_bins:
            if b[1] <= v <= b[2]:
                b[3] += 1
                break

    max_count = max([b[3] for b in mutable_bins], default=1)
    if max_count == 0:
        max_count = 1

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(x, y + h + 12, "Histogramme de confiance (visage)")

    bar_w = w / 5.5
    gap = bar_w * 0.1
    for idx, b in enumerate(mutable_bins):
        label, _, _, count = b
        bx = x + idx * (bar_w + gap)
        bh = (count / max_count) * h

        c.setFillColor(colors.HexColor("#E2E8F0"))
        c.rect(bx, y, bar_w, h, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#6366F1"))
        c.rect(bx, y, bar_w, bh, fill=1, stroke=0)

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawCentredString(bx + bar_w / 2, y - 10, label)
        c.drawCentredString(bx + bar_w / 2, y + bh + 3, str(count))


def build_result_pdf(payload: NotificationRequest) -> bytes:
    quiz = payload.quiz_result

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "SIMCO - Rapport de Resultat")
    y -= 22
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Etudiant: {payload.user_name}")
    y -= 16
    c.drawString(40, y, f"Email: {payload.user_email}")

    # Summary box
    y -= 24
    c.setStrokeColor(colors.HexColor("#D1D5DB"))
    c.setFillColor(colors.HexColor("#F9FAFB"))
    c.rect(35, y - 95, width - 70, 95, fill=1, stroke=1)
    c.setFillColor(colors.black)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(45, y - 18, "Statistiques principales")
    c.setFont("Helvetica", 10)
    c.drawString(45, y - 36, f"Score: {quiz.score}/{quiz.total_questions}")
    c.drawString(250, y - 36, f"Pourcentage: {quiz.percentage}%")
    c.drawString(45, y - 52, f"Niveau: {_safe(quiz.level)}")
    c.drawString(250, y - 52, f"Profil: {_safe(quiz.profile_label)}")
    c.drawString(45, y - 68, f"Confiance declaree: {_safe(quiz.self_confidence)}")
    c.drawString(250, y - 68, f"Confiance estimee: {_safe(quiz.true_confidence)}")

    y -= 118

    # Graph 1: score bar
    _draw_score_bar(c, 45, y - 12, width - 90, 14, quiz.percentage)
    y -= 36

    # Graph 2: confidence comparison bars
    declared_for_chart = payload.dunning_kruger.declared_confidence if payload.dunning_kruger else quiz.self_confidence
    _draw_confidence_comparison(c, 45, y - 2, width - 90, 12, declared_for_chart, quiz.true_confidence, quiz.percentage)
    y -= 64

    # Graph 3: face-confidence histogram (if any values exist)
    _draw_confidence_histogram(c, 45, y - 40, width - 90, 34, payload.question_results)
    y -= 56

    # Dunning-Kruger section
    if payload.dunning_kruger:
        dk = payload.dunning_kruger
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Calibration (Dunning-Kruger)")
        y -= 16
        c.setFont("Helvetica", 10)
        c.drawString(45, y, f"Score reel: {_safe(dk.actual_score)}")
        c.drawString(250, y, f"Confiance declaree: {_safe(dk.declared_confidence)}")
        y -= 14
        c.drawString(45, y, f"Score de calibration: {_safe(dk.calibration_score)}")
        y -= 22

    # Message
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Feedback")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(45, y, _safe(quiz.message, "Aucun message"))
    y -= 24

    # Recommendations
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Plan d'action")
    y -= 16
    c.setFont("Helvetica", 10)
    recommendations = quiz.recommendations[:6] if quiz.recommendations else ["Continuez la pratique reguliere."]
    for idx, rec in enumerate(recommendations, start=1):
        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)
        c.drawString(45, y, f"{idx}. {rec}")
        y -= 14

    # Per-question insights
    if payload.question_results:
        y -= 8
        if y < 110:
            c.showPage()
            y = height - 50

        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Analyse par question")
        y -= 16

        c.setFont("Helvetica", 9)
        for idx, q in enumerate(payload.question_results[:10], start=1):
            if y < 70:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 9)

            status = "Correct" if q.is_correct else ("Incorrect" if q.is_correct is False else "N/A")
            face_conf = _safe(q.face_confidence)
            line = f"Q{idx} [{status}] - Face confidence: {face_conf} - {_safe(q.confidence_analysis, 'N/A')}"
            c.drawString(45, y, line[:130])
            y -= 12

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, 30, "Genere par SIMCO Notification Service")

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
