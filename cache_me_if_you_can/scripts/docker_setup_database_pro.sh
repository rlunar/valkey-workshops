#!/bin/bash
set -euo pipefail

IMAGE="${1:-${IMAGE:-rlunaws/flughafendb_mariadb:latest}}"
CONTAINER_NAME="${CONTAINER_NAME:-flughafendb_mariadb}"
HOST_PORT="${HOST_PORT:-13306}"

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is required but was not found on PATH." >&2
    exit 1
fi

docker run -d --rm --name "$CONTAINER_NAME" \
    -p "$HOST_PORT:3306" \
    -e MYSQL_ROOT_PASSWORD=flughafendb_password \
    "$IMAGE"

echo "Waiting for MariaDB to start..."
ready=0
for attempt in {1..30}; do
    if docker exec "$CONTAINER_NAME" mysqladmin ping \
        -u root -pflughafendb_password --silent 2>/dev/null; then
        ready=1
        break
    fi
    echo "Attempt $attempt/30..."
    sleep 1
done

if [ "$ready" -ne 1 ]; then
    echo "Error: MariaDB did not become ready in 30 seconds." >&2
    exit 1
fi

echo "Creating workshop database and user..."
docker exec "$CONTAINER_NAME" mariadb -u root -pflughafendb_password \
    -e "CREATE DATABASE IF NOT EXISTS flughafendb_large;"
docker exec "$CONTAINER_NAME" mariadb -u root -pflughafendb_password \
    -e "CREATE USER IF NOT EXISTS 'flughafen_user'@'%' IDENTIFIED BY 'flughafen_password';"
docker exec "$CONTAINER_NAME" mariadb -u root -pflughafendb_password \
    -e "GRANT ALL PRIVILEGES ON flughafendb_large.* TO 'flughafen_user'@'%';"
docker exec "$CONTAINER_NAME" mariadb -u root -pflughafendb_password \
    -e "GRANT PROCESS ON *.* TO 'flughafen_user'@'%';"
docker exec "$CONTAINER_NAME" mariadb -u root -pflughafendb_password \
    -e "FLUSH PRIVILEGES;"

echo "Setup complete"
echo "  Image: $IMAGE"
echo "  Host: 127.0.0.1"
echo "  Port: $HOST_PORT"
echo "  User: flughafen_user"
echo "  Password: flughafen_password"
echo "  Database: flughafendb_large"
