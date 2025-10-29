#!/bin/bash

# Database Setup Script for FlughafenDB Workshop
# Supports MySQL/MariaDB and PostgreSQL setup

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

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt-get; then
            echo "ubuntu"
        elif command_exists yum; then
            echo "centos"
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

# Function to check if MySQL/MariaDB is running
check_mysql_running() {
    if command_exists mysqladmin; then
        mysqladmin ping >/dev/null 2>&1
    else
        return 1
    fi
}

# Function to check if PostgreSQL is running
check_postgresql_running() {
    if command_exists pg_isready; then
        pg_isready >/dev/null 2>&1
    else
        return 1
    fi
}

# Function to install MySQL/MariaDB
install_mysql() {
    local os=$(detect_os)
    
    print_status "Installing MySQL/MariaDB for $os..."
    
    case $os in
        macos)
            if command_exists brew; then
                print_status "Installing MySQL via Homebrew..."
                brew install mysql
                print_status "Starting MySQL service..."
                brew services start mysql
            else
                print_error "Homebrew not found. Please install Homebrew first: https://brew.sh"
                exit 1
            fi
            ;;
        ubuntu)
            print_status "Installing MySQL via apt..."
            sudo apt-get update
            sudo apt-get install -y mysql-server mysql-client
            print_status "Starting MySQL service..."
            sudo systemctl start mysql
            sudo systemctl enable mysql
            ;;
        centos)
            print_status "Installing MariaDB via yum..."
            sudo yum install -y mariadb-server mariadb
            print_status "Starting MariaDB service..."
            sudo systemctl start mariadb
            sudo systemctl enable mariadb
            ;;
        *)
            print_error "Unsupported OS. Please install MySQL/MariaDB manually."
            exit 1
            ;;
    esac
}

# Function to install PostgreSQL
install_postgresql() {
    local os=$(detect_os)
    
    print_status "Installing PostgreSQL for $os..."
    
    case $os in
        macos)
            if command_exists brew; then
                print_status "Installing PostgreSQL via Homebrew..."
                brew install postgresql
                print_status "Starting PostgreSQL service..."
                brew services start postgresql
            else
                print_error "Homebrew not found. Please install Homebrew first: https://brew.sh"
                exit 1
            fi
            ;;
        ubuntu)
            print_status "Installing PostgreSQL via apt..."
            sudo apt-get update
            sudo apt-get install -y postgresql postgresql-contrib
            print_status "Starting PostgreSQL service..."
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        centos)
            print_status "Installing PostgreSQL via yum..."
            sudo yum install -y postgresql-server postgresql
            print_status "Initializing PostgreSQL database..."
            sudo postgresql-setup initdb
            print_status "Starting PostgreSQL service..."
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        *)
            print_error "Unsupported OS. Please install PostgreSQL manually."
            exit 1
            ;;
    esac
}

# Function to setup MySQL database and user
setup_mysql_database() {
    print_status "Setting up MySQL database and user..."
    
    # Check if we can connect as root without password
    if mysql -u root -e "SELECT 1;" >/dev/null 2>&1; then
        ROOT_PASSWORD=""
        print_success "Connected to MySQL as root (no password)"
    else
        # Try with empty password
        if mysql -u root -p"" -e "SELECT 1;" >/dev/null 2>&1; then
            ROOT_PASSWORD=""
            print_success "Connected to MySQL as root (empty password)"
        else
            # Ask for root password
            echo -n "Enter MySQL root password (or press Enter if none): "
            read -s ROOT_PASSWORD
            echo
            
            if ! mysql -u root -p"$ROOT_PASSWORD" -e "SELECT 1;" >/dev/null 2>&1; then
                print_error "Failed to connect to MySQL with provided password"
                print_status "You may need to reset the MySQL root password or run mysql_secure_installation"
                return 1
            fi
        fi
    fi
    
    # Create database and user
    mysql -u root -p"$ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS flughafendb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'flughafen_user'@'localhost' IDENTIFIED BY 'flughafen_password';
GRANT ALL PRIVILEGES ON flughafendb.* TO 'flughafen_user'@'localhost';
GRANT PROCESS ON *.* TO 'flughafen_user'@'localhost';
FLUSH PRIVILEGES;
EOF
    
    print_success "MySQL database 'flughafendb' and user 'flughafen_user' created successfully"
    
    # Update .env file
    cat > .env <<EOF
# Database Configuration
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flughafendb
DB_USER=flughafen_user
DB_PASSWORD=flughafen_password
EOF
    
    print_success ".env file updated with MySQL configuration"
}

