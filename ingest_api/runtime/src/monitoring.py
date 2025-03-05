"""Observability utils"""

import json
from typing import Callable

from aws_lambda_powertools import Logger, Metrics, Tracer, single_metric
from aws_lambda_powertools.metrics import MetricUnit  # noqa: F401
from src.config import settings

from fastapi import Request, Response
from fastapi.routing import APIRoute

logger: Logger = Logger(service="ingest-api", namespace="veda-backend")
metrics: Metrics = Metrics(namespace="veda-backend")
metrics.set_default_dimensions(environment=settings.stage, service="ingest-api")
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

            with single_metric(
                name="RequestCount",
                unit=MetricUnit.Count,
                value=1,
                default_dimensions=metrics.default_dimensions,
                namespace="veda-backend",
            ) as metric:
                metric.add_dimension(
                    name="route", value=f"{request.method} {self.path}"
                )

            tracer.put_annotation(key="path", value=request.url.path)
            tracer.capture_method(original_route_handler)(request)
            return await original_route_handler(request)

        return route_handler
