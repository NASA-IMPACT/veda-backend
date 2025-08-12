#!/bin/bash
set -e

# Lint
pre-commit run --all-files

# Bring up stack for testing; ingestor not required
docker compose up -d stac raster database dynamodb pypgstac
# docker compose up -d --wait stac raster database dynamodb pypgstac

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
python -m pytest .github/workflows/tests/ -vv -s

# Run ingest unit tests
NO_PYDANTIC_SSM_SETTINGS=1 python -m pytest --cov=ingest_api/runtime/src ingest_api/runtime/tests/ -vv -s

# Transactions tests
# Temp disable transactions tests
# python -m pytest stac_api/runtime/tests/ --asyncio-mode=auto -vv -s
