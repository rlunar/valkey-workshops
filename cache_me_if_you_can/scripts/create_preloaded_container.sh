#!/bin/bash
set -e

REGISTRY_USER="${1:-rlunar}"
IMAGE_NAME="flughafendb_mariadb"
TAG="latest"

echo "Creating pre-loaded MariaDB container image using Dockerfile..."

# https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/f2be885b-fc0c-4fe7-9c3a-fe2c179a73eb/data/flughafendb_large_20251127_150159.sql.gz

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Verify Dockerfile exists
if [ ! -f "$SCRIPT_DIR/Dockerfile" ]; then
    echo "Error: Dockerfile not found at $SCRIPT_DIR/Dockerfile"
    exit 1
fi

# Verify latest dump exists
DATA_DIR="$PROJECT_ROOT/data"
LATEST_DUMP=$(ls -t "$DATA_DIR"/*.sql.gz 2>/dev/null | head -1)
if [ -z "$LATEST_DUMP" ]; then
    echo "Error: No SQL dump found in $DATA_DIR. Run ./scripts/dump_mariadb.sh first"
    exit 1
fi

echo "Using dump file: $LATEST_DUMP"
echo "Building image (this will take 10-30 minutes)..."

# Get relative path from project root to dump file (macOS compatible)
DUMP_FILE_RELATIVE="${LATEST_DUMP#$PROJECT_ROOT/}"

# Build the image using Dockerfile with build arg
cd "$PROJECT_ROOT"
podman build -t ${REGISTRY_USER}/${IMAGE_NAME}:${TAG} \
    --build-arg DUMP_FILE="$DUMP_FILE_RELATIVE" \
    -f scripts/Dockerfile .

echo ""
echo "Image created: ${REGISTRY_USER}/${IMAGE_NAME}:${TAG}"
echo ""
echo "To push:"
echo "  podman login docker.io"
echo "  podman push ${REGISTRY_USER}/${IMAGE_NAME}:${TAG}"
echo ""
echo "To run:"
echo "  podman run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=flughafendb_password --name flughafendb_mariadb ${REGISTRY_USER}/${IMAGE_NAME}:${TAG}"
