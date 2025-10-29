#!/bin/bash
source .env

# Create backup directory if it doesn't exist
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

# Generate timestamp for backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/flughafendb_backup_${TIMESTAMP}.sql"

echo "Starting database backup..."
echo "Database Type: $DB_TYPE"
echo "Database Name: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup File: $BACKUP_FILE"

mysqldump -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD --no-tablespaces $DB_NAME > $BACKUP_FILE

gzip "$BACKUP_FILE"
COMPRESSED_FILE="${BACKUP_FILE}.gz"
COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
