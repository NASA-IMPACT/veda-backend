"""Observability utils"""
from typing import Callable

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit  # noqa: F401

from fastapi import Request, Response
from fastapi.routing import APIRoute

logger: Logger = Logger(service="features-api", namespace="veda-backend")
metrics: Metrics = Metrics(service="features-api", namespace="veda-backend")
tracer: Tracer = Tracer()


class LoggerRouteHandler(APIRoute):
    """Extension of base APIRoute to add context to log statements, as well as record usage metricss"""

    def get_route_handler(self) -> Callable:
        """Overide route handler method to add logs, metrics, tracing"""
        original_route_handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            # Add fastapi context to logs
            ctx = {
                "path": request.url.path,
                "route": self.path,
                "method": request.method,
            }
            logger.append_keys(fastapi=ctx)
            logger.info("Received request")
            metrics.add_metric(
                name="/".join(
                    str(request.url.path).split("/")[:2]
                ),  # enough detail to capture search IDs, but not individual tile coords
                unit=MetricUnit.Count,
                value=1,
            )
            tracer.put_annotation(key="path", value=request.url.path)
            tracer.capture_method(original_route_handler)(request)
            return await original_route_handler(request)

        return route_handler
