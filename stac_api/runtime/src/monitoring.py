"""Observability utils"""
import json
from typing import Callable

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit  # noqa: F401
from src.config import ApiSettings

from fastapi import Request, Response
from fastapi.routing import APIRoute

settings = ApiSettings()

logger: Logger = Logger(service="stac-api", namespace="veda-backend")
metrics: Metrics = Metrics(service="stac-api", namespace="veda-backend")
metrics.set_default_dimensions(environment=settings.stage)
tracer: Tracer = Tracer()


class LoggerRouteHandler(APIRoute):
    """Extension of base APIRoute to add context to log statements, as well as record usage metrics"""

    def get_route_handler(self) -> Callable:
        """Overide route handler method to add logs, metrics, tracing"""
        original_route_handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            # Add fastapi context to logs
            body = await request.body()
            try:
                body_json = json.loads(body)
            except json.decoder.JSONDecodeError:
                body_json = None

            ctx = {
                "path": request.url.path,
                "path_params": request.path_params,
                "body": body_json,
                "route": self.path,
                "method": request.method,
            }
            logger.append_keys(fastapi=ctx)
            logger.info("Received request")

            metrics.add_metric(
                name=self.path,
                unit=MetricUnit.Count,
                value=1,
            )
            tracer.put_annotation(key="path", value=request.url.path)
            tracer.capture_method(original_route_handler)(request)
            return await original_route_handler(request)

        return route_handler
