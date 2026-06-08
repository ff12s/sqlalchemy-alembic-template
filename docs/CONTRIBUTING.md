# CONTRIBUTING

## Требования

- Python 3.11+
- Docker + Docker Compose
- Доступ к репозиторию

## Образы Docker

В проекте два Dockerfile:

| Файл | Назначение | База |
|---|---|---|
| `Dockerfile` | Образ для применения миграций | `python:3.12-slim` |
| `Dockerfile.dev` | Локальная разработка и docker-compose | `python:3.12-slim` |

**Образ для миграций** собирается без дополнительных аргументов и устанавливает зависимости из `requirements.txt` (`alembic`, `SQLAlchemy`, `psycopg`):

```bash
docker build -t registry.example.com/db-models-template:<tag> .
```

**Локальный образ** (для docker-compose) собирается из `Dockerfile.dev`:

```bash
docker compose --profile dev up --build alembic_dev
```

## Подготовка окружения

```bash
pip install -e ".[alembic]"
pre-commit install
docker compose up -d db
```

Проверка подключения (контур должен совпадать с целевой БД и веткой миграций):

```bash
upgrade-migration dev
```

Вручную: выставьте `MIGRATION_ENV` и вызовите `alembic upgrade <контур>@head` (например `alembic upgrade main@head`).

## Локальный запуск миграций через Docker Compose

