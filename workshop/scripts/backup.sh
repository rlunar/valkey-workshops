#!/bin/bash

# Enhanced backup script for FlughafenDB
# Supports MySQL, MariaDB, and PostgreSQL based on .env configuration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please copy .env.example to .env and configure your database settings."
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
if [ -z "$DB_TYPE" ] || [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    print_error "Missing required environment variables. Please check your .env file."
    print_error "Required: DB_TYPE, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
    exit 1
fi

# Create backup directory if it doesn't exist
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

# Generate timestamp for backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/flughafendb_backup_${TIMESTAMP}.sql"

print_status "Starting database backup..."
print_status "Database Type: $DB_TYPE"
print_status "Database Name: $DB_NAME"
print_status "Host: $DB_HOST:$DB_PORT"
print_status "Backup File: $BACKUP_FILE"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to test database connection
test_connection() {
    case "$DB_TYPE" in
        mysql|mariadb)
            if command_exists mysql; then
                mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" "$DB_NAME" >/dev/null 2>&1
            else
                print_error "mysql client not found. Please install MySQL client."
                return 1
            fi
            ;;
        postgresql|postgres)
            if command_exists psql; then
                PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1
            else
                print_error "psql client not found. Please install PostgreSQL client."
                return 1
            fi
            ;;
        *)
            print_error "Unsupported database type: $DB_TYPE"
            return 1
            ;;
    esac
}

# Function to perform MySQL/MariaDB backup
backup_mysql() {
    if ! command_exists mysqldump; then
        print_error "mysqldump not found. Please install MySQL client tools."
        exit 1
    fi
    
    print_status "Creating MySQL/MariaDB backup..."
    
    # Additional options for better backup
    MYSQL_OPTIONS="--single-transaction --routines --triggers --events --add-drop-table --add-locks --disable-keys --extended-insert --quick --lock-tables=false"
    
    if mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" $MYSQL_OPTIONS "$DB_NAME" > "$BACKUP_FILE"; then
        print_success "MySQL/MariaDB backup completed successfully"
    else
        print_error "MySQL/MariaDB backup failed"
        exit 1
    fi
}

# Function to perform PostgreSQL backup
backup_postgresql() {
    if ! command_exists pg_dump; then
        print_error "pg_dump not found. Please install PostgreSQL client tools."
        exit 1
    fi
    
    print_status "Creating PostgreSQL backup..."
    
    # Set password environment variable for pg_dump
    export PGPASSWORD="$DB_PASSWORD"
    
    # Additional options for better backup
    PG_OPTIONS="--verbose --clean --if-exists --create --format=plain"
    
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" $PG_OPTIONS "$DB_NAME" > "$BACKUP_FILE"; then
        print_success "PostgreSQL backup completed successfully"
    else
        print_error "PostgreSQL backup failed"
        exit 1
    fi
    
    # Clean up password environment variable
    unset PGPASSWORD
}

# Test database connection first
print_status "Testing database connection..."
if test_connection; then
    print_success "Database connection successful"
else
    print_error "Failed to connect to database. Please check your configuration."
    exit 1
fi

# Perform backup based on database type
case "$DB_TYPE" in
    mysql|mariadb)
        backup_mysql
        ;;
    postgresql|postgres)
        backup_postgresql
        ;;
    *)
        print_error "Unsupported database type: $DB_TYPE"
        print_error "Supported types: mysql, mariadb, postgresql, postgres"
        exit 1
        ;;
esac

# Check if backup file was created and has content
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    print_success "Backup completed successfully!"
    print_success "File: $BACKUP_FILE"
    print_success "Size: $BACKUP_SIZE"
    
    # Optional: Compress the backup
    if command_exists gzip; then
        print_status "Compressing backup file..."
        gzip "$BACKUP_FILE"
        COMPRESSED_FILE="${BACKUP_FILE}.gz"
        COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
        print_success "Backup compressed: $COMPRESSED_FILE ($COMPRESSED_SIZE)"
    fi
    
    # Optional: Clean up old backups (keep last 7 days)
    print_status "Cleaning up old backups (keeping last 7 days)..."
    find "$BACKUP_DIR" -name "flughafendb_backup_*.sql*" -type f -mtime +7 -delete 2>/dev/null || true
    
else
    print_error "Backup file is empty or was not created"
    exit 1
fi

print_success "Database backup process completed!"

# Display backup directory contents
print_status "Available backups:"
ls -lah "$BACKUP_DIR"/flughafendb_backup_*.sql* 2>/dev/null || print_warning "No backup files found in $BACKUP_DIR"