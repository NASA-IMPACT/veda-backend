"""Observability middleware for logging and tracing requests."""
import json
import time
from typing import Callable, Optional

from aws_lambda_powertools import Logger, Metrics, Tracer, single_metric
from aws_lambda_powertools.metrics import MetricUnit
from src.config import ApiSettings

settings = ApiSettings()

logger: Logger = Logger(service="stac-api", namespace="veda-backend")
metrics: Metrics = Metrics(namespace="veda-backend")
metrics.set_default_dimensions(environment=settings.stage, service="stac-api")
tracer: Tracer = Tracer()


class ObservabilityMiddleware:
    """Observability middleware for logging and tracing requests."""

    def __init__(self, app: Callable):
        """Observability middleware for logging and tracing requests."""
        self.app = app

    async def __call__(self, scope, receive, send):  # noqa: C901
        """Observability middleware for logging and tracing requests."""
        # Only handle HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "GET")
        raw_path: str = scope.get("path", "")

        # --- Buffer the incoming body so we can log it but still pass it downstream ---
        body = b""
        more_body = True

        # Consume the body from the original receive channel
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                # Pass through non-http.request messages
                await self.app(scope, _make_receive_replay([message]), send)
                return
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        # Prepare a receive wrapper that replays the buffered body to the app
        receive_replayed = _make_receive_replay(
            [{"type": "http.request", "body": body, "more_body": False}]
        )

        # Try to parse JSON body for structured logging (non-JSON becomes None)
        body_json = None
        if body:
            try:
                body_json = json.loads(body)
            except json.JSONDecodeError:
                body_json = None

        # Initial context logging (route template not yet resolved here)
        ctx = {
            "path": raw_path,
            "method": method,
            "path_params": None,  # will try to resolve after routing
            "route": None,  # will try to resolve after routing
            "body": body_json,
        }
        logger.append_keys(fastapi=ctx)
        logger.info("Received request")

        # Add X-Ray annotations early
        tracer.put_annotation(key="path", value=raw_path)
        tracer.put_annotation(key="method", value=method)

        # Capture status code via send wrapper
        status_holder = {"status": 500}
        resp_size_holder = {"bytes": 0}

        start = time.perf_counter_ns()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message.get("status", 500)
                # If Content-Length is set, remember it; otherwise we’ll sum body chunks
                for (h, v) in message.get("headers", []) or []:
                    if h.lower() == b"content-length":
                        try:
                            resp_size_holder["bytes"] = int(v.decode("latin1"))
                        except Exception:
                            pass
            elif message["type"] == "http.response.body":
                # If no Content-Length, accumulate bytes
                if resp_size_holder["bytes"] == 0:
                    resp_size_holder["bytes"] += len(message.get("body") or b"")
            await send(message)

        # Route/execute the request with tracing around the app call
        @tracer.capture_method(capture_response=False)
        async def _call_downstream():
            await self.app(scope, receive_replayed, send_wrapper)

        await _call_downstream()

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
        status = status_holder["status"]
        status_family = f"{status // 100}xx"

        # After downstream handled routing, try to resolve route template & path params
        route_template: Optional[str] = None
        path_params = None
        route_obj = scope.get("route")
        if route_obj is not None:
            # FastAPI/Starlette exposes a path_format like "/items/{item_id}"
            route_template = getattr(route_obj, "path_format", None) or getattr(
                route_obj, "path", None
            )
        path_params = scope.get("path_params", None)

        # Update log context with resolved info and status
        final_ctx = {
            "path": raw_path,
            "method": method,
            "path_params": path_params,
            "route": route_template or raw_path,
            "status_code": status_holder["status"],
            "body": body_json,
        }
        logger.append_keys(fastapi=final_ctx)
        logger.info("Completed request")

        with single_metric(
            name="http_requests_total",
            unit=MetricUnit.Count,
            value=1,
            default_dimensions=metrics.default_dimensions,
            namespace="veda-backend",
        ) as m:
            m.add_dimension("route_template", route_template)
            m.add_dimension("status_family", status_family)
            m.add_metric("http_requests_total", 1, MetricUnit.Count)
            m.add_metric(
                "http_request_duration_ms", elapsed_ms, MetricUnit.Milliseconds
            )
            m.add_metric(
                "http_response_size_bytes", resp_size_holder["bytes"], MetricUnit.Bytes
            )


def _make_receive_replay(messages):
    """
    Build a 'receive' callable that replays given ASGI messages once.
    """

    async def _receive():
        if _receive._idx < len(messages):
            msg = messages[_receive._idx]
            _receive._idx += 1
            return msg
        # No more data
        return {"type": "http.request", "body": b"", "more_body": False}

    _receive._idx = 0  # type: ignore[attr-defined]
    return _receive
