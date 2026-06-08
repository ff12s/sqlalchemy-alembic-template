# Changelog

---

# 0.1.0

## Added

- Первый релиз `db-models-template` — библиотека-шаблон на SQLAlchemy 2.0 + Alembic для переноса одной
  схемы БД между контурами по двухуровневой лесенке `LADDER = (main, dev)` (`db_models/tiers.py`,
  `BASE_TIER = main`)
- `db_models/models/example/`: демо-схема `example` с моделями `Foo` (родитель) и `Bar` (ребёнок, FK на
  `Foo`); `db_models/models/example/dev/bar.py` — table override, добавляющий колонку `debug_note`
  только для dev-тира
- `migrations/versions/main` и `migrations/versions/dev`: две независимые Alembic-ветки (`main@head`,
  `dev@head`) с начальными ревизиями схемы `example`; `alembic.ini` использует
  `recursive_version_locations = true` (без перечисления тиров)
- `db_models/cli/`: консольные команды (`create-migration`, `upgrade-migration`, `downgrade-migration`,
  `run-migration`, `create-schema`, `generate-models`, `generate-stubs`), доступные после
  `pip install -e .` и из любого каталога
- `Dockerfile`, `Dockerfile.dev`: образы для применения миграций на базе `python:3.12-slim`;
  `docker-compose.yml` с профилями `main` и `dev`; Helm-чарт в `helm/`
- Документация (`README.md`, `docs/CONTRIBUTING.md`, `docs/RUNBOOK.md`): описание двухуровневой лесенки,
  механизма table override и рабочего процесса миграций
