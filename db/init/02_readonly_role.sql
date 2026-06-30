-- Role read-only khusus LLM agent. Tidak pernah punya hak tulis.
-- Init script jalan urut abjad, jadi file ini jalan SETELAH 01_create_tables.sql.

CREATE ROLE llm_readonly WITH LOGIN PASSWORD 'change_me_readonly';

GRANT CONNECT ON DATABASE olist TO llm_readonly;
GRANT USAGE  ON SCHEMA public  TO llm_readonly;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO llm_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO llm_readonly;

ALTER ROLE llm_readonly SET default_transaction_read_only = on;
ALTER ROLE llm_readonly SET statement_timeout = '15s';