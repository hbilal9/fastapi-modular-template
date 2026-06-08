lint:
	uv run ruff check ./app

format:
	uv run ruff format ./app

start:
	uv run uvicorn app.main:app --reload

worker:
	uv run celery -A app.core.celery_app worker -l info

beat:
	uv run celery -A app.core.celery_app beat -l info

alembic-revision:
	uv run alembic revision --autogenerate -m "$(MSG)"

alembic-upgrade:
	uv run alembic upgrade head
