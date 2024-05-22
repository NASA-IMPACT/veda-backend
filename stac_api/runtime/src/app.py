"""FastAPI application using PGStac.
Based on https://github.com/developmentseed/eoAPI/tree/master/src/eoapi/stac
"""

from aws_lambda_powertools.metrics import MetricUnit
from src.config import ApiSettings, TilesApiSettings
from src.config import extensions as PgStacExtensions
from src.config import get_request_model as GETModel
from src.config import post_request_model as POSTModel
from src.extension import TiTilerExtension

from fastapi import APIRouter, FastAPI
from fastapi.params import Depends
from fastapi.responses import ORJSONResponse
from stac_fastapi.pgstac.db import close_db_connection, connect_to_db
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates
from starlette_cramjam.middleware import CompressionMiddleware

from common.auth import Auth
from .api import VedaStacApi
from .core import VedaCrudClient
from .monitoring import LoggerRouteHandler, logger, metrics, tracer
from .routes import add_route_dependencies
from .validation import ValidationMiddleware

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore


templates = Jinja2Templates(directory=str(resources_files(__package__) / "templates"))  # type: ignore

api_settings = ApiSettings()
tiles_settings = TilesApiSettings()

auth = Auth(api_settings)

api = VedaStacApi(
    app=FastAPI(
        title=api_settings.name,
        openapi_url="/openapi.json",
        docs_url="/docs",
        root_path=api_settings.root_path,
        swagger_ui_init_oauth={
            "appName": "Cognito",
            "clientId": api_settings.client_id,
            "usePkceWithAuthorizationCodeGrant": True,
        },
    ),
    title=api_settings.name,
    description=api_settings.name,
    settings=api_settings.load_postgres_settings(),
    extensions=PgStacExtensions,
    client=VedaCrudClient(post_request_model=POSTModel),
    search_get_request_model=GETModel,
    search_post_request_model=POSTModel,
    response_class=ORJSONResponse,
    middlewares=[CompressionMiddleware, ValidationMiddleware],
    router=APIRouter(route_class=LoggerRouteHandler),
)
app = api.app

# see https://github.com/stac-utils/stac-fastapi/issues/265
# app.add_middleware(CompressionMiddleware)

# Set all CORS enabled origins
if api_settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["*"],
    )

# Require auth for all endpoints that create, modify or delete data.
add_route_dependencies(
    app.router.routes,
    [
        {"path": "/collections", "method": "POST", "type": "http"},
        {"path": "/collections/{collectionId}", "method": "PUT", "type": "http"},
        {"path": "/collections/{collectionId}", "method": "DELETE", "type": "http"},
        {"path": "/collections/{collectionId}/items", "method": "POST", "type": "http"},
        {
            "path": "/collections/{collectionId}/items/{itemId}",
            "method": "PUT",
            "type": "http",
        },
        {
            "path": "/collections/{collectionId}/items/{itemId}",
            "method": "DELETE",
            "type": "http",
        },
        {
            "path": "/collections/{collectionId}/bulk_items",
            "method": "POST",
            "type": "http",
        },
    ],
    [Depends(auth.validated_token)],
)

if tiles_settings.titiler_endpoint:
    # Register to the TiTiler extension to the api
    extension = TiTilerExtension()
    extension.register(api.app, tiles_settings.titiler_endpoint)


@app.get("/index.html", response_class=HTMLResponse)
async def viewer_page(request: Request):
    """Search viewer."""
    path = api_settings.root_path or ""
    return templates.TemplateResponse(
        "stac-viewer.html",
        {"request": request, "endpoint": str(request.url).replace("/index.html", path)},
        media_type="text/html",
    )


# If the correlation header is used in the UI, we can analyze traces that originate from a given user or client
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ids to all requests and subsequent logs/traces"""
    # Get correlation id from X-Correlation-Id header
    corr_id = request.headers.get("x-correlation-id")
    if not corr_id:
        try:
            # If empty, use request id from aws context
            corr_id = request.scope["aws.context"].aws_request_id
        except KeyError:
            # If empty, use uuid
            corr_id = "local"
    # Add correlation id to logs
    logger.set_correlation_id(corr_id)
    # Add correlation id to traces
    tracer.put_annotation(key="correlation_id", value=corr_id)

    response = await tracer.capture_method(call_next)(request)
    # Return correlation header in response
    response.headers["X-Correlation-Id"] = corr_id
    logger.info("Request completed")
    return response


@app.exception_handler(Exception)
async def validation_exception_handler(request, err):
    """Handle exceptions that aren't caught elsewhere"""
    metrics.add_metric(name="UnhandledExceptions", unit=MetricUnit.Count, value=1)
    logger.error("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.on_event("startup")
async def startup_event():
    """Connect to database on startup."""
    await connect_to_db(app)


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection."""
    await close_db_connection(app)
