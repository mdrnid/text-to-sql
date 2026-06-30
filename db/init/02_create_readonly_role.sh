#!/bin/bash
set -euo pipefail

# Role read-only khusus LLM agent. Dijalankan otomatis saat DB pertama kali start,
# SETELAH 01_create_tables.sql. Password diambil dari environment (lihat compose).

: "${DB_READONLY_USER:?DB_READONLY_USER belum di-set}"
: "${DB_READONLY_PASSWORD:?DB_READONLY_PASSWORD belum di-set}"

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" <<-EOSQL
    -- Buat role login read-only (idempotent)
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_READONLY_USER}') THEN
            CREATE ROLE ${DB_READONLY_USER} LOGIN PASSWORD '${DB_READONLY_PASSWORD}';
        END IF;
    END
    \$\$;

    -- Izin koneksi & pakai schema
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${DB_READONLY_USER};
    GRANT USAGE ON SCHEMA public TO ${DB_READONLY_USER};

    -- SELECT untuk semua tabel yang SUDAH ada
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${DB_READONLY_USER};

    -- SELECT untuk tabel yang dibuat di MASA DEPAN (oleh POSTGRES_USER)
    ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
        GRANT SELECT ON TABLES TO ${DB_READONLY_USER};

    -- Pastikan tidak ada hak tulis yang bocor
    REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public
        FROM ${DB_READONLY_USER};
EOSQL

echo "Read-only role '${DB_READONLY_USER}' siap."