# Function to setup PostgreSQL database and user
setup_postgresql_database() {
    print_status "Setting up PostgreSQL database and user..."
    
    # Create user and database
    sudo -u postgres psql <<EOF
CREATE USER flughafen_user WITH PASSWORD 'flughafen_password';
CREATE DATABASE flughafendb OWNER flughafen_user;
GRANT ALL PRIVILEGES ON DATABASE flughafendb TO flughafen_user;
EOF
    
    print_success "PostgreSQL database 'flughafendb' and user 'flughafen_user' created successfully"
    
    # Update .env file
    cat > .env <<EOF
# Database Configuration
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=flughafendb
DB_USER=flughafen_user
DB_PASSWORD=flughafen_password
EOF
    
    print_success ".env file updated with PostgreSQL configuration"
}

# Function to test database connection
test_database_connection() {
    source .env
    
    print_status "Testing database connection..."
    
    case "$DB_TYPE" in
        mysql|mariadb)
            if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" "$DB_NAME" >/dev/null 2>&1; then
                print_success "Database connection successful!"
                return 0
            else
                print_error "Database connection failed"
                return 1
            fi
            ;;
        postgresql|postgres)
            if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
                print_success "Database connection successful!"
                return 0
            else
                print_error "Database connection failed"
                return 1
            fi
            ;;
    esac
}

# Function to download and import FlughafenDB data
import_sample_data() {
    print_status "Checking for FlughafenDB sample data..."
    
    if [ ! -f "data/flughafendb.sql" ]; then
        print_status "Sample data not found. You can download it from:"
        print_status "https://github.com/stefanproell/flughafendb/"
        print_warning "Skipping data import. You can import manually later."
        return 0
    fi
    
    source .env
    
    print_status "Importing FlughafenDB sample data..."
    
    case "$DB_TYPE" in
        mysql|mariadb)
            if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < data/flughafendb.sql; then
                print_success "Sample data imported successfully!"
            else
                print_error "Failed to import sample data"
                return 1
            fi
            ;;
        postgresql|postgres)
            if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < data/flughafendb.sql; then
                print_success "Sample data imported successfully!"
            else
                print_error "Failed to import sample data"
                return 1
            fi
            ;;
    esac
}

# Main menu
show_menu() {
    print_header "FlughafenDB Database Setup"
    echo "1) Install and setup MySQL/MariaDB"
    echo "2) Install and setup PostgreSQL"
    echo "3) Setup database only (server already installed)"
    echo "4) Test database connection"
    echo "5) Import sample data"
    echo "6) Show current configuration"
    echo "7) Troubleshoot connection issues"
    echo "q) Quit"
    echo
    echo -n "Select an option: "
}

