from datetime import UTC, datetime

from sqlalchemy import delete

from app.core.celery_app import celery_app
from app.core.worker import run_async, worker_session_factory
from app.modules.auth.models import RefreshToken


@celery_app.task(name="auth.purge_expired_refresh_tokens")
def purge_expired_refresh_tokens() -> int:
    return run_async(_purge())


async def _purge() -> int:
    async with worker_session_factory()() as db:
        result = await db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.now(UTC))
        )
        await db.commit()
        return result.rowcount or 0
