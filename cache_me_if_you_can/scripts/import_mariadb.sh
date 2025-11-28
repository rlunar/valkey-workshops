#!/bin/bash

# Import flughafendb_large database into MariaDB (port 3307)
# Expects a compressed .sql.gz file in the data folder

set -e

DB_NAME="flughafendb_large"
MARIADB_PORT=3308
DATA_DIR="data"

# Check if a specific file was provided as argument
if [ $# -eq 1 ]; then
  LATEST_DUMP="$1"
else
  # Find latest SQL dump or create new one
  LATEST_DUMP=$(ls -t data/*.sql.gz 2>/dev/null | head -1)

  if [ -z "$LATEST_DUMP" ]; then
      echo "No SQL dump found. Creating new dump..."
      ./scripts/dump_mariadb.sh
      LATEST_DUMP=$(ls -t data/*.sql.gz | head -1)
  fi
fi

echo "Starting MariaDB database import..."
echo "Database: ${DB_NAME}"
echo "Port: ${MARIADB_PORT}"
echo "Source file: ${LATEST_DUMP}"

# Create database if it doesn't exist
echo "Creating database if not exists..."
mariadb \
  --host=127.0.0.1 \
  --port=${MARIADB_PORT} \
  --user=root \
  --password \
  -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME};"

# Extract SQL file
echo "Extracting SQL file..."
SQL_FILE="${DATA_DIR}/temp_import.sql"
gunzip -c "${LATEST_DUMP}" > "${SQL_FILE}"

# Import in background with progress monitoring
echo "Importing database in background..."
LOG_FILE="${DATA_DIR}/import.log"
PID_FILE="${DATA_DIR}/import.pid"

(
  mariadb \
    --host=127.0.0.1 \
    --port=${MARIADB_PORT} \
    --user=root \
    --password \
    "${DB_NAME}" < "${SQL_FILE}" > "${LOG_FILE}" 2>&1
  
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date)] Import completed successfully" >> "${LOG_FILE}"
    rm -f "${SQL_FILE}" "${PID_FILE}"
  else
    echo "[$(date)] Import failed with exit code $EXIT_CODE" >> "${LOG_FILE}"
  fi
) &

IMPORT_PID=$!
echo $IMPORT_PID > "${PID_FILE}"

echo "Import started with PID: ${IMPORT_PID}"
echo "Monitor: tail -f ${LOG_FILE}"
echo "Status: ps -p ${IMPORT_PID} || echo 'Import complete'"
