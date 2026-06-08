# db-models-template

Небольшая библиотека-шаблон на SQLAlchemy 2.0 + Alembic для переноса одной схемы БД между контурами (тирами). Лесенка контуров двухуровневая: `main` (базовый, самый широкий) и `dev` (самый специфичный). Пакет можно использовать и как зависимость (`from db_models.models.example import Foo`), и запускать как миграционную задачу (локально, через docker-compose или как k8s `Job`).

В качестве демонстрации в комплекте идёт схема `example` с моделями `Foo` и `Bar`, а dev-тир добавляет к `bar` диагностическую колонку `debug_note` через механизм table override.

## Что внутри

- `db_models/tiers.py` — единственный источник правды по названиям контуров; экспортирует `Tier` (StrEnum), `LADDER = (main, dev)`, `BASE_TIER` (= `main`) и `ENV_ALLOWED_TIERS`
- `db_models/config.py` — читает переменные окружения (`DATABASE_*`, `MIGRATION_ENV`) и строит `SQLALCHEMY_DATABASE_URI`
- `db_models/models/` — ORM-модели по схемам БД (демо-схема `example` с моделями `Foo`/`Bar`)
- `migrations/` — Alembic-окружение и ревизии (две независимые ветки: `main` и `dev`)
- `db_models/cli/` — консольные команды (после `pip install -e .` доступны как entry points в активном окружении):
  - `create-migration` — создание миграций с корректным `branch-label`: при `--autogenerate` с контура `X` каскадно генерируются ревизии для `X` и всех контуров ниже по лесенке (`main` → `dev`); пустые файлы удаляются; после каскада перегенерируются `__init__.pyi` стабы базового тира
  - `generate-stubs` — AST-парсит файлы базового тира всех схем и создаёт `db_models/models/<schema>/__init__.pyi`; IDE видит статические реэкспорты вместо динамического `auto_import_models`; можно запускать вручную
  - `upgrade-migration` / `downgrade-migration` / `run-migration` — применение/откат миграций с выставленным `MIGRATION_ENV`; цель `alembic upgrade` — `<контур>@head` (`run-migration` — это CMD миграционного контейнера)
  - `create-schema` — создание заготовки нового пакета схемы (`db_models/models/<schema>/`) вместе с подпапками для каждого не-базового тира (`dev/`) и корректными `__init__.py`
  - `generate-models` — генерация моделей из живой БД
- `Dockerfile` / `Dockerfile.dev` — образы для применения миграций на базе `python:3.12-slim`
- `requirements.txt` — зависимости (`alembic`, `SQLAlchemy`, `psycopg`)

## Быстрый старт

1. Установить зависимости:

```bash
pip install -e ".[alembic]"
```

2. Поднять локальный Postgres:

```bash
docker compose up -d db
```

3. Выполнить миграции.

**Через консольную команду (рекомендуется):**

```bash
upgrade-migration dev
```

Команда доступна после `pip install -e .` и работает из любого каталога (кросс-платформенно, в т.ч. из корня родительского проекта).

**Через Docker Compose** (не требует локального Python-окружения):

```bash
docker compose --profile dev up alembic_dev
```

Профили соответствуют контурам: `main` и `dev`. Каждый сервис ждёт готовности БД через healthcheck и запускает `run-migration` (CMD образа) с нужным `MIGRATION_ENV`.

**Напрямую через Alembic:**

```bash
MIGRATION_ENV=dev alembic upgrade dev@head
```

## Контуры миграций

В `migrations/env.py` используется `MIGRATION_ENV`. Лесенка контуров задана в `db_models/tiers.py` как `LADDER = (main, dev)`; каждый контур «содержит» себя и все нижестоящие. Структура папок моделей отражает контур:

| Папка | Тир | Входит в |
|---|---|---|
| `db_models/models/<schema>/` | `main` | `main`, `dev` |
| `db_models/models/<schema>/dev/` | `dev` | только `dev` |

- `main` — только модели без спецпапки (базовый тир)
- `dev` — `main` + модели из `dev/`

