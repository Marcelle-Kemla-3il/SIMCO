from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Line, Circle, Rect
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.widgets.markers import makeMarker
import io
import base64
from datetime import datetime
from typing import Dict, List, Any

class PDFReportService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Configure les styles personnalisés pour le PDF"""
        # Style pour les titres
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2d3748'),
            alignment=TA_CENTER,
            borderWidth=0,
            borderColor=colors.transparent
        ))
        
        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=15,
            spaceBefore=20,
            textColor=colors.HexColor('#4a5568'),
            borderWidth=0,
            borderColor=colors.transparent
        ))
        
        # Style pour le contenu
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.HexColor('#2d3748'),
            alignment=TA_LEFT
        ))
        
        # Style pour les métriques
        self.styles.add(ParagraphStyle(
            name='MetricStyle',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=5,
            textColor=colors.HexColor('#2d3748'),
            alignment=TA_CENTER
        ))
        # Style atténué
        self.styles.add(ParagraphStyle(
            name='Muted',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER
        ))
    
    def create_score_circle(self, score_percentage: int) -> Drawing:
        """Crée un indicateur simple: anneau + barres Acquis vs À renforcer"""
        drawing = Drawing(260, 180)
        cx, cy, r = 90, 90, 60

        # Anneau de fond
        bg = Circle(cx, cy, r, fillColor=colors.whitesmoke, strokeColor=colors.grey, strokeWidth=2)
        drawing.add(bg)

        # Anneau intérieur pour effet donut
        inner = Circle(cx, cy, r-18, fillColor=colors.white, strokeColor=colors.transparent)
        drawing.add(inner)

        # Valeurs
        known = max(0, min(100, int(score_percentage)))
        improve = 100 - known

        # Barres à droite (robustes sur ReportLab)
        known_bar = Rect(cx + r + 20, cy + 15, 18, max(2, int(known)), fillColor=colors.HexColor('#4CAF50'), strokeColor=colors.HexColor('#4CAF50'))
        improve_bar = Rect(cx + r + 60, cy + 15, 18, max(2, int(improve)), fillColor=colors.HexColor('#FF7043'), strokeColor=colors.HexColor('#FF7043'))
        drawing.add(known_bar)
        drawing.add(improve_bar)

        from reportlab.graphics.shapes import String
        # Texte central
        drawing.add(String(cx, cy+2, f"{known}%", fontSize=16, textAnchor='middle', fillColor=colors.HexColor('#2d3748')))
        drawing.add(String(cx, cy-16, "Connaissance", fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#4a5568')))

        # Légendes barres
        drawing.add(String(cx + r + 29, cy - 6, "Acquis", fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#4CAF50')))
        drawing.add(String(cx + r + 29, cy + max(18, 20 + known), f"{known}%", fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#2d3748')))
        drawing.add(String(cx + r + 69, cy - 6, "À renforcer", fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#FF7043')))
        drawing.add(String(cx + r + 69, cy + max(18, 20 + improve), f"{improve}%", fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#2d3748')))

        return drawing

    def create_header_banner(self) -> Drawing:
        """Bannière d'entête colorée pour une touche professionnelle"""
        drawing = Drawing(468, 24)
        bar = Rect(0, 0, 468, 24, fillColor=colors.HexColor('#4f46e5'), strokeColor=colors.HexColor('#4f46e5'))
        accent = Rect(0, 0, 8, 24, fillColor=colors.HexColor('#06b6d4'), strokeColor=colors.HexColor('#06b6d4'))
        drawing.add(bar)
        drawing.add(accent)
        return drawing

    def create_section_divider(self) -> Drawing:
        """Fine ligne séparatrice pour structurer le document"""
        drawing = Drawing(468, 6)
        drawing.add(Line(0, 3, 468, 3, strokeColor=colors.HexColor('#e5e7eb'), strokeWidth=1))
        return drawing

    def create_seal_stamp(self, title: str, subtitle: str) -> Drawing:
        """Cachet circulaire simulé SIMCO"""
        size = 180
        d = Drawing(size, size)
        center = size/2
        outer = Circle(center, center, 80, strokeColor=colors.HexColor('#0ea5e9'), strokeWidth=3, fillColor=None)
        inner = Circle(center, center, 60, strokeColor=colors.HexColor('#0ea5e9'), strokeWidth=1.5, fillColor=None)
        band = Rect(center-62, center-20, 124, 40, strokeColor=colors.HexColor('#0ea5e9'), fillColor=colors.HexColor('#e0f2fe'))
        from reportlab.graphics.shapes import String
        d.add(outer)
        d.add(inner)
        d.add(band)
        d.add(String(center, center+38, title, fontSize=12, fillColor=colors.HexColor('#0ea5e9'), textAnchor='middle'))
        d.add(String(center, center-36, subtitle, fontSize=9, fillColor=colors.HexColor('#0ea5e9'), textAnchor='middle'))
        d.add(String(center, center-3, "SIMCO", fontSize=22, fillColor=colors.HexColor('#0f172a'), textAnchor='middle'))
        return d
    
    def create_knowledge_curve(self, progress_percentage: int) -> Drawing:
        """Crée une courbe de connaissance simple avec ticks et position"""
        drawing = Drawing(520, 220)
        x0, x1, y = 40, 480, 150
        drawing.add(Line(x0, y, x1, y, strokeColor=colors.grey, strokeWidth=1.5))

        phases = [0, 20, 40, 60, 80, 100]
        labels = ["Incompétence inconsciente", "Incompétence consciente", "Conscience", "Compétence", "Maîtrise"]

        from reportlab.graphics.shapes import String
        for i, phase in enumerate(phases):
            px = x0 + (x1 - x0) * (phase / 100.0)
            drawing.add(Line(px, y-6, px, y+6, strokeColor=colors.HexColor('#b0b0b0'), strokeWidth=1))
            if i < len(labels):
                drawing.add(String(px, y+20, labels[i], fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#4a5568')))

        ux = x0 + (x1 - x0) * (max(0, min(100, progress_percentage)) / 100.0)
        drawing.add(Circle(ux, y, 7, fillColor=colors.HexColor('#e74c3c'), strokeColor=colors.HexColor('#c0392b')))
        drawing.add(String(ux, y-18, f"{progress_percentage}%", fontSize=9, textAnchor='middle', fillColor=colors.HexColor('#2d3748')))
        drawing.add(String(ux, y-34, "👤", fontSize=14, textAnchor='middle'))

        return drawing
    
    def create_error_analysis_chart(self, correct_answers: int, total_answers: int) -> Drawing:
        """Crée un graphique d'analyse des erreurs"""
        drawing = Drawing(400, 200)
        
        wrong_answers = total_answers - correct_answers
        
        # Graphique en barres
        data = [
            [correct_answers, wrong_answers]
        ]
        
        bc = VerticalBarChart()
        bc.x = 50
        bc.y = 50
        bc.height = 125
        bc.width = 300
        bc.data = data
        
        bc.bars[0].fillColor = colors.HexColor('#27ae60')
        bc.bars[1].fillColor = colors.HexColor('#e74c3c')
        
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = max(total_answers, 10)
        bc.valueAxis.valueStep = 1
        
        bc.categoryAxis.labels.boxAnchor = 'n'
        bc.categoryAxis.labels.dx = 0
        bc.categoryAxis.labels.dy = -15
        bc.categoryAxis.labels.angle = 0
        bc.categoryAxis.categoryNames = ['Correctes', 'Incorrectes']
        
        drawing.add(bc)
        
        return drawing
    
    def generate_comprehensive_pdf(self, report_data: Dict[str, Any], session_data: Dict[str, Any], 
                                  facial_analysis: Dict[str, Any] = None) -> bytes:
        """Génère un PDF complet avec tous les éléments visuels"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, 
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # En-tête professionnel
        story.append(self.create_header_banner())
        story.append(Spacer(1, 12))
        title = Paragraph("RAPPORT D'ÉVALUATION COGNITIVE COMPLET", self.styles['CustomTitle'])
        story.append(title)
        story.append(Paragraph("SIMCO · Système Intelligent Multimodal d'Évaluation Cognitive", self.styles['Muted']))
        story.append(Spacer(1, 10))
        story.append(self.create_section_divider())
        story.append(Spacer(1, 16))
        
        # 1. Informations générales
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        story.append(Paragraph("1. Informations générales", self.styles['CustomHeading']))
        info_text = f"""
        <b>Nom/ID étudiant:</b> {session_data.get('student_id', 'N/A')}<br/>
        <b>Date de l’évaluation:</b> {date_str}<br/>
        <b>Contexte de l’épreuve:</b> {report_data.get('context', 'QCM, courte durée, analyse multimodale')}<br/>
        <b>ID Session:</b> {session_data.get('id', 'N/A')}<br/>
        """
        story.append(Paragraph(info_text, self.styles['CustomBody']))
        story.append(Spacer(1, 30))
        
        # 2. Performance réelle
        score = session_data.get('score', 0)
        score_percentage = int(score * 100) if score <= 1 else int(score)
        
        story.append(Paragraph("2. Performance réelle", self.styles['CustomHeading']))
        
        try:
            score_circle = self.create_score_circle(score_percentage)
            story.append(score_circle)
        except Exception as e:
            print(f"DEBUG: Error creating score circle: {e}")
            story.append(Paragraph(f"<b>Score:</b> {score_percentage}%", self.styles['CustomBody']))
        
        story.append(Spacer(1, 20))
        
        avg_group = report_data.get('group_average', None)
        score_details = f"""
        <b>Score obtenu:</b> {score_percentage}%<br/>
        <b>Répartition des réponses (bonnes/total):</b> {session_data.get('answered_questions', 0)}/{session_data.get('total_questions', 0)}<br/>
        <b>Moyenne du groupe:</b> {f"{int(avg_group*100)}%" if isinstance(avg_group,(int,float)) and avg_group<=1 else (str(avg_group) if avg_group is not None else 'N/A')}<br/>
        <b>Notions maîtrisées vs notions à renforcer:</b> {score_percentage}% / {100-score_percentage}%
        """
        story.append(Paragraph(score_details, self.styles['CustomBody']))
        story.append(Spacer(1, 30))

        # 3. Confiance déclarée
        story.append(Paragraph("3. Confiance déclarée", self.styles['CustomHeading']))
        declared_conf = report_data.get('cognitive_profile', {}).get('global_confidence', None)
        if declared_conf is not None:
            gap = (declared_conf*100) - score_percentage
            story.append(Paragraph(f"<b>Moyenne de confiance globale:</b> {declared_conf*100:.0f}%", self.styles['CustomBody']))
            story.append(Paragraph(f"<b>Écart entre confiance et performance réelle:</b> {gap:+.0f} points", self.styles['CustomBody']))
        else:
            story.append(Paragraph("Niveau de confiance globale non disponible.", self.styles['CustomBody']))
        story.append(Spacer(1, 30))
        
        # 4. Position sur la courbe de connaissance
        if report_data.get('knowledge_position'):
            story.append(Paragraph("4. Position sur la courbe de connaissance", self.styles['CustomHeading']))
            
            position = report_data['knowledge_position']
            progress = position.get('progress_percentage', 0)
            
            try:
                knowledge_curve = self.create_knowledge_curve(progress)
                story.append(knowledge_curve)
            except Exception as e:
                print(f"DEBUG: Error creating knowledge curve: {e}")
                story.append(Paragraph(f"<b>Progression:</b> {progress}%", self.styles['CustomBody']))
            
            story.append(Spacer(1, 20))
            
            position_info = f"""
            <b>Phase Actuelle:</b> {position.get('phase', 'Non déterminée')}<br/>
            <b>Description:</b> {position.get('description', 'Non disponible')}<br/>
            <b>Prochaine Étape:</b> {position.get('next_step', 'Non définie')}
            """
            story.append(Paragraph(position_info, self.styles['CustomBody']))
            story.append(Spacer(1, 30))
        
        # 5. Analyse des erreurs
        if report_data.get('performance_analysis'):
            story.append(Paragraph("5. Analyse des erreurs", self.styles['CustomHeading']))
            
            perf = report_data['performance_analysis']
            correct = perf.get('correct_answers', 0)
            total = perf.get('total_answers', 0)
            
            if total > 0:
                try:
                    error_chart = self.create_error_analysis_chart(correct, total)
                    story.append(error_chart)
                except Exception as e:
                    print(f"DEBUG: Error creating error chart: {e}")
            
            story.append(Spacer(1, 20))
            
            error_analysis = f"""
            <b>Taux de Précision:</b> {perf.get('accuracy_rate', 0) * 100:.1f}%<br/>
            <b>Réponses Correctes:</b> {correct}/{total}<br/>
            <b>Temps Moyen:</b> {perf.get('avg_response_time', 0):.0f}ms
            """
            story.append(Paragraph(error_analysis, self.styles['CustomBody']))
            story.append(Spacer(1, 30))
        
        # 6. Profil cognitif
        if report_data.get('cognitive_profile'):
            story.append(Paragraph("6. Profil cognitif", self.styles['CustomHeading']))
            
            profile = report_data['cognitive_profile']
            profile_info = f"""
            <b>Type de Profil:</b> {profile.get('profile_type', 'Non déterminé')}<br/>
            <b>Description:</b> {profile.get('profile_description', 'Non disponible')}<br/>
            <b>Score Cognitif Global:</b> {profile.get('cognitive_score', 0) * 100:.1f}%<br/>
            <b>Score de Performance:</b> {profile.get('performance_score', 0) * 100:.1f}%<br/>
            <b>Score de Calibration:</b> {profile.get('calibration_score', 0) * 100:.1f}%
            """
            story.append(Paragraph(profile_info, self.styles['CustomBody']))
            story.append(Spacer(1, 20))
            
            # Forces et Faiblesses
            if profile.get('strengths'):
                story.append(Paragraph("💪 POINTS FORTS", self.styles['CustomHeading']))
                strengths_text = "<br/>".join([f"• {s.replace('_', ' ')}" for s in profile['strengths']])
                story.append(Paragraph(strengths_text, self.styles['CustomBody']))
                story.append(Spacer(1, 15))
            
            if profile.get('weaknesses'):
                story.append(Paragraph("🎯 AXES D'AMÉLIORATION", self.styles['CustomHeading']))
                weaknesses_text = "<br/>".join([f"• {w.replace('_', ' ')}" for w in profile['weaknesses']])
                story.append(Paragraph(weaknesses_text, self.styles['CustomBody']))
                story.append(Spacer(1, 30))
        
        # 7. Détection des biais cognitifs (heuristique)
        try:
            perf_pct = score_percentage
            dc = report_data.get('cognitive_profile', {}).get('global_confidence', None)
            bias_lines = []
            if dc is not None:
                conf_pct = int(dc * 100)
                if perf_pct <= 50 and conf_pct >= perf_pct + 20:
                    bias_lines.append("• Effet Dunning–Kruger: confiance élevée malgré des performances faibles")
                if perf_pct >= 70 and conf_pct <= perf_pct - 20:
                    bias_lines.append("• Syndrome de l’imposteur: sous-estimation malgré de bonnes performances")
            if bias_lines:
                story.append(Paragraph("7. Détection des biais cognitifs", self.styles['CustomHeading']))
                story.append(Paragraph("<br/>".join(bias_lines), self.styles['CustomBody']))
                story.append(Spacer(1, 20))
        except Exception:
            pass

        # 8. Plan d'Amélioration
        if report_data.get('recommendations'):
            story.append(Paragraph("8. Plan d'amélioration personnalisé", self.styles['CustomHeading']))
            
            for i, rec in enumerate(report_data['recommendations'], 1):
                rec_text = f"<b>{i}.</b> {rec}"
                story.append(Paragraph(rec_text, self.styles['CustomBody']))
                story.append(Spacer(1, 10))
            
            story.append(Spacer(1, 30))
        
        # 9. Analyse des signaux non verbaux
        if facial_analysis:
            story.append(Paragraph("9. Analyse des signaux non verbaux", self.styles['CustomHeading']))
            
            facial_info = f"""
            <b>Indicateurs captés:</b> expressions faciales (heuristiques OpenCV/MediaPipe)<br/>
            <b>Confiance implicite estimée:</b> {facial_analysis.get('confidence', 0) * 100:.0f}%<br/>
            <b>Niveau de stress:</b> {facial_analysis.get('stress', 0) * 100:.0f}%<br/>
            <b>Engagement:</b> {facial_analysis.get('engagement', 0) * 100:.0f}%
            """
            story.append(Paragraph(facial_info, self.styles['CustomBody']))
            story.append(Spacer(1, 30))

        # 10. Synthèse visuelle
        story.append(Paragraph("10. Synthèse visuelle", self.styles['CustomHeading']))
        story.append(Paragraph("Graphiques croisés performance vs confiance, et position sur la courbe de connaissance présentés ci-dessus.", self.styles['CustomBody']))
        story.append(Spacer(1, 20))
        
        # Conclusion
        story.append(Paragraph("📋 CONCLUSION", self.styles['CustomHeading']))
        
        conclusion = f"""
        Cette évaluation cognitive multimodale fournit une analyse complète de vos performances,
        intégrant les réponses aux questions, la confiance déclarée et les indicateurs comportementaux.
        
        Les recommandations personnalisées ci-dessus vous aideront à progresser efficacement
        dans votre apprentissage. Continuez à pratiquer régulièrement pour améliorer vos compétences.
        """
        story.append(Paragraph(conclusion, self.styles['CustomBody']))
        
        # Pied de page avec cachet
        story.append(Spacer(1, 12))
        story.append(self.create_section_divider())
        story.append(Spacer(1, 14))
        story.append(self.create_seal_stamp("RAPPORT VALIDÉ", date_str))
        story.append(Spacer(1, 8))
        story.append(Paragraph("Signature et cachet électroniques SIMCO", self.styles['Muted']))
        
        # Construire le PDF
        try:
            doc.build(story)
        except Exception as e:
            print(f"DEBUG: Error building PDF: {e}")
            # Créer un PDF minimal en cas d'erreur
            story = [
                Paragraph("RAPPORT D'ÉVALUATION", self.styles['CustomTitle']),
                Spacer(1, 20),
                Paragraph(f"Session: {session_data.get('id', 'N/A')}", self.styles['CustomBody']),
                Paragraph(f"Score: {score_percentage}%", self.styles['CustomBody']),
                Paragraph("Erreur lors de la génération complète du rapport.", self.styles['CustomBody'])
            ]
            doc.build(story)
        
        # Récupérer les bytes du PDF
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes

# Instance globale du service
pdf_service = PDFReportService()
