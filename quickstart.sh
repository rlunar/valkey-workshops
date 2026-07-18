#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSHOP_DIR="${SCRIPT_DIR}/cache_me_if_you_can"
ENV_FILE="${WORKSHOP_DIR}/.env"
ENV_EXAMPLE="${WORKSHOP_DIR}/.env.example"

VALKEY_IMAGE="valkey/valkey:9-alpine"
VALKEY_CONTAINER="valkey-server"
VALKEY_PORT="6380"
BUNDLE_IMAGE="valkey/valkey-bundle:9-alpine"
BUNDLE_CONTAINER="valkey-bundle"
BUNDLE_PORT="16379"
OLLAMA_MODEL="codellama"
MINIMUM_PYTHON="3.13"

DRY_RUN=false
PYTHON_BIN=""

usage() {
    cat <<'EOF'
Usage: ./quickstart.sh [--dry-run] [--help]

Prepare the Cache Me If You Can workshop:
  - verify Docker, Ollama, Python 3.13+, and uv
  - start local Valkey and valkey-bundle containers
  - start Ollama when needed and pull the codellama model
  - create or reconcile cache_me_if_you_can/.env
  - install locked Python dependencies with uv

Options:
  --dry-run  Check prerequisites and show pending changes without applying them.
  --help     Show this help message.

The script does not install missing system software or manage the workshop's
relational database. Existing containers with conflicting names or settings are
left untouched.
EOF
}

log() {
    printf '[quickstart] %s\n' "$*"
}

warn() {
    printf '[quickstart] WARNING: %s\n' "$*" >&2
}

fail() {
    printf '[quickstart] ERROR: %s\n' "$*" >&2
    exit 1
}

print_command() {
    printf '[quickstart] Would run:'
    printf ' %q' "$@"
    printf '\n'
}

run_command() {
    if [[ "${DRY_RUN}" == "true" ]]; then
        print_command "$@"
    else
        "$@"
    fi
}

require_command() {
    local command_name="$1"
    local install_hint="$2"

    if ! command -v "${command_name}" >/dev/null 2>&1; then
        fail "${command_name} is required. ${install_hint}"
    fi
}

find_compatible_python() {
    local candidate
    local discovered=""

    for candidate in python3.13 python3 python; do
        if ! command -v "${candidate}" >/dev/null 2>&1; then
            continue
        fi

        discovered="${discovered} ${candidate}=$(${candidate} --version 2>&1)"
        if "${candidate}" -c 'import sys; raise SystemExit(sys.version_info < (3, 13))'; then
            PYTHON_BIN="$(command -v "${candidate}")"
            return
        fi
    done

    fail "Python ${MINIMUM_PYTHON} or later is required. Found:${discovered:- none}."
}

check_prerequisites() {
    log "Checking prerequisites"

    require_command docker "Install Docker Desktop or Docker Engine: https://docs.docker.com/get-docker/"
    if ! docker info >/dev/null 2>&1; then
        fail "Docker is installed, but its daemon is unavailable. Start Docker and run this script again."
    fi
    log "Docker is ready: $(docker --version)"

    require_command ollama "Install Ollama: https://ollama.com/download"
    log "Ollama is installed: $(ollama --version 2>&1 | head -n 1)"

    find_compatible_python
    log "Python is ready: $("${PYTHON_BIN}" --version 2>&1)"

    require_command uv "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
    log "uv is ready: $(uv --version)"

    [[ -d "${WORKSHOP_DIR}" ]] || fail "Workshop directory not found: ${WORKSHOP_DIR}"
    [[ -f "${ENV_EXAMPLE}" ]] || fail "Environment template not found: ${ENV_EXAMPLE}"
    [[ -f "${WORKSHOP_DIR}/uv.lock" ]] || fail "Dependency lock file not found: ${WORKSHOP_DIR}/uv.lock"
}

container_exists() {
    docker container inspect "$1" >/dev/null 2>&1
}

