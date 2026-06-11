#!/usr/bin/env bash
# scripts/setup_postgres.sh
# Inicializa el rol y las bases de datos del proyecto en PostgreSQL.
#
# Uso (desde la raíz del proyecto):
#   chmod +x scripts/setup_postgres.sh
#   ./scripts/setup_postgres.sh
#
# Requiere PostgreSQL instalado y el servicio corriendo.
# En Ubuntu/Debian:  sudo apt install postgresql postgresql-contrib
# En Windows: usar el instalador oficial y correr los comandos psql manualmente.

set -euo pipefail

DB_USER="${DOCTORADO_DB_USER:-doctorado}"
DB_PASS="${DOCTORADO_DB_PASS:-doctorado_dev_2025}"
DB_DEV="${DOCTORADO_DB_DEV:-doctorado_dev}"
DB_TEST="${DOCTORADO_DB_TEST:-doctorado_test}"

echo ">> Creando rol '${DB_USER}' (si no existe)..."
sudo -u postgres psql <<SQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
      CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';
   END IF;
END
\$\$;
SQL

echo ">> Creando base de desarrollo '${DB_DEV}' (si no existe)..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_DEV}'" | grep -q 1 || \
  sudo -u postgres createdb -O "${DB_USER}" "${DB_DEV}"

echo ">> Creando base de pruebas '${DB_TEST}' (si no existe)..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_TEST}'" | grep -q 1 || \
  sudo -u postgres createdb -O "${DB_USER}" "${DB_TEST}"

echo ">> Otorgando privilegios..."
sudo -u postgres psql -d "${DB_DEV}"  -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"
sudo -u postgres psql -d "${DB_TEST}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"

echo ""
echo "Listo. Agrega esto a tu .env:"
echo "DATABASE_URL=postgresql+psycopg2://${DB_USER}:${DB_PASS}@localhost:5432/${DB_DEV}"