`docker-compose.yml` содержит сервисы для каждого контура, изолированные через [profiles](https://docs.docker.com/compose/profiles/). Сервисы не запускаются при `docker compose up` без явного указания профиля.

Каждый сервис использует `Dockerfile.dev`, выставляет `MIGRATION_ENV` и `DATABASE_NAME`, ждёт healthcheck БД и запускает `run-migration` (CMD образа).

| Контур | Сервис | DATABASE_NAME | Профиль |
|---|---|---|---|
| `main` | `alembic_main` | `main` | `main` |
| `dev` | `alembic_dev` | `dev` | `dev` |

**Запустить миграции одного контура:**

```bash
docker compose --profile dev up alembic_dev
```

**Пересобрать образ при изменениях:**

```bash
docker compose --profile dev up --build alembic_dev
```

**Запустить все контуры последовательно** (например, для полного накатывания локальной БД):

```bash
for tier in main dev; do
  docker compose --profile $tier up alembic_$tier
done
```

Windows (PowerShell):

```powershell
foreach ($tier in @("main","dev")) {
  docker compose --profile $tier up alembic_$tier
}
```

## Добавление нового контура

Все названия контуров централизованы в `db_models/tiers.py`. Чтобы добавить новый контур:

1. Добавьте член в `Tier` enum.
2. Вставьте его в нужную позицию в `LADDER` — `ENV_ALLOWED_TIERS` пересчитывается автоматически.
3. Создайте папки `migrations/versions/<tier>/` и подпапки `<schema>/<tier>/` там, где нужно.

## Ветки и контуры

- `develop` → `dev`
- `master` → остальные кластеры (`main`)

Фиче-ветки для dev-тира создавайте от `develop`.

## Как создавать новую схему БД

Для создания пакета новой схемы используйте команду-скаффолдер:

```bash
create-schema <schema_name>
```

Команда создаёт:

- `db_models/models/<schema_name>/__init__.py` — базовый класс `Base<SchemaName>` и вызов `auto_import_models`
- `db_models/models/<schema_name>/dev/__init__.py` — для каждого не-базового тира из `LADDER`

После этого сгенерируйте модели из живой БД (см. следующий раздел) или создайте файлы вручную, затем создайте начальную миграцию через `create-migration`.

## Как генерировать модели из БД

Команда `generate-models` подключается к живой БД, отражает схему и создаёт файлы моделей, следующие всем конвенциям проекта (MappedAsDataclass, Russian docstring, base class, with_constraints и т.д.).

**Предварительные условия:** БД доступна, схема уже создана через `create-schema`.

Сгенерировать все таблицы схемы:

```bash
generate-models example
```

Только указанные таблицы (для тира `dev`):

```bash
generate-models example dev --tables foo,bar
```

Перезаписать существующие файлы:

```bash
generate-models example --overwrite
```

После генерации:

1. Проверьте правила `cascade` у `relationship()` — генератор намеренно их не заполняет.
2. Заполните описание модели в docstring (первая строка `"""Модель <описание>.`).
3. Обратите внимание на строки с `# TODO:` — они требуют ручной доработки.
4. Убедитесь, что файл чисто импортируется: `python -c "import db_models.models.example.<table_name>"`.
5. Запустите `pre-commit run --all-files` перед PR.

## Как создавать миграции

### Рекомендуемый путь: autogenerate (нужна живая БД)

```bash
create-migration main "add foo column" --autogenerate
create-migration dev "add debug table" --autogenerate
```

При `--autogenerate` с контура `main` последовательно запускается autogenerate для всех контуров ниже по лесенке (`main` → `dev`). Пустые сгенерированные файлы удаляются. После каскада автоматически перегенерируются `__init__.pyi` стабы для всех схем — коммитьте их вместе с миграцией.

### Альтернативный путь: ручная миграция (без БД)

```bash
create-migration main "manual migration" --manual
```

После этого заполните `upgrade()`/`downgrade()` вручную.

Перед `--autogenerate` база должна быть на актуальной ревизии ветки; подтяните схему командой обновления:

```bash
upgrade-migration main
```

## Branch labels

Ветки Alembic **независимы** (без `depends_on` между контурами). Для первой ревизии ветки: `--branch-label <контур> --head base`; для следующих: `--head <контур>@head`.

При `--autogenerate` с контура `X` команда `create-migration` последовательно генерирует ревизии для `X` и всех контуров ниже по лесенке (`main` → `dev`); пустые файлы удаляются. При `--manual` создаётся только одна ревизия для выбранного контура.

Ревизии сохраняются в отдельные каталоги и обнаруживаются рекурсивно (`alembic.ini`: `recursive_version_locations = true`):

- `migrations/versions/main`
- `migrations/versions/dev`

## Как работает фильтрация autogenerate

В `migrations/env.py` набор таблиц зависит от `MIGRATION_ENV`:

- `main` -> только модели без спецпапки (обычные файлы схем);
- `dev` -> `main` + модели из `dev/`.

Технически используется двухуровневый фильтр:

- `include_name` отсекает лишние схемы/таблицы до детальной рефлексии;
- `include_object` оставлен для точечных исключений на уровне объектов.

Чистые функции сравнения (нормализация `server_default`, приведения типов `::type`, сигнатуры FK)
вынесены в `migrations/migration_filters.py` — их можно покрывать unit-тестами без подключения к БД
(`tests/test_migration_filters/`). Сам `migrations/env.py` импортирует их и при импорте запускает миграции.

> Маркер типизации PEP 561 (`py.typed`) лежит в корне пакета — `db_models/py.typed` — чтобы потребители
> устанавливаемого wheel видели пакет как типизированный.

Применение миграций (команда выставляет `MIGRATION_ENV` и цель `alembic upgrade <контур>@head`):

```bash
upgrade-migration main
upgrade-migration dev
```

Напрямую через Alembic (эквивалент при совпадающем `MIGRATION_ENV`):

```bash
MIGRATION_ENV=main alembic upgrade main@head
MIGRATION_ENV=dev alembic upgrade dev@head
```

## Добавление tier-специфичной колонки к существующей базовой таблице

Используйте **table override** — создайте версию базового файла в нужной tier-подпапке. В шаблоне это уже сделано: `db_models/models/example/dev/bar.py` добавляет к `example.bar` колонку `debug_note` только для dev.

### Пример: добавить колонку только для dev

1. **Создайте override-файл** `db_models/models/<schema>/dev/<table>.py`:
   - Скопируйте всё из базовой версии (`db_models/models/<schema>/<table>.py`)
   - Добавьте новые колонки
   - Первой строкой: `# OVERRIDE: dev-тир добавляет к <schema>.<table> колонку <col>.`

2. **Проверьте загрузку:**

   ```bash
   MIGRATION_ENV=dev python -c "from db_models.models.<schema> import <ModelClass>; print(<ModelClass>.__module__)"
   # → db_models.models.<schema>.dev.<table>

   MIGRATION_ENV=main python -c "from db_models.models.<schema> import <ModelClass>; print(<ModelClass>.__module__)"
   # → db_models.models.<schema>.<table>
   ```

3. **Создайте миграцию:**

   ```bash
   create-migration dev "add col X to <table>" --autogenerate
   # main — пустая, удалится автоматически
   ```

4. **Примените:** `upgrade-migration dev`

5. **Проверки перед PR:** `pre-commit run --all-files && alembic heads`

### Правила override-файла

- **Те же** `__tablename__` и имя класса, что у базовой модели
- Тот же schema-base (`BaseExample`, …)
- Все базовые колонки плюс новые
- Все стандартные конвенции: docstring, порядок полей `MappedAsDataclass`

### Most-specific-wins

Каждый контур может иметь свою версию одной таблицы. При нескольких override-файлах для одного стема побеждает **самый специфичный** тир (ниже по `LADDER`). В двухуровневой лесенке это означает: если есть `dev/tbl.py`, то `dev` видит его, а `main` — базовый файл:

| Файлы | main | dev |
|---|---|---|
| `dev/tbl.py` | базовый `tbl.py` | `dev/tbl.py` |

## Проверки перед PR

```bash
pre-commit run --all-files
alembic heads
alembic history --verbose
```

Если миграция делалась через `--autogenerate`, обязательно проверьте, что в diff нет лишних `drop_table`/`drop_column`.

## PR checklist

- Миграция лежит в `migrations/versions/<env>/`
- Имя и message миграции понятны
- `upgrade()` и `downgrade()` обратимы
- Прогон применения миграций до head вашего контура проходит локально (команда `upgrade-migration` или `alembic upgrade …@head` с тем же `MIGRATION_ENV`, что и у контура)
- Pre-commit проверки зелёные
