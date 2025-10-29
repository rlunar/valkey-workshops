#!/bin/bash

# Enhanced restore script for FlughafenDB
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

# Function to show usage
show_usage() {
    echo "Usage: $0 [backup_file]"
    echo ""
    echo "If no backup file is specified, the script will show available backups"
    echo "and prompt you to select one."
    echo ""
    echo "Examples:"
    echo "  $0                                    # Interactive mode"
    echo "  $0 backups/flughafendb_backup_20231028_143022.sql"
    echo "  $0 backups/flughafendb_backup_20231028_143022.sql.gz"
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to list available backups
list_backups() {
    BACKUP_DIR="backups"
    if [ ! -d "$BACKUP_DIR" ]; then
        print_error "Backup directory '$BACKUP_DIR' not found."
        return 1
    fi
    
    print_status "Available backup files:"
    local backup_files=($(ls -t "$BACKUP_DIR"/flughafendb_backup_*.sql* 2>/dev/null))
    
    if [ ${#backup_files[@]} -eq 0 ]; then
        print_warning "No backup files found in $BACKUP_DIR"
        return 1
    fi
    
    for i in "${!backup_files[@]}"; do
        local file="${backup_files[$i]}"
        local size=$(du -h "$file" | cut -f1)
        local date=$(stat -c %y "$file" 2>/dev/null || stat -f %Sm "$file" 2>/dev/null || echo "Unknown")
        printf "%2d) %s (%s) - %s\n" $((i+1)) "$(basename "$file")" "$size" "$date"
    done
    
    echo ""
    echo -n "Select backup file (1-${#backup_files[@]}) or 'q' to quit: "
    read -r selection
    
    if [ "$selection" = "q" ] || [ "$selection" = "Q" ]; then
        print_status "Restore cancelled."
        exit 0
    fi
    
    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le ${#backup_files[@]} ]; then
        BACKUP_FILE="${backup_files[$((selection-1))]}"
        print_status "Selected: $(basename "$BACKUP_FILE")"
    else
        print_error "Invalid selection."
        exit 1
    fi
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

# Function to restore MySQL/MariaDB backup
restore_mysql() {
    if ! command_exists mysql; then
        print_error "mysql client not found. Please install MySQL client tools."
        exit 1
    fi
    
    print_status "Restoring MySQL/MariaDB backup..."
    
    # Determine if file is compressed
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        if command_exists gunzip; then
            print_status "Decompressing backup file..."
            if gunzip -c "$BACKUP_FILE" | mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME"; then
                print_success "MySQL/MariaDB restore completed successfully"
            else
                print_error "MySQL/MariaDB restore failed"
                exit 1
            fi
        else
            print_error "gunzip not found. Cannot decompress backup file."
            exit 1
        fi
    else
        if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$BACKUP_FILE"; then
            print_success "MySQL/MariaDB restore completed successfully"
        else
            print_error "MySQL/MariaDB restore failed"
            exit 1
        fi
    fi
}

# Function to restore PostgreSQL backup
restore_postgresql() {
    if ! command_exists psql; then
        print_error "psql client not found. Please install PostgreSQL client tools."
        exit 1
    fi
    
    print_status "Restoring PostgreSQL backup..."
    
    # Set password environment variable
    export PGPASSWORD="$DB_PASSWORD"
    
    # Determine if file is compressed
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        if command_exists gunzip; then
            print_status "Decompressing backup file..."
            if gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"; then
                print_success "PostgreSQL restore completed successfully"
            else
                print_error "PostgreSQL restore failed"
                exit 1
            fi
        else
            print_error "gunzip not found. Cannot decompress backup file."
            exit 1
        fi
    else
        if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"; then
            print_success "PostgreSQL restore completed successfully"
        else
            print_error "PostgreSQL restore failed"
            exit 1
        fi
    fi
    
    # Clean up password environment variable
    unset PGPASSWORD
}

# Main script logic
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
    exit 0
fi

# Determine backup file
if [ -z "$1" ]; then
    # Interactive mode - list available backups
    list_backups
else
    # Use provided backup file
    BACKUP_FILE="$1"
    if [ ! -f "$BACKUP_FILE" ]; then
        print_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
fi

print_status "Starting database restore..."
print_status "Database Type: $DB_TYPE"
print_status "Database Name: $DB_NAME"
print_status "Host: $DB_HOST:$DB_PORT"
print_status "Backup File: $BACKUP_FILE"

# Confirm restore operation
print_warning "This will restore the database '$DB_NAME' from backup."
print_warning "All existing data will be replaced!"
echo -n "Are you sure you want to continue? (yes/no): "
read -r confirmation

if [ "$confirmation" != "yes" ]; then
    print_status "Restore cancelled."
    exit 0
fi

# Test database connection
print_status "Testing database connection..."
if test_connection; then
    print_success "Database connection successful"
else
    print_error "Failed to connect to database. Please check your configuration."
    exit 1
fi

# Perform restore based on database type
case "$DB_TYPE" in
    mysql|mariadb)
        restore_mysql
        ;;
    postgresql|postgres)
        restore_postgresql
        ;;
    *)
        print_error "Unsupported database type: $DB_TYPE"
        print_error "Supported types: mysql, mariadb, postgresql, postgres"
        exit 1
        ;;
esac

print_success "Database restore process completed!"