"""FastAPI application using PGStac with integrated tenant filtering.
Based on https://github.com/developmentseed/eoAPI/tree/master/src/eoapi/stac
"""

import json
from contextlib import asynccontextmanager
from typing import Dict, Any

from aws_lambda_powertools.metrics import MetricUnit
from src.config import TilesApiSettings, api_settings
from src.config import extensions as PgStacExtensions
from src.config import get_request_model as GETModel
from src.config import items_get_request_model
from src.config import post_request_model as POSTModel
from src.extension import TiTilerExtension

from fastapi import APIRouter, FastAPI, Request as FastAPIRequest, Depends
from fastapi.responses import ORJSONResponse
from stac_fastapi.pgstac.db import close_db_connection, connect_to_db
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.templating import Jinja2Templates
from starlette.types import ASGIApp
from starlette_cramjam.middleware import CompressionMiddleware

from .api import VedaStacApi
from .core import VedaCrudClient
from .monitoring import LoggerRouteHandler, logger, metrics, tracer
from .validation import ValidationMiddleware

from eoapi.auth_utils import OpenIdConnectAuth, OpenIdConnectSettings

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore


templates = Jinja2Templates(directory=str(resources_files(__package__) / "templates"))  # type: ignore

tiles_settings = TilesApiSettings()
auth_settings = OpenIdConnectSettings(_env_prefix="VEDA_STAC_")


class TenantFilteringMiddleware(BaseHTTPMiddleware):
    """Middleware to extract tenant from request and apply filtering."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Process request and apply tenant filtering."""
        
        # Extract tenant from URL path
        path_parts = request.url.path.strip('/').split('/')
        
        # Check if first path segment is a potential tenant (not a known STAC endpoint)
        known_endpoints = {'collections', 'search', 'docs', 'openapi.json', 'index.html'}
        
        if (len(path_parts) >= 1 and 
            path_parts[0] not in known_endpoints and 
            path_parts[0] != ''):
            
            tenant = path_parts[0]
            
            # Store tenant in request state
            request.state.tenant_filter = tenant
            
            # Modify the path to remove tenant part
            if len(path_parts) > 1:
                new_path = '/' + '/'.join(path_parts[1:])
            else:
                new_path = '/'
                
            # Update request scope
            scope = request.scope.copy()
            scope['path'] = new_path
            scope['raw_path'] = new_path.encode()
            
            # Create new request with modified scope
            modified_request = Request(scope, request.receive)
            
            # Process the modified request
            response = await call_next(modified_request)
            return response
        
        # If no tenant in URL, proceed normally
        return await call_next(request)


