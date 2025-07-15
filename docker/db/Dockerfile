# ── Base Postgres image ───────────────────────────────────────────
FROM postgres:16

# ── Install pgvector from the PGDG repo already in the image ─────
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        postgresql-16-pgvector; \
    rm -rf /var/lib/apt/lists/*

# ── Automatically create the extension in EVERY new database ─────
# Files in /docker-entrypoint-initdb.d are executed at first boot.
COPY init/*.sql /docker-entrypoint-initdb.d/

