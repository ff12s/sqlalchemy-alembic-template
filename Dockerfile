# ── Stage: wheel-builder ───────────────────────────────────────────────────────
# Собирает wheel из исходников проекта (без зависимостей).
FROM python:3.12-slim AS wheel-builder

WORKDIR /opt/db-models-template

COPY pyproject.toml setup.py requirements.txt release_parameters.yml ./
COPY db_models ./db_models
COPY migrations ./migrations

RUN pip wheel . --no-deps -w dist


# ── Stage: migration (runtime) ──────────────────────────────────────────────────
# Минимальный образ для применения миграций через alembic.
# Должен быть последним, чтобы docker build без --target собирал именно migration-образ.
FROM python:3.12-slim AS migration

WORKDIR /opt/db-models-template

COPY pyproject.toml setup.py requirements.txt release_parameters.yml ./
COPY db_models ./db_models
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --no-cache-dir ".[alembic]"

CMD ["run-migration"]