# Troubleshooting function
troubleshoot_connection() {
    print_header "Database Connection Troubleshooting"
    
    if [ ! -f ".env" ]; then
        print_error ".env file not found"
        return 1
    fi
    
    source .env
    
    print_status "Current configuration:"
    echo "  DB_TYPE: $DB_TYPE"
    echo "  DB_HOST: $DB_HOST"
    echo "  DB_PORT: $DB_PORT"
    echo "  DB_NAME: $DB_NAME"
    echo "  DB_USER: $DB_USER"
    echo "  DB_PASSWORD: [HIDDEN]"
    echo
    
    case "$DB_TYPE" in
        mysql|mariadb)
            print_status "Checking MySQL/MariaDB..."
            
            if command_exists mysql; then
                print_success "mysql client found"
            else
                print_error "mysql client not found. Install with:"
                echo "  macOS: brew install mysql-client"
                echo "  Ubuntu: sudo apt-get install mysql-client"
                echo "  CentOS: sudo yum install mysql"
            fi
            
            if command_exists mysqladmin; then
                if mysqladmin ping >/dev/null 2>&1; then
                    print_success "MySQL server is running"
                else
                    print_error "MySQL server is not running. Start with:"
                    echo "  macOS: brew services start mysql"
                    echo "  Ubuntu: sudo systemctl start mysql"
                    echo "  CentOS: sudo systemctl start mariadb"
                fi
            fi
            
            # Test connection with different methods
            print_status "Testing connection methods..."
            
            # Method 1: TCP connection
            if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" "$DB_NAME" >/dev/null 2>&1; then
                print_success "TCP connection works"
            else
                print_warning "TCP connection failed"
            fi
            
            # Method 2: Socket connection (if localhost)
            if [ "$DB_HOST" = "localhost" ]; then
                if mysql -u "$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" "$DB_NAME" >/dev/null 2>&1; then
                    print_success "Socket connection works"
                else
                    print_warning "Socket connection failed"
                fi
            fi
            ;;
            
        postgresql|postgres)
            print_status "Checking PostgreSQL..."
            
            if command_exists psql; then
                print_success "psql client found"
            else
                print_error "psql client not found. Install with:"
                echo "  macOS: brew install postgresql"
                echo "  Ubuntu: sudo apt-get install postgresql-client"
                echo "  CentOS: sudo yum install postgresql"
            fi
            
            if command_exists pg_isready; then
                if pg_isready >/dev/null 2>&1; then
                    print_success "PostgreSQL server is running"
                else
                    print_error "PostgreSQL server is not running. Start with:"
                    echo "  macOS: brew services start postgresql"
                    echo "  Ubuntu: sudo systemctl start postgresql"
                    echo "  CentOS: sudo systemctl start postgresql"
                fi
            fi
            
            # Test connection
            if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
                print_success "PostgreSQL connection works"
            else
                print_warning "PostgreSQL connection failed"
            fi
            ;;
    esac
}

# Main script
main() {
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1)
                print_header "Installing MySQL/MariaDB"
                if check_mysql_running; then
                    print_success "MySQL/MariaDB is already running"
                else
                    install_mysql
                fi
                setup_mysql_database
                test_database_connection
                ;;
            2)
                print_header "Installing PostgreSQL"
                if check_postgresql_running; then
                    print_success "PostgreSQL is already running"
                else
                    install_postgresql
                fi
                setup_postgresql_database
                test_database_connection
                ;;
            3)
                print_header "Database Setup"
                echo "Which database type are you using?"
                echo "1) MySQL/MariaDB"
                echo "2) PostgreSQL"
                echo -n "Select: "
                read -r db_choice
                
                case $db_choice in
                    1)
                        setup_mysql_database
                        ;;
                    2)
                        setup_postgresql_database
                        ;;
                    *)
                        print_error "Invalid choice"
                        continue
                        ;;
                esac
                test_database_connection
                ;;
            4)
                test_database_connection
                ;;
            5)
                import_sample_data
                ;;
            6)
                if [ -f ".env" ]; then
                    source .env
                    print_header "Current Configuration"
                    echo "DB_TYPE: $DB_TYPE"
                    echo "DB_HOST: $DB_HOST"
                    echo "DB_PORT: $DB_PORT"
                    echo "DB_NAME: $DB_NAME"
                    echo "DB_USER: $DB_USER"
                    echo "DB_PASSWORD: [HIDDEN]"
                else
                    print_error ".env file not found"
                fi
                ;;
            7)
                troubleshoot_connection
                ;;
            q|Q)
                print_status "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option. Please try again."
                ;;
        esac
        
        echo
        echo "Press Enter to continue..."
        read -r
        clear
    done
}

# Check if running as main script
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    clear
    main
fi