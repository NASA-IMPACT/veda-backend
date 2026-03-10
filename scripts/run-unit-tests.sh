#!/bin/bash
set -e

# =================================================================
#  Run unit tests
# =================================================================
echo "--- Running core.py unit tests ---"
.venv/bin/python3.12 -m pytest stac_api/runtime/tests/test_core.py --asyncio-mode=auto -vv -s -p no:warnings
