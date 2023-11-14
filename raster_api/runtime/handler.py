"""AWS Lambda handler."""

import asyncio
import logging
import os

from mangum import Mangum
from src.app import app
from src.config import ApiSettings
from src.monitoring import logger, metrics, tracer

from titiler.pgstac.db import connect_to_db

settings = ApiSettings()

logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)


@app.on_event("startup")
async def startup_event() -> None:
    """Connect to database on startup."""
    await connect_to_db(app, settings=settings.load_postgres_settings())


handler = Mangum(app, lifespan="off", api_gateway_base_path=app.root_path)

if "AWS_EXECUTION_ENV" in os.environ:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.router.startup())

# Add tracing
handler.__name__ = "handler"  # tracer requires __name__ to be set
handler = tracer.capture_lambda_handler(handler)
# Add logging
handler = logger.inject_lambda_context(handler, clear_state=True)
# Add metrics last to properly flush metrics.
handler = metrics.log_metrics(handler, capture_cold_start_metric=True)
