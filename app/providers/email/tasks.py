from app.core.celery_app import celery_app
from app.core.worker import run_async
from app.providers.email import get_email_provider


@celery_app.task(name="email.send")
def send_email(to: str, subject: str, html: str) -> None:
    run_async(get_email_provider().send(to, subject, html))
