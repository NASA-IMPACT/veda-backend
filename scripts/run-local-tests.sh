#!/bin/bash
set -e

# =================================================================
#  Ensure all Python dependencies are installed
# =================================================================
echo "--- Installing all development dependencies ---"
uv sync --extra dev --extra deploy --extra test
uv sync --project ingest_api/runtime --group test
uv sync --project stac_api/runtime --group test
echo "--- Dependency installation complete ---"
# =================================================================

# Lint
uv run pre-commit run --all-files

# Bring up stack for testing; ingestor not required
docker compose up -d --wait stac raster database dynamodb pypgstac

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

# Load data for tests
docker exec veda.loadtestdata /tmp/scripts/bin/load-data.sh

# Run tests
echo "--- Running stac and raster tests ---"
uv run pytest .github/workflows/tests/ -vv -s

# Run ingest unit tests
echo "--- Running ingest api runtime tests ---"
NO_PYDANTIC_SSM_SETTINGS=1 uv run --project ingest_api/runtime python -m pytest --cov=ingest_api/runtime/src ingest_api/runtime/tests/ -vv -s

# Transactions tests
echo "--- Running stac api runtime tests ---"
uv run --project stac_api/runtime pytest stac_api/runtime/tests/ --asyncio-mode=auto -vv -s -p no:warnings
