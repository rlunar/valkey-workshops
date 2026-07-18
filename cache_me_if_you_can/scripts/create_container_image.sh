#!/bin/bash
# Compatibility entry point. New workflows should call
# create_preloaded_container.sh directly.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Warning: create_container_image.sh is deprecated; delegating to create_preloaded_container.sh." >&2
exec "$SCRIPT_DIR/create_preloaded_container.sh" "$@"
