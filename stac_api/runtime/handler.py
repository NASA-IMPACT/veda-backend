"""AWS Lambda handler."""

import logging

from mangum import Mangum
from src.app import app
from src.config import ApiSettings
from src.monitoring import logger, metrics, tracer

settings = ApiSettings()
print("REBUILD ME")
logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)

handler = Mangum(app, lifespan="auto", api_gateway_base_path=f"/{settings.root_path}")

# Add tracing
handler.__name__ = "handler"  # tracer requires __name__ to be set
handler = tracer.capture_lambda_handler(handler)
# Add logging
handler = logger.inject_lambda_context(handler, clear_state=True)
# Add metrics last to properly flush metrics.
handler = metrics.log_metrics(handler, capture_cold_start_metric=True)
