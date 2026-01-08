#!/bin/bash
set -e

# =================================================================
#  Ensure all Python dependencies are installed
# =================================================================
echo "--- Installing all development dependencies ---"
pip install -r ingest_api/runtime/requirements_dev.txt
echo "--- Dependency installation complete ---"
# =================================================================

# Lint
pre-commit run --all-files

# Bring up stack for testing; ingestor not required
# Use transactions override to enable STAC transactions for testing
docker compose -f docker-compose.yml -f docker-compose.transactions.yml up -d --wait stac raster database dynamodb pypgstac oidc

# cleanup, logging in case of failure
cleanup() {
    # Get the exit status of the last command executed before trap was called
    local exit_status=$?
    if [ $exit_status -ne 0 ]; then
        echo "Test failed, collecting logs from all containers..."
        LOG_FILE="container_logs.log"
        docker compose -f docker-compose.yml -f docker-compose.transactions.yml logs > "$LOG_FILE"
        echo "Logs collected and saved to $LOG_FILE"
    else
        echo "Tests passed, no need to collect logs."
    fi

    echo "Removing test stack..."
    docker compose -f docker-compose.yml -f docker-compose.transactions.yml down
}
trap cleanup EXIT

# Load data for tests
docker exec veda.loadtestdata /tmp/scripts/bin/load-data.sh

# Run tests
python -m pytest .github/workflows/tests/ -vv -s

# Run ingest unit tests
NO_PYDANTIC_SSM_SETTINGS=1 python -m pytest --cov=ingest_api/runtime/src ingest_api/runtime/tests/ -vv -s

# Transactions integration tests (against docker-compose environment)
# These tests use the mock OIDC server for authentication
echo "--- Running STAC Transactions integration tests ---"
python -m pytest .github/workflows/tests/test_transactions.py -vv -s

# Transactions tests
python -m pytest stac_api/runtime/tests/ --asyncio-mode=auto -vv -s