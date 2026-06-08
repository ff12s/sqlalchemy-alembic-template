# Helm-чарт `models` — Alembic migration Job

Запускает миграции (`run-migration` — CMD образа) как k8s `Job`. Образ читает `MIGRATION_ENV`
и применяет `alembic upgrade <tier>@head` (или downgrade, если задан `downgradeRevision`).

## Values-файлы

| Файл | Назначение |
|---|---|
| `values-main.yaml` | main-контур (`migrationEnv: "main"`) |
| `values-dev.yaml` | dev-контур (`migrationEnv: "dev"`) |

## Развёртывание

```bash
# main-контур
helm upgrade --install db-models-template . -f values-main.yaml

# dev-контур
helm upgrade --install db-models-template . -f values-dev.yaml
```

## Безопасность и лимиты (переопределяемые в values)

Шаблон `migration-job.yaml` задаёт безопасные значения по умолчанию; их можно переопределить в любом
values-файле:

```yaml
activeDeadlineSeconds: 1800          # жёсткий лимит на весь Job (с учётом ретраев)
imagePullPolicy: Always
podSecurityContext:                  # дефолт: runAsNonRoot:true + seccomp RuntimeDefault (UID назначает платформа)
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
containerSecurityContext:            # allowPrivilegeEscalation:false, drop ALL caps
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
resources:
  requests: { cpu: 100m, memory: 256Mi }
  limits:   { cpu: 500m, memory: 512Mi }
```

На обычном k8s контейнер запускается под `USER 1000` из образа (см. корневой `Dockerfile`, стейдж
`migration`), что удовлетворяет `runAsNonRoot`. На кластере с диапазонной SCC платформа подставляет UID
из разрешённого диапазона неймспейса; дефолт намеренно не фиксирует `runAsUser`, чтобы не конфликтовать с
этим диапазоном. Если контуру нужен Kerberos-keytab под root — переопределите `podSecurityContext`.

> **`version: "latest"`** в values — источник невоспроизводимости и неоднозначных откатов. Рекомендуется
> подставлять конкретный SemVer-тег из `release_parameters.yml`/CI при `helm upgrade`.
