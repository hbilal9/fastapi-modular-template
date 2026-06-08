import smtplib
from email.message import EmailMessage

import anyio.to_thread

from app.core.config import settings
from app.providers.email.base import EmailProvider


class SMTPEmailProvider(EmailProvider):
    async def send(self, to: str, subject: str, html: str) -> None:
        await anyio.to_thread.run_sync(self._send, to, subject, html)

    def _send(self, to: str, subject: str, html: str) -> None:
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = to
        message["Subject"] = subject
        message.set_content(html, subtype="html")
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
