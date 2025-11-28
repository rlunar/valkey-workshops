#!/bin/bash
set -e

REGISTRY_USER="${1:-rlunar}"
IMAGE_NAME="flughafendb_mariadb"
TAG="latest"

# Find latest SQL dump or create new one
LATEST_DUMP=$(ls -t data/*.sql.gz 2>/dev/null | head -1)

if [ -z "$LATEST_DUMP" ]; then
    echo "No SQL dump found. Creating new dump..."
    ./scripts/dump_mariadb.sh
    LATEST_DUMP=$(ls -t data/*.sql.gz | head -1)
fi

echo "Using dump: $LATEST_DUMP"

# Extract to temporary SQL file
TEMP_SQL="data/temp_dump.sql"
gunzip -c "$LATEST_DUMP" > "$TEMP_SQL"

# Create temporary Containerfile
cat > Containerfile.temp <<EOF
FROM docker.io/mariadb:10.11
ENV MYSQL_ROOT_PASSWORD=flughafendb_password
ENV MYSQL_DATABASE=flughafendb_large
COPY $TEMP_SQL /docker-entrypoint-initdb.d/init.sql
EOF

# Build image
echo "Building container image..."
podman build -f Containerfile.temp -t ${REGISTRY_USER}/${IMAGE_NAME}:${TAG} .

# Cleanup
rm -f Containerfile.temp "$TEMP_SQL"

echo "Image built: ${REGISTRY_USER}/${IMAGE_NAME}:${TAG}"
echo ""
echo "Run locally:"
echo "podman run -d -p 3306:3306 --name flughafendb_mariadb rlunar/flughafendb_mariadb:latest"
echo ""
echo "Check logs (wait for "ready for connections")"
echo "podman logs -f flughafendb_mariadb"
echo ""
echo "Test connection"
echo "podman exec flughafendb_mariadb mysql -u root -pflughafendb_password flughafendb_large -e 'SELECT 1;'"
echo ""
echo "Check table count periodically"
echo "podman exec flughafendb_mariadb mysql -u root -pflughafendb_password flughafendb_large -e 'SHOW TABLES;' 2>/dev/null | wc -l"
echo ""
echo "Count rows in flight table"
echo 'mysql -h 127.0.0.1 -u root -pflughafendb_password flughafendb_large -e "SELECT COUNT(*) FROM flight;"'
echo ""
echo "Stop/remove"
echo "podman stop flughafendb_mariadb"
echo "podman rm flughafendb_mariadb"
echo ""
echo "To push to Docker Hub:"
echo "  podman login docker.io"
echo "  podman push ${REGISTRY_USER}/${IMAGE_NAME}:${TAG}"
echo ""
echo "To test locally:"
echo "  podman run -d -p 3306:3306 --name flughafendb_mariadb ${REGISTRY_USER}/${IMAGE_NAME}:${TAG}"

# Watch for completion
# podman logs -f flughafendb_mariadb | grep -E "ready for connections|port: 3306"

# Use TCP connection (not socket)
mysql -h 127.0.0.1 --protocol=TCP -P 3306 -u root -pflughafendb_password flughafendb_large -e 'SELECT 1;'
mysql -h 127.0.0.1 --protocol=TCP -P 3306 -u root -pflughafendb_password flughafendb_large -e 'SELECT COUNT(*) FROM airline;'

podman stop flughafendb_mariadb
podman rm flughafendb_mariadb
podman run -d --network host -p 3306:3306 --name flughafendb_mariadb rlunar/flughafendb_mariadb:latest
mysql -h 127.0.0.1 -P 3306 -u root -pflughafendb_password flughafendb_large -e 'SELECT 1;'