Tier-подпапка может содержать файл с тем же именем (стемом), что и базовая модель — в этом случае она **заменяет** её для данного и нижних контуров (table override). Так, демо-файл `db_models/models/example/dev/bar.py` добавляет к `example.bar` колонку `debug_note` только в dev, не трогая `main`. Подробнее: [CONTRIBUTING.md](docs/CONTRIBUTING.md#добавление-tier-специфичной-колонки-к-существующей-базовой-таблице).

Alembic-ревизии хранятся раздельно по контурам и обнаруживаются рекурсивно (`alembic.ini`: `recursive_version_locations = true`, без перечисления тиров):

- `migrations/versions/main`
- `migrations/versions/dev`

Ветки `main` и `dev` независимы (без `depends_on` между ними); у каждой свой head, цель — `<контур>@head`.

Локальное значение по умолчанию для `DATABASE_NAME` совпадает с именем тира (`main` -> `main`, `dev` -> `dev`). Если `DATABASE_NAME` задан явно, используется значение из `env` (для реальных БД).

Автогенерация использует двухуровневый фильтр:

- `include_name` — ранняя фильтрация reflected схем/таблиц (до детальной рефлексии БД);
- `include_object` — точечные правила на уровне объектов (например, `Column.info.skip_autogenerate`).

## Запуск в Kubernetes

Helm-чарт находится в `helm/`. Для каждого контура предусмотрен свой values-файл.

1. Собрать и загрузить образ:

```bash
docker build -t registry.example.com/db-models-template:<tag> .
docker push registry.example.com/db-models-template:<tag>
```

2. В кластере должны существовать:
   - **ConfigMap** `db-models-template` — переменные `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`
   - **Secret** `db-models-template-credentials` — `DATABASE_PASSWORD`
   - **Secret** `db-models-template-tls` — CA-бандл PostgreSQL (`ca-bundle.pem`)

3. Запустить Job через Helm:

```bash
helm upgrade --install db-models-template helm/ -f helm/values-dev.yaml
```

Контейнер читает `MIGRATION_ENV` из values и вызывает `run-migration` — итоговая команда: `alembic upgrade <контур>@head`.

## Создание новой схемы БД

Скаффолдинг нового пакета схемы (создаёт `db_models/models/<schema>/` с подпапкой для каждого не-базового тира — `dev/` — и `__init__.py` с базовым классом):

```bash
create-schema <schema_name>
```

После этого используйте команду генерации моделей (см. ниже) или создайте файлы вручную по аналогии с демо-схемой `example`.

## Генерация моделей из БД

Команда `generate-models` подключается к живой БД, отражает схему и генерирует готовые к ревью `.py`-файлы моделей:

```bash
generate-models example
generate-models example dev --tables foo,bar
generate-models example --overwrite
```

Аргументы:

| Аргумент | Описание |
|---|---|
| `schema` | Имя PostgreSQL-схемы (`example`, …) — обязательный |
| `tier` | `main` (по умолчанию) \| `dev` — куда кладётся результат |
| `--tables t1,t2` | Генерировать только указанные таблицы |
| `--overwrite` | Перезаписывать существующие файлы (по умолчанию — пропустить) |

Вывод: `db_models/models/<schema>/` для `main`, `db_models/models/<schema>/<tier>/` для остальных тиров.

Подключение через те же переменные окружения, что и `db_models/config.py`: `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`.

Перед запуском схема должна быть создана через `create-schema <schema>`. Сгенерированные файлы — отправная точка: контрибьютор проверяет правила cascade у связей и заполняет описание модели в docstring.

## Использование моделей в другом проекте

### Через git-зависимость

```bash
pip install "db-models-template @ git+https://github.com/org/db-models-template.git@v0.1.0"
```

### Через приватный пакетный реестр

```bash
python -m build
twine upload --repository-url https://nexus.example.com/simple/ dist/*
```

Затем в потребителе:

```bash
pip install --index-url https://nexus.example.com/simple/ db-models-template
```

После установки импорт моделей:

```python
from db_models import models                          # пакет моделей целиком
from db_models.models import Base
from db_models.models.example import Foo, Bar
from db_models.config import get_migration_env
```

Подробный процесс контрибьюта: [CONTRIBUTING.md](docs/CONTRIBUTING.md)
