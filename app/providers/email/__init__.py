from functools import lru_cache

from app.core.config import settings
from app.providers.email.base import EmailProvider
from app.providers.email.console import ConsoleEmailProvider
from app.providers.email.smtp import SMTPEmailProvider

_PROVIDERS: dict[str, type[EmailProvider]] = {
    "console": ConsoleEmailProvider,
    "smtp": SMTPEmailProvider,
}


@lru_cache
def get_email_provider() -> EmailProvider:
    provider = _PROVIDERS.get(settings.EMAIL_PROVIDER, ConsoleEmailProvider)
    return provider()
