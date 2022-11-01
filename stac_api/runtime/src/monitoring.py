from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit  # noqa: F401
from fastapi import Request, Response
from fastapi.routing import APIRoute
from typing import Callable
from functools import wraps
 
logger: Logger = Logger(service='stac-api', namespace='veda-backend')
metrics: Metrics = Metrics(service='stac-api', namespace='veda-backend')
tracer: Tracer = Tracer()

class LoggerRouteHandler(APIRoute):
    def get_route_handler(self) -> Callable:
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
            metrics.add_metric(name='/'.join(str(request.url).split('/')[:2]), unit=MetricUnit.Count, value=1)
            tracer.put_annotation(key="path", value=request.url.path)
            tracer.capture_method(original_route_handler)(request)
            return await original_route_handler(request)
 
        return route_handler
