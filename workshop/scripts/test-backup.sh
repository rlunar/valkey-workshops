#!/bin/bash

# Test script for backup functionality
# This script validates the backup configuration without performing actual backup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_status "Testing backup script configuration..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please copy .env.example to .env and configure your database settings."
    exit 1
fi

# Load environment variables
source .env

print_status "Configuration loaded from .env:"
echo "  DB_TYPE: $DB_TYPE"
echo "  DB_HOST: $DB_HOST"
echo "  DB_PORT: $DB_PORT"
echo "  DB_NAME: $DB_NAME"
echo "  DB_USER: $DB_USER"
echo "  DB_PASSWORD: [HIDDEN]"

# Validate required environment variables
missing_vars=()
[ -z "$DB_TYPE" ] && missing_vars+=("DB_TYPE")
[ -z "$DB_HOST" ] && missing_vars+=("DB_HOST")
[ -z "$DB_PORT" ] && missing_vars+=("DB_PORT")
[ -z "$DB_NAME" ] && missing_vars+=("DB_NAME")
[ -z "$DB_USER" ] && missing_vars+=("DB_USER")
[ -z "$DB_PASSWORD" ] && missing_vars+=("DB_PASSWORD")

if [ ${#missing_vars[@]} -gt 0 ]; then
    print_error "Missing required environment variables: ${missing_vars[*]}"
    exit 1
fi

print_success "All required environment variables are set"

# Check database type
case "$DB_TYPE" in
    mysql|mariadb)
        print_success "Database type '$DB_TYPE' is supported"
        
        # Check for MySQL client tools
        if command -v mysql >/dev/null 2>&1; then
            print_success "mysql client found: $(which mysql)"
        else
            print_warning "mysql client not found. Install with: apt-get install mysql-client (Ubuntu/Debian) or brew install mysql-client (macOS)"
        fi
        
        if command -v mysqldump >/dev/null 2>&1; then
            print_success "mysqldump found: $(which mysqldump)"
        else
            print_warning "mysqldump not found. Install with: apt-get install mysql-client (Ubuntu/Debian) or brew install mysql-client (macOS)"
        fi
        ;;
    postgresql|postgres)
        print_success "Database type '$DB_TYPE' is supported"
        
        # Check for PostgreSQL client tools
        if command -v psql >/dev/null 2>&1; then
            print_success "psql client found: $(which psql)"
        else
            print_warning "psql client not found. Install with: apt-get install postgresql-client (Ubuntu/Debian) or brew install postgresql (macOS)"
        fi
        
        if command -v pg_dump >/dev/null 2>&1; then
            print_success "pg_dump found: $(which pg_dump)"
        else
            print_warning "pg_dump not found. Install with: apt-get install postgresql-client (Ubuntu/Debian) or brew install postgresql (macOS)"
        fi
        ;;
    *)
        print_error "Unsupported database type: $DB_TYPE"
        print_error "Supported types: mysql, mariadb, postgresql, postgres"
        exit 1
        ;;
esac

# Check for optional tools
if command -v gzip >/dev/null 2>&1; then
    print_success "gzip found: $(which gzip) - backup compression will be available"
else
    print_warning "gzip not found - backups will not be compressed"
fi

# Check backup directory
BACKUP_DIR="backups"
if [ -d "$BACKUP_DIR" ]; then
    print_success "Backup directory exists: $BACKUP_DIR"
    
    # Check permissions
    if [ -w "$BACKUP_DIR" ]; then
        print_success "Backup directory is writable"
    else
        print_error "Backup directory is not writable"
        exit 1
    fi
    
    # List existing backups
    backup_count=$(ls -1 "$BACKUP_DIR"/flughafendb_backup_*.sql* 2>/dev/null | wc -l)
    if [ "$backup_count" -gt 0 ]; then
        print_status "Found $backup_count existing backup(s) in $BACKUP_DIR"
    else
        print_status "No existing backups found in $BACKUP_DIR"
    fi
else
    print_status "Backup directory will be created: $BACKUP_DIR"
fi

# Test database connection (optional - only if tools are available)
case "$DB_TYPE" in
    mysql|mariadb)
        if command -v mysql >/dev/null 2>&1; then
            print_status "Testing MySQL/MariaDB connection..."
            if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" "$DB_NAME" >/dev/null 2>&1; then
                print_success "Database connection successful"
            else
                print_warning "Database connection failed. Please check your credentials and ensure the database server is running."
            fi
        fi
        ;;
    postgresql|postgres)
        if command -v psql >/dev/null 2>&1; then
            print_status "Testing PostgreSQL connection..."
            if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
                print_success "Database connection successful"
            else
                print_warning "Database connection failed. Please check your credentials and ensure the database server is running."
            fi
        fi
        ;;
esac

print_success "Backup configuration test completed!"
print_status "You can now run './scripts/backup.sh' to create a backup"
print_status "Use './scripts/restore.sh' to restore from a backup"