#!/bin/bash
set -e  # Exit on error

# Start container
docker run -d --rm --name flughafendb_mariadb \
  -p 13306:3306 \
  -e MYSQL_ROOT_PASSWORD=flughafendb_password \
  rlunar/flughafendb_mariadb:10.11-20251127

# Wait for MariaDB to be ready with retry logic
echo "Waiting for MariaDB to start..."
for i in {1..30}; do
    if docker exec flughafendb_mariadb mysqladmin ping -u root -pflughafendb_password --silent 2>/dev/null; then
        echo "✓ MariaDB is ready"
        break
    fi
    echo "Attempt $i/30..."
    sleep 1
done

# Create database
echo "Creating database..."
docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "CREATE DATABASE IF NOT EXISTS flughafendb_large;"

# Create user
echo "Creating user..."
docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "CREATE USER IF NOT EXISTS 'flughafen_user'@'%' IDENTIFIED BY 'flughafen_password';"

# Grant privileges
echo "Granting privileges..."
docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "GRANT ALL PRIVILEGES ON flughafendb_large.* TO 'flughafen_user'@'%';"

docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "GRANT PROCESS ON *.* TO 'flughafen_user'@'%';"

docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "FLUSH PRIVILEGES;"

echo "✓ Setup complete!"
echo ""
echo "Connection details:"
echo "  Host: 127.0.0.1"
echo "  Port: 13306"
echo "  User: flughafen_user"
echo "  Password: flughafen_password"
echo "  Database: flughafendb_large"