container_is_running() {
    [[ "$(docker inspect --format '{{.State.Running}}' "$1" 2>/dev/null)" == "true" ]]
}

validate_container() {
    local name="$1"
    local expected_image="$2"
    local expected_port="$3"
    local actual_image
    local port_bindings

    actual_image="$(docker inspect --format '{{.Config.Image}}' "${name}")"
    if [[ "${actual_image}" != "${expected_image}" ]]; then
        fail "Container ${name} uses ${actual_image}, expected ${expected_image}. Remove or rename it manually before retrying."
    fi

    port_bindings="$(docker port "${name}" 6379/tcp 2>/dev/null || true)"
    if ! printf '%s\n' "${port_bindings}" | grep -Eq ":${expected_port}$"; then
        fail "Container ${name} is not publishing port 6379 on host port ${expected_port}. Remove or rename it manually before retrying."
    fi
}

wait_for_valkey() {
    local name="$1"
    local attempt=0

    while [[ ${attempt} -lt 30 ]]; do
        if docker exec "${name}" valkey-cli ping 2>/dev/null | grep -q '^PONG$'; then
            log "${name} is responding to PING"
            return
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    fail "${name} did not become ready within 30 seconds. Check: docker logs ${name}"
}

ensure_container() {
    local name="$1"
    local image="$2"
    local host_port="$3"
    local created=false

    if container_exists "${name}"; then
        validate_container "${name}" "${image}" "${host_port}"
        if container_is_running "${name}"; then
            log "Container ${name} is already running"
        else
            log "Starting existing container ${name}"
            run_command docker start "${name}"
        fi
    else
        if ! docker image inspect "${image}" >/dev/null 2>&1; then
            log "Pulling ${image}"
            run_command docker pull "${image}"
        else
            log "Docker image is already available: ${image}"
        fi

        log "Creating container ${name} on 127.0.0.1:${host_port}"
        run_command docker run -d --rm \
            --name "${name}" \
            -p "127.0.0.1:${host_port}:6379" \
            "${image}"
        created=true
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
        if [[ "${created}" == "true" ]]; then
            log "Would wait for ${name} to respond to PING"
        fi
        return
    fi

    wait_for_valkey "${name}"
}

ollama_is_ready() {
    ollama list >/dev/null 2>&1
}

