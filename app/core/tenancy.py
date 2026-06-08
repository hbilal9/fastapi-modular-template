import uuid
from contextvars import ContextVar

from sqlalchemy import Uuid, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

current_org_id: ContextVar[str | None] = ContextVar("current_org_id", default=None)


class TenantMixin:
    """Add to any model that must be tenant-scoped. (org_id has no FK here so the
    template stays app-agnostic; the per-app `organizations` table owns the PK.)"""

    org_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)


async def set_tenant(session: AsyncSession, org_id: str | uuid.UUID) -> None:
    """Bind the tenant for the current transaction (transaction-local GUC)."""
    await session.execute(
        text("SELECT set_config('app.current_org', :org, true)"),
        {"org": str(org_id)},
    )


def rls_statements(table: str) -> list[str]:
    """DDL to enforce tenant isolation on a table — call from an Alembic migration."""
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
        f"CREATE POLICY tenant_isolation ON {table} "
        "USING (org_id = current_setting('app.current_org', true)::uuid) "
        "WITH CHECK (org_id = current_setting('app.current_org', true)::uuid)",
    ]
