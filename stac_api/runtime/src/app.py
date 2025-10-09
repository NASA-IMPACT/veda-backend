"""FastAPI application using PGStac.
Based on https://github.com/developmentseed/eoAPI/tree/master/src/eoapi/stac
"""

from contextlib import asynccontextmanager

from aws_lambda_powertools.metrics import MetricUnit
from src.config import (
    TilesApiSettings,
    api_settings,
    application_extensions,
    collections_get_request_model,
    get_request_model,
    items_get_request_model,
    post_request_model,
)
from src.extension import TiTilerExtension
from stac_auth_proxy import configure_app

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from stac_fastapi.api.app import StacApi
from stac_fastapi.pgstac.db import close_db_connection, connect_to_db
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates
from starlette_cramjam.middleware import CompressionMiddleware

from .core import VedaCrudClient
from .monitoring import ObservabilityMiddleware, logger, metrics, tracer
from .tenant_extraction_middleware import TenantExtractionMiddleware
from .tenant_links_middleware import TenantLinksMiddleware
from .validation import ValidationMiddleware

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore


templates = Jinja2Templates(directory=str(resources_files(__package__) / "templates"))  # type: ignore

tiles_settings = TilesApiSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Get a database connection on startup, close it on shutdown."""
    await connect_to_db(app, postgres_settings=api_settings.postgres_settings)
    yield
    await close_db_connection(app)


api = StacApi(
    app=FastAPI(
        title=f"{api_settings.project_name} STAC API",
        openapi_url=api_settings.openapi_spec_endpoint,
        docs_url=api_settings.swagger_ui_endpoint,
        root_path=api_settings.root_path,
        swagger_ui_init_oauth=(
            {
                "appName": "STAC API",
                "clientId": api_settings.client_id,
                "usePkceWithAuthorizationCodeGrant": True,
                "scopes": "openid stac:item:create stac:item:update stac:item:delete stac:collection:create stac:collection:update stac:collection:delete",
            }
            if api_settings.client_id
            else {}
        ),
        lifespan=lifespan,
    ),
    title=f"{api_settings.project_name} STAC API",
    description=api_settings.project_description,
    settings=api_settings,
    extensions=application_extensions,
    client=VedaCrudClient(pgstac_search_model=post_request_model),
    search_get_request_model=get_request_model,
    search_post_request_model=post_request_model,
    collections_get_request_model=collections_get_request_model,
    items_get_request_model=items_get_request_model,
    response_class=ORJSONResponse,
    middlewares=[
        Middleware(ValidationMiddleware),
        Middleware(TenantExtractionMiddleware, root_path=api_settings.root_path),
        Middleware(TenantLinksMiddleware, root_path=api_settings.root_path),
    ],
)

if api_settings.openid_configuration_url and api_settings.enable_stac_auth_proxy:
    # Use stac-auth-proxy when authentication is enabled, which it will be for production envs
    app = configure_app(
        api.app,
        upstream_url=(api_settings.custom_host + (api_settings.root_path or "")),
        default_public=True,
        oidc_discovery_url=str(api_settings.openid_configuration_url),
        oidc_discovery_internal_url=(
            str(api_settings.openid_configuration_internal_url)
            if api_settings.openid_configuration_internal_url
            else None
        ),
        openapi_spec_endpoint=api_settings.openapi_spec_endpoint,
        root_path=api_settings.root_path,
    )
else:
    # Use standard FastAPI app when authentication is disabled, for testing
    # and add compression middleware since stac-auth-proxy provides it when enabled
    app = api.app
    app.add_middleware(CompressionMiddleware)

# Set all CORS enabled origins
if api_settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["*"],
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


app.add_middleware(ObservabilityMiddleware)


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
