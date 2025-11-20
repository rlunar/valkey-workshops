#!/bin/bash

# Import flughafendb_large database into MariaDB (port 3307)
# Expects a compressed .sql.gz file in the data folder

set -e

DB_NAME="flughafendb_large"
MARIADB_PORT=3307
DATA_DIR="data"

# Check if a specific file was provided as argument
if [ $# -eq 1 ]; then
  COMPRESSED_FILE="$1"
else
  # Find the most recent compressed dump file
  COMPRESSED_FILE=$(ls -t ${DATA_DIR}/${DB_NAME}_*.sql.gz 2>/dev/null | head -n 1)
fi

if [ -z "${COMPRESSED_FILE}" ] || [ ! -f "${COMPRESSED_FILE}" ]; then
  echo "Error: No dump file found in ${DATA_DIR}/"
  echo "Usage: $0 [path/to/dump.sql.gz]"
  exit 1
fi

echo "Starting MariaDB database import..."
echo "Database: ${DB_NAME}"
echo "Port: ${MARIADB_PORT}"
echo "Source file: ${COMPRESSED_FILE}"

# Create database if it doesn't exist
echo "Creating database if not exists..."
mysql \
  --host=127.0.0.1 \
  --port=${MARIADB_PORT} \
  --user=root \
  --password \
  -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME};"

# Import the compressed dump
echo "Importing database..."
gunzip -c "${COMPRESSED_FILE}" | mysql \
  --host=127.0.0.1 \
  --port=${MARIADB_PORT} \
  --user=root \
  --password \
  "${DB_NAME}"

echo "Import completed successfully!"
echo "Database ${DB_NAME} is now available on MariaDB port ${MARIADB_PORT}"
