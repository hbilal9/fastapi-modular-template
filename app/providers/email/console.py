import logging

from app.providers.email.base import EmailProvider

logger = logging.getLogger(__name__)


class ConsoleEmailProvider(EmailProvider):
    async def send(self, to: str, subject: str, html: str) -> None:
        logger.info("email_console", extra={"to": to, "subject": subject})