start_ollama() {
    local log_file="${TMPDIR:-/tmp}/valkey-workshop-ollama.log"

    if ollama_is_ready; then
        log "Ollama service is already running"
        return
    fi

    log "Ollama is installed but not responding; starting it"
    if [[ "${DRY_RUN}" == "true" ]]; then
        if [[ "$(uname -s)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
            print_command open -a Ollama
        else
            log "Would start 'ollama serve' in the background; log: ${log_file}"
        fi
        return
    fi

    if [[ "$(uname -s)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
        open -a Ollama
    else
        nohup ollama serve >"${log_file}" 2>&1 &
    fi

    local attempt=0
    while [[ ${attempt} -lt 30 ]]; do
        if ollama_is_ready; then
            log "Ollama service is ready"
            return
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    fail "Ollama did not become ready within 30 seconds. Check ${log_file} or start Ollama manually."
}

ensure_ollama_model() {
    if ollama_is_ready && ollama show "${OLLAMA_MODEL}" >/dev/null 2>&1; then
        log "Ollama model is already available: ${OLLAMA_MODEL}"
        return
    fi

    log "Pulling Ollama model: ${OLLAMA_MODEL}"
    if [[ "${DRY_RUN}" == "true" ]]; then
        print_command ollama pull "${OLLAMA_MODEL}"
    else
        ollama pull "${OLLAMA_MODEL}"
    fi
}

reconcile_environment() {
    local source_file="${ENV_FILE}"
    local mode="write"
    local settings=(
        "CACHE_ENGINE=valkey"
        "CACHE_HOST=localhost"
        "CACHE_PORT=${VALKEY_PORT}"
        "CACHE_TLS=false"
        "VECTOR_ENGINE=valkey"
        "VECTOR_HOST=localhost"
        "VECTOR_PORT=${BUNDLE_PORT}"
        "OLLAMA_MODEL=${OLLAMA_MODEL}"
        "OLLAMA_URL=http://localhost:11434/api/generate"
        "KNOWLEDGE_BASE_PATH=knowledge_base"
    )

    if [[ ! -f "${ENV_FILE}" ]]; then
        if [[ "${DRY_RUN}" == "true" ]]; then
            log "Would create ${ENV_FILE} from ${ENV_EXAMPLE}"
            source_file="${ENV_EXAMPLE}"
        else
            log "Creating ${ENV_FILE} from ${ENV_EXAMPLE}"
            cp "${ENV_EXAMPLE}" "${ENV_FILE}"
            chmod 600 "${ENV_FILE}"
        fi
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
        mode="dry-run"
    fi

    "${PYTHON_BIN}" - "${mode}" "${source_file}" "${ENV_FILE}" "${settings[@]}" <<'PY'
import os
import re
import stat
import sys
from pathlib import Path

mode, source_name, target_name, *raw_settings = sys.argv[1:]
source = Path(source_name)
target = Path(target_name)
settings = dict(item.split("=", 1) for item in raw_settings)
lines = source.read_text().splitlines()
changes = []

for key, desired_value in settings.items():
    pattern = re.compile(rf"^(\s*(?:export\s+)?){re.escape(key)}\s*=.*$")
    matches = [index for index, line in enumerate(lines) if pattern.match(line)]
    desired_line = f"{key}={desired_value}"

    if matches:
        for index in matches:
            current_line = lines[index]
            if current_line != desired_line:
                lines[index] = desired_line
                changes.append(key)
    else:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(desired_line)
        changes.append(key)

if not changes:
    print("[quickstart] Environment is already configured")
    raise SystemExit(0)

unique_changes = list(dict.fromkeys(changes))
if mode == "dry-run":
    print(f"[quickstart] Would update environment keys: {', '.join(unique_changes)}")
    raise SystemExit(0)

content = "\n".join(lines) + "\n"
temporary = target.with_name(f".{target.name}.quickstart.tmp")
temporary.write_text(content)
if target.exists():
    os.chmod(temporary, stat.S_IMODE(target.stat().st_mode))
else:
    os.chmod(temporary, 0o600)
os.replace(temporary, target)
print(f"[quickstart] Updated environment keys: {', '.join(unique_changes)}")
PY
}

sync_dependencies() {
    log "Synchronizing locked Python dependencies"
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "Would run in ${WORKSHOP_DIR}: uv sync --frozen"
    else
        (
            cd "${WORKSHOP_DIR}"
            uv sync --frozen
        )
    fi
}

show_summary() {
    printf '\n'
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "Dry run complete; no changes were made"
        return
    fi

    log "Workshop setup complete"
    log "Valkey:        redis://localhost:${VALKEY_PORT} (${VALKEY_CONTAINER})"
    log "Valkey bundle: redis://localhost:${BUNDLE_PORT} (${BUNDLE_CONTAINER})"
    log "Ollama:       http://localhost:11434 (${OLLAMA_MODEL})"
    log "Environment:  ${ENV_FILE}"
    printf '\nNext step:\n  cd %q\n  uv run streamlit run airport_app.py\n' "${WORKSHOP_DIR}"
}

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                ;;
            --help|-h)
                usage
                return
                ;;
            *)
                usage >&2
                fail "Unknown option: $1"
                ;;
        esac
        shift
    done

    check_prerequisites
    ensure_container "${VALKEY_CONTAINER}" "${VALKEY_IMAGE}" "${VALKEY_PORT}"
    ensure_container "${BUNDLE_CONTAINER}" "${BUNDLE_IMAGE}" "${BUNDLE_PORT}"
    start_ollama
    ensure_ollama_model
    reconcile_environment
    sync_dependencies
    show_summary
}

main "$@"
