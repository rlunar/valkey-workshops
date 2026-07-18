#!/bin/bash
# Compatibility shortcut for the canonical database setup workflow.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HOST_PORT="${HOST_PORT:-23306}"
exec "$SCRIPT_DIR/docker_setup_database_pro.sh" "$@"
