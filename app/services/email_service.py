import smtplib
from email.message import EmailMessage
from typing import Optional
from app.core.config import settings

class EmailService:
    def __init__(self):
        # Expected settings (with safe defaults)
        self.smtp_host: str = getattr(settings, 'SMTP_HOST', '')
        self.smtp_port: int = int(getattr(settings, 'SMTP_PORT', 587) or 587)
        self.smtp_user: str = getattr(settings, 'SMTP_USER', '')
        self.smtp_password: str = getattr(settings, 'SMTP_PASSWORD', '')
        self.smtp_tls: bool = bool(getattr(settings, 'SMTP_USE_TLS', True))
        self.from_address: str = getattr(settings, 'EMAIL_FROM', self.smtp_user or 'no-reply@simco.local')

    def _can_send(self) -> bool:
        return bool(self.smtp_host and self.from_address)

    def send_email_with_attachment(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachment_bytes: Optional[bytes] = None,
        attachment_filename: Optional[str] = None,
        mime_type: str = 'application/octet-stream'
    ) -> None:
        """Send an email with optional attachment. If SMTP is not configured, log to console and return."""
        if not self._can_send():
            print("[EmailService] SMTP not configured. Skipping real send. Preview:")
            print(f"To: {to_address}\nSubject: {subject}\nBody:\n{body[:400]}...\nAttachment: {attachment_filename if attachment_bytes else 'none'}")
            return

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.from_address
        msg['To'] = to_address
        msg.set_content(body)

        if attachment_bytes and attachment_filename:
            maintype, _, subtype = mime_type.partition('/')
            msg.add_attachment(attachment_bytes, maintype=maintype or 'application', subtype=subtype or 'octet-stream', filename=attachment_filename)

        if self.smtp_tls:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

email_service = EmailService()
