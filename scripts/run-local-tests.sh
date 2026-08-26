#!/bin/bash
set -e

# =================================================================
#  Ensure all Python dependencies are installed
# =================================================================
echo "--- Installing all development dependencies ---"
uv sync --all-groups
uv sync --project ingest_api/runtime --group test
uv sync --project stac_api/runtime --group test
echo "--- Dependency installation complete ---"
# =================================================================

# Lint
uv run pre-commit run --all-files

# Bring up infra first
docker compose up -d --wait database dynamodb oidc

# Load fixtures once via the pypgstac service and block until completion
echo "--- Loading pgstac fixture data ---"
docker compose up -d pypgstac
load_exit_code="$(docker wait veda.loadtestdata)"
if [ "$load_exit_code" -ne 0 ]; then
    echo "pypgstac seed load failed with exit code $load_exit_code"
    docker logs veda.loadtestdata
    exit 1
fi

# Bring up APIs after data load to avoid startup-time race conditions
docker compose up -d --wait stac raster

# cleanup, logging in case of failure
cleanup() {
    # Get the exit status of the last command executed before trap was called
    local exit_status=$?
    if [ $exit_status -ne 0 ]; then
        echo "Test failed, collecting logs from all containers..."
        LOG_FILE="container_logs.log"
        docker compose logs > "$LOG_FILE"
        echo "Logs collected and saved to $LOG_FILE"
    else
        echo "Tests passed, no need to collect logs."
    fi

    echo "Removing test stack..."
    docker compose down
}
trap cleanup EXIT

# Run tests
echo "--- Running stac and raster tests ---"
uv run pytest .github/workflows/tests/ -vv -s

# Run ingest unit tests
echo "--- Running ingest api runtime tests ---"
# Must ping PGSTAC_VERSION in multiple places due to version management outside of repository
PGSTAC_VERSION=0.9.6
NO_PYDANTIC_SSM_SETTINGS=1 uv run --project ingest_api/runtime \
    --with common/auth \
    --with "pypgstac==${PGSTAC_VERSION}" \
    pytest --cov=ingest_api/runtime/src ingest_api/runtime/tests/ -vv -s

# Transactions tests
echo "--- Running stac api runtime tests ---"
uv run --project stac_api/runtime \
    --with common/auth \
    pytest stac_api/runtime/tests/ --asyncio-mode=auto -vv -s -p no:warnings

echo "--- Running auth tests ---"
uv run --with common/auth pytest common/auth/tests/ -vv -s
