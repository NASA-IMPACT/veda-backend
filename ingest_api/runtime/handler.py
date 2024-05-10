"""
Entrypoint for Lambda execution.
"""

from mangum import Mangum
from src.main import app
from src.monitoring import logger, metrics, tracer

handler = Mangum(app, lifespan="off", api_gateway_base_path=app.root_path)

# Add tracing
handler.__name__ = "handler"  # tracer requires __name__ to be set
handler = tracer.capture_lambda_handler(handler)
# Add logging
handler = logger.inject_lambda_context(handler, clear_state=True)
# Add metrics last to properly flush metrics.
handler = metrics.log_metrics(handler, capture_cold_start_metric=True)
