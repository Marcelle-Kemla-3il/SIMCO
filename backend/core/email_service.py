"""
email_service.py
Envoie le rapport PDF par email via Gmail SMTP.

Configuration requise dans .env :
  GMAIL_ADDRESS  = votre.adresse@gmail.com
  GMAIL_PASSWORD = votre_mot_de_passe_application

⚠️ Utiliser un "Mot de passe d'application" Google,
   pas votre mot de passe Gmail normal.
   Créer ici : https://myaccount.google.com/apppasswords
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text       import MIMEText
from email.mime.base       import MIMEBase
from email                 import encoders
from datetime              import datetime


def send_report_email(
    recipient_email: str,
    student_name: str,
    subject: str,
    pdf_bytes: bytes,
    score: float,
    profil_ml: str,
    zone_label: str
) -> dict:
    """
    Envoie le rapport PDF par email.

    Paramètres :
        recipient_email : email de l'étudiant
        student_name    : prénom/nom
        subject         : sujet du quiz
        pdf_bytes       : rapport PDF en bytes
        score           : score en pourcentage
        profil_ml       : profil DK détecté
        zone_label      : zone DK

    Retourne :
        { "success": True/False, "message": "..." }
    """
    # ─── Récupérer les credentials depuis les variables d'environnement ───────
    gmail_address  = os.getenv("GMAIL_ADDRESS",  "")
    gmail_password = os.getenv("GMAIL_PASSWORD", "")

    if not gmail_address or not gmail_password:
        return {
            "success": False,
            "message": "Email non configuré. Ajoutez GMAIL_ADDRESS et GMAIL_PASSWORD dans .env"
        }

    if not recipient_email or "@" not in recipient_email:
        return {
            "success": False,
            "message": "Adresse email invalide"
        }

    try:
        # ─── Construire l'email ───────────────────────────────────────────────
        msg = MIMEMultipart("mixed")
        msg["From"]    = f"SIMCO Évaluation <{gmail_address}>"
        msg["To"]      = recipient_email
        msg["Subject"] = f"📊 Votre rapport SIMCO — {subject} — {datetime.now().strftime('%d/%m/%Y')}"

        # Corps de l'email HTML
        profil_emoji = {
            "overconfident": "⚠️",
            "impostor": "💪",
            "calibrated": "🎯",
            "conscious": "📚"
        }.get(profil_ml, "📊")

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">

            <div style="background: linear-gradient(135deg, #1a6b5a, #4ecdc4); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">SIMCO</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0;">Système Intelligent Multimodal d'Évaluation Cognitive</p>
            </div>

            <div style="background: #f8fffe; padding: 30px; border: 1px solid #e0e0e0;">
                <h2 style="color: #1a6b5a;">Bonjour {student_name},</h2>
                <p>Votre rapport d'évaluation SIMCO est prêt. Voici un résumé de vos résultats :</p>

                <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px; font-weight: bold; color: #666; width: 40%;">📚 Sujet</td>
                            <td style="padding: 10px; color: #333;">{subject}</td>
                        </tr>
                        <tr style="background: #f5f5f5;">
                            <td style="padding: 10px; font-weight: bold; color: #666;">📊 Score</td>
                            <td style="padding: 10px; color: #1a6b5a; font-size: 20px; font-weight: bold;">{score:.0f}%</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; font-weight: bold; color: #666;">🧠 Zone DK</td>
                            <td style="padding: 10px; color: #333;">{zone_label}</td>
                        </tr>
                        <tr style="background: #f5f5f5;">
                            <td style="padding: 10px; font-weight: bold; color: #666;">🤖 Profil ML</td>
                            <td style="padding: 10px; color: #333;">{profil_emoji} {profil_ml.capitalize() if profil_ml else 'N/A'}</td>
                        </tr>
                    </table>
                </div>

                <p style="color: #666; font-size: 14px;">
                    Le rapport PDF complet est joint à cet email. Il contient :
                </p>
                <ul style="color: #666; font-size: 14px;">
                    <li>Votre positionnement sur la courbe de Dunning-Kruger</li>
                    <li>Les notions spécifiques à réviser</li>
                    <li>Les compétences que vous maîtrisez sans le savoir</li>
                    <li>Des recommandations personnalisées</li>
                </ul>

                <div style="background: #e8f8f5; border-left: 4px solid #4ecdc4; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <p style="margin: 0; color: #1a6b5a; font-size: 14px;">
                        💡 Utilisez ce rapport pour guider votre apprentissage et améliorer votre auto-évaluation.
                    </p>
                </div>
            </div>

            <div style="background: #1a6b5a; padding: 15px; text-align: center; border-radius: 0 0 8px 8px;">
                <p style="color: rgba(255,255,255,0.7); font-size: 12px; margin: 0;">
                    © 2026 Projet SIMCO — Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}
                </p>
            </div>

        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # ─── Attacher le PDF ──────────────────────────────────────────────────
        filename = f"rapport_SIMCO_{student_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(pdf_bytes)
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}"
        )
        msg.attach(attachment)

        # ─── Envoyer via Gmail SMTP ───────────────────────────────────────────
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, recipient_email, msg.as_string())

        print(f"✅ Email envoyé à {recipient_email}")
        return {
            "success": True,
            "message": f"Rapport envoyé à {recipient_email}"
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "Erreur d'authentification Gmail. Vérifiez GMAIL_ADDRESS et GMAIL_PASSWORD dans .env"
        }
    except smtplib.SMTPException as e:
        return {
            "success": False,
            "message": f"Erreur SMTP : {str(e)}"
        }
    except Exception as e:
        print(f"❌ Email error: {e}")
        return {
            "success": False,
            "message": f"Erreur envoi email : {str(e)}"
        }