#!/bin/bash

# Dump flughafendb_large database from MySQL (port 3306)
# Creates a compressed backup in the data folder

set -e

DB_NAME="flughafendb_large"
MYSQL_PORT=3306
OUTPUT_DIR="data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="${OUTPUT_DIR}/${DB_NAME}_${TIMESTAMP}.sql"
COMPRESSED_FILE="${OUTPUT_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "Starting MySQL database dump..."
echo "Database: ${DB_NAME}"
echo "Port: ${MYSQL_PORT}"

# Create data directory if it doesn't exist
mkdir -p "${OUTPUT_DIR}"

# Dump the database
mysqldump \
  --host=127.0.0.1 \
  --port=${MYSQL_PORT} \
  --user=root \
  --password \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  "${DB_NAME}" > "${DUMP_FILE}"

echo "Database dumped to: ${DUMP_FILE}"

# Compress the dump file
echo "Compressing dump file..."
gzip "${DUMP_FILE}"

echo "Compressed file created: ${COMPRESSED_FILE}"
echo "Dump completed successfully!"
