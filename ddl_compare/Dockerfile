FROM debian:bullseye-slim

# PG 13 dev headers для сборки (pgquarrel не собирается с PG 15). Собранный бинарник подключается к PG 15 через libpq.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git cmake build-essential \
    postgresql-server-dev-13 libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --depth 1 --branch pgquarrel_0_7_0 https://github.com/eulerto/pgquarrel.git . \
    && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_PREFIX_PATH=/usr . \
    && make && make install \
    && cd / && rm -rf /build

WORKDIR /reports
ENTRYPOINT ["pgquarrel"]
