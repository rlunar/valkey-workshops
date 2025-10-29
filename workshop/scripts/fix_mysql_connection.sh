#!/bin/bash

# Quick fix script for MySQL connection issues

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

print_status "MySQL Connection Troubleshooting"
echo "=================================="

# Check if MySQL is installed
if command -v mysql >/dev/null 2>&1; then
    print_success "MySQL client is installed"
else
    print_error "MySQL client not found"
    print_status "Install MySQL client:"
    echo "  macOS: brew install mysql"
    echo "  Ubuntu: sudo apt-get install mysql-client"
    exit 1
fi

# Check if MySQL server is running
print_status "Checking if MySQL server is running..."

# Try different methods to check MySQL status
if command -v mysqladmin >/dev/null 2>&1; then
    if mysqladmin ping >/dev/null 2>&1; then
        print_success "MySQL server is running (no password)"
    elif mysqladmin -u root ping >/dev/null 2>&1; then
        print_success "MySQL server is running (root user)"
    else
        print_warning "MySQL server may not be running or requires password"
    fi
else
    print_warning "mysqladmin not found, cannot check server status"
fi

# Check for common MySQL socket locations
print_status "Checking MySQL socket locations..."
SOCKET_LOCATIONS=(
    "/tmp/mysql.sock"
    "/var/run/mysqld/mysqld.sock"
    "/var/lib/mysql/mysql.sock"
    "/usr/local/var/mysql/mysql.sock"
)

for socket in "${SOCKET_LOCATIONS[@]}"; do
    if [ -S "$socket" ]; then
        print_success "Found MySQL socket: $socket"
        MYSQL_SOCKET="$socket"
        break
    fi
done

if [ -z "$MYSQL_SOCKET" ]; then
    print_warning "No MySQL socket found in common locations"
fi

# Try to start MySQL service
print_status "Attempting to start MySQL service..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew >/dev/null 2>&1; then
        print_status "Starting MySQL via Homebrew..."
        brew services start mysql || print_warning "Failed to start MySQL via brew"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v systemctl >/dev/null 2>&1; then
        print_status "Starting MySQL via systemctl..."
        sudo systemctl start mysql || sudo systemctl start mariadb || print_warning "Failed to start MySQL via systemctl"
    fi
fi

# Wait a moment for service to start
sleep 2

# Test different connection methods
print_status "Testing connection methods..."

# Method 1: Connect as root with no password
if mysql -u root -e "SELECT 1;" >/dev/null 2>&1; then
    print_success "✓ Can connect as root (no password)"
    ROOT_ACCESS=true
elif mysql -u root -p"" -e "SELECT 1;" >/dev/null 2>&1; then
    print_success "✓ Can connect as root (empty password)"
    ROOT_ACCESS=true
else
    print_warning "✗ Cannot connect as root without password"
    ROOT_ACCESS=false
fi

# Method 2: Try with socket if found
if [ -n "$MYSQL_SOCKET" ]; then
    if mysql -u root -S "$MYSQL_SOCKET" -e "SELECT 1;" >/dev/null 2>&1; then
        print_success "✓ Can connect via socket: $MYSQL_SOCKET"
    else
        print_warning "✗ Cannot connect via socket: $MYSQL_SOCKET"
    fi
fi

# Method 3: Try TCP connection
if mysql -h 127.0.0.1 -P 3306 -u root -e "SELECT 1;" >/dev/null 2>&1; then
    print_success "✓ Can connect via TCP (127.0.0.1:3306)"
elif mysql -h localhost -P 3306 -u root -e "SELECT 1;" >/dev/null 2>&1; then
    print_success "✓ Can connect via TCP (localhost:3306)"
else
    print_warning "✗ Cannot connect via TCP"
fi

# If we have root access, set up the workshop database
if [ "$ROOT_ACCESS" = true ]; then
    print_status "Setting up workshop database and user..."
    
    mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS flughafendb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'flughafen_user'@'localhost' IDENTIFIED BY 'flughafen_password';
GRANT ALL PRIVILEGES ON flughafendb.* TO 'flughafen_user'@'localhost';
FLUSH PRIVILEGES;
EOF
    
    print_success "Database and user created successfully!"
    
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
    
    print_success ".env file updated"
    
    # Test the new connection
    if mysql -u flughafen_user -pflughafen_password flughafendb -e "SELECT 1;" >/dev/null 2>&1; then
        print_success "✓ Workshop database connection works!"
        print_status "You can now connect with:"
        echo "  mysql -u flughafen_user -pflughafen_password flughafendb"
    else
        print_error "✗ Workshop database connection failed"
    fi
else
    print_error "Cannot set up workshop database without root access"
    print_status "Manual setup required:"
    echo "1. Connect to MySQL as root:"
    echo "   mysql -u root -p"
    echo "2. Run these commands:"
    echo "   CREATE DATABASE flughafendb;"
    echo "   CREATE USER 'flughafen_user'@'localhost' IDENTIFIED BY 'flughafen_password';"
    echo "   GRANT ALL PRIVILEGES ON flughafendb.* TO 'flughafen_user'@'localhost';"
    echo "   FLUSH PRIVILEGES;"
fi

print_status "Troubleshooting complete!"