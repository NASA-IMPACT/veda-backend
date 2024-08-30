"""FastAPI application using PGStac.
Based on https://github.com/developmentseed/eoAPI/tree/master/src/eoapi/stac
"""

from aws_lambda_powertools.metrics import MetricUnit
from src.config import TilesApiSettings, api_settings, VedaOpenIdConnectSettings
from src.config import extensions as PgStacExtensions
from src.config import get_request_model as GETModel
from src.config import post_request_model as POSTModel
from src.extension import TiTilerExtension

from eoapi.auth_utils import OpenIdConnectAuth
from fastapi import APIRouter, FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.routing import APIRoute
from stac_fastapi.pgstac.db import close_db_connection, connect_to_db
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates
from starlette_cramjam.middleware import CompressionMiddleware

from .api import VedaStacApi
from .core import VedaCrudClient
from .monitoring import LoggerRouteHandler, logger, metrics, tracer

# from .routes import add_route_dependencies
from .validation import ValidationMiddleware

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore


templates = Jinja2Templates(directory=str(resources_files(__package__) / "templates"))  # type: ignore

tiles_settings = TilesApiSettings()
auth_settings = VedaOpenIdConnectSettings()

api = VedaStacApi(
    app=FastAPI(
        title=f"{api_settings.project_name} STAC API",
        openapi_url="/openapi.json",
        docs_url="/docs",
        root_path=api_settings.root_path,
        swagger_ui_init_oauth=(
            {
                "appName": "STAC Api",
                "clientId": auth_settings.client_id,
                "usePkceWithAuthorizationCodeGrant": True,
                "scopes": "openid stac:item:create stac:item:update stac:item:delete stac:collection:create stac:collection:update stac:collection:delete",
            }
            if auth_settings.client_id
            else {}
        ),
    ),
    title=f"{api_settings.project_name} STAC API",
    description=api_settings.project_description,
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

if api_settings.enable_transactions and auth_settings.client_id:
    oidc_auth = OpenIdConnectAuth(
        openid_configuration_url=auth_settings.openid_configuration_url,
    )

    restricted_prefixes_methods = {
        "/collections": ("POST", "stac:collection:create"),
        "/collections/{collection_id}": ("PUT", "stac:collection:update"),
        "/collections/{collection_id}": ("DELETE", "stac:collection:delete"),
        "/collections/{collection_id}/items": ("POST", "stac:item:create"),
        "/collections/{collection_id}/items/{item_id}": ("PUT", "stac:item:update"),
        "/collections/{collection_id}/items/{item_id}": ("DELETE", "stac:item:delete"),
        "/collections/{collection_id}/bulk_items": ("POST", "stac:item:create"),
    }

    api_routes = {
        route.path: route for route in app.router.routes if isinstance(route, APIRoute)
    }

    for route in app.router.routes:
        method_scope = restricted_prefixes_methods.get(route.path)
        if not method_scope:
            continue
        [method, scope] = method_scope
        if method not in route.methods:
            continue
        oidc_auth.apply_auth_dependencies(route, required_token_scopes=[scope])

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