def get_tenant_filter(request: FastAPIRequest) -> str:
    """Dependency to extract tenant filter from request state."""
    return getattr(request.state, 'tenant_filter', None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Get a database connection on startup, close it on shutdown."""
    await connect_to_db(app)
    yield
    await close_db_connection(app)


# Create the base STAC API
api = VedaStacApi(
    app=FastAPI(
        title=f"{api_settings.project_name} STAC API",
        openapi_url="/openapi.json",
        docs_url="/docs",
        root_path=api_settings.root_path,
        swagger_ui_init_oauth=(
            {
                "appName": "STAC API",
                "clientId": auth_settings.client_id,
                "usePkceWithAuthorizationCodeGrant": True,
                "scopes": "openid stac:item:create stac:item:update stac:item:delete stac:collection:create stac:collection:update stac:collection:delete",
            }
            if auth_settings.client_id
            else {}
        ),
        lifespan=lifespan,
    ),
    title=f"{api_settings.project_name} STAC API",
    description=api_settings.project_description,
    settings=api_settings.load_postgres_settings(),
    extensions=PgStacExtensions,
    client=VedaCrudClient(post_request_model=POSTModel),
    search_get_request_model=GETModel,
    search_post_request_model=POSTModel,
    items_get_request_model=items_get_request_model,
    response_class=ORJSONResponse,
    middlewares=[
        Middleware(CompressionMiddleware),
        Middleware(ValidationMiddleware),
        Middleware(TenantFilteringMiddleware),  # Add tenant filtering middleware
    ],
    router=APIRouter(route_class=LoggerRouteHandler),
)
app = api.app

# Set all CORS enabled origins
if api_settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["*"],
    )

# Modify the VedaCrudClient to handle tenant filtering
class TenantAwareVedaCrudClient(VedaCrudClient):
    """Extended CRUD client that applies tenant filtering."""
    
    async def get_collections(self, request: FastAPIRequest, **kwargs):
        """Get collections with tenant filtering."""
        tenant = get_tenant_filter(request)
        
        if tenant:
            # Add tenant filter to the query
            # This assumes your database has a tenant column in collections
            # Adjust the filter implementation based on your actual schema
            if 'filter' not in kwargs:
                kwargs['filter'] = {}
            kwargs['filter']['tenant'] = tenant
        
        return await super().get_collections(request, **kwargs)
    
    async def get_collection(self, collection_id: str, request: FastAPIRequest, **kwargs):
        """Get collection with tenant filtering."""
        tenant = get_tenant_filter(request)
        
        if tenant:
            # First check if collection belongs to tenant
            collection = await super().get_collection(collection_id, request, **kwargs)
            if collection and collection.get('tenant') != tenant:
                # Return 404 if collection doesn't belong to tenant
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Collection not found")
            return collection
        
        return await super().get_collection(collection_id, request, **kwargs)
    
    async def item_collection(self, collection_id: str, request: FastAPIRequest, **kwargs):
        """Get items with tenant filtering."""
        tenant = get_tenant_filter(request)
        
        if tenant:
            # Add tenant filter for items
            if 'filter' not in kwargs:
                kwargs['filter'] = {}
            kwargs['filter']['tenant'] = tenant
        
        return await super().item_collection(collection_id, request, **kwargs)
    
    async def post_search(self, search_request, request: FastAPIRequest, **kwargs):
        """Search with tenant filtering."""
        tenant = get_tenant_filter(request)
        
        if tenant:
            # Add tenant filter to search request
            if not hasattr(search_request, 'filter') or search_request.filter is None:
                search_request.filter = {}
            
            # Add tenant filter (adjust based on your filter implementation)
            if isinstance(search_request.filter, dict):
                search_request.filter['tenant'] = tenant
            else:
                # Handle other filter formats as needed
                pass
        
        return await super().post_search(search_request, request, **kwargs)
    
    async def get_search(self, request: FastAPIRequest, **kwargs):
        """GET search with tenant filtering."""
        tenant = get_tenant_filter(request)
        
        if tenant:
            # Add tenant filter to query parameters
            if 'filter' not in kwargs:
                kwargs['filter'] = {}
            kwargs['filter']['tenant'] = tenant
        
        return await super().get_search(request, **kwargs)


# Replace the client in the existing API
api.client = TenantAwareVedaCrudClient(post_request_model=POSTModel)

if api_settings.enable_transactions and auth_settings.client_id:
    oidc_auth = OpenIdConnectAuth(
        openid_configuration_url=auth_settings.openid_configuration_url,
        allowed_jwt_audiences="account",
    )

    restricted_prefixes_methods = {
        "/collections": [("POST", "stac:collection:create")],
        "/collections/{collection_id}": [
            ("PUT", "stac:collection:update"),
            ("DELETE", "stac:collection:delete"),
        ],
        "/collections/{collection_id}/items": [("POST", "stac:item:create")],
        "/collections/{collection_id}/items/{item_id}": [
            ("PUT", "stac:item:update"),
            ("DELETE", "stac:item:delete"),
        ],
        "/collections/{collection_id}/bulk_items": [("POST", "stac:item:create")],
    }

    for route in app.router.routes:
        method_scopes = restricted_prefixes_methods.get(route.path)
        if not method_scopes:
            continue
        for method, scope in method_scopes:
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
