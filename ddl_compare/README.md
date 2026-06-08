# ddl_compare — ручная проверка дрейфа схем между тирами

Опциональный **локальный** инструмент: сравнивает DDL соседних тиров (main↔dev) с помощью
[pgquarrel](https://github.com/eulerto/pgquarrel) и выгружает SQL-дельты в `reports/`.
Это вспомогательная диагностика; **в CI/CD не подключён** — основной источник истины по схеме остаётся
Alembic-autogenerate (см. `docs/CONTRIBUTING.md`).

## Запуск

```powershell
# Базы должны быть доступны контейнеру pgquarrel (по умолчанию host.docker.internal:5432).
# Параметры подключения берутся из env, иначе — локальные dev-дефолты (postgres/postgres).
$env:PGHOST = "host.docker.internal"; $env:PGPORT = "5432"
$env:PGUSER = "postgres"; $env:PGPASSWORD = "<пароль>"
./compare_schemas.ps1
```

Результат — файл `reports/<target>_to_<source>.sql`: SQL, приводящий `target` к виду `source`
(например, `dev_to_main.sql` — что не хватает в dev относительно main).

> Не храните реальные пароли в скрипте — передавайте через `$env:PGPASSWORD`.
