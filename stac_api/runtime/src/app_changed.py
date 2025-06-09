"""FastAPI application using PGStac with integrated tenant filtering.
Based on https://github.com/developmentseed/eoAPI/tree/master/src/eoapi/stac
"""

import json
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from aws_lambda_powertools.metrics import MetricUnit
from src.config import TilesApiSettings, api_settings
from src.config import extensions as PgStacExtensions
from src.config import get_request_model as GETModel
from src.config import items_get_request_model
from src.config import post_request_model as POSTModel
from src.extension import TiTilerExtension

from fastapi import APIRouter, FastAPI, Request as FastAPIRequest, Depends, Path
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

def update_links_with_tenant(data: dict, tenant: str, base_url: str = "http://localhost:8081") -> dict:
    """Update all links in a response to include tenant prefix."""
    
    def update_link(link: dict):
        if 'href' in link:
            href = link['href']
            if href.startswith(f'{base_url}/'):
                # Replace base URL with tenant-prefixed URL
                link['href'] = href.replace(f'{base_url}/', f'{base_url}/{tenant}/')
            elif href.startswith('/') and not href.startswith(f'/{tenant}/'):
                # Handle relative URLs
                link['href'] = f'/{tenant}{href}'
    
    # Update main response links
    if 'links' in data and isinstance(data['links'], list):
        for link in data['links']:
            update_link(link)
    
    # Update collection links
    if 'collections' in data and isinstance(data['collections'], list):
        for collection in data['collections']:
            if 'links' in collection and isinstance(collection['links'], list):
                for link in collection['links']:
                    update_link(link)
    
    # Update item/feature links
    if 'features' in data and isinstance(data['features'], list):
        for item in data['features']:
            if 'links' in item and isinstance(item['links'], list):
                for link in item['links']:
                    update_link(link)
    
    return data


class TenantOnlyMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce tenant-only access to STAC endpoints."""
    
    def __init__(self, app: ASGIApp, enforce_tenant_only: bool = True):
        super().__init__(app)
        self.enforce_tenant_only = enforce_tenant_only
        # Endpoints that should be tenant-only
        self.tenant_only_endpoints = {
            '/collections', '/search', '/conformance'
        }
        # Endpoints that are allowed without tenant prefix
        self.allowed_endpoints = {
            '/docs', '/openapi.json', '/index.html', '/health', '/'
        }
    
    async def dispatch(self, request: Request, call_next):
        """Check if tenant-only enforcement should be applied."""
        
        if not self.enforce_tenant_only:
            return await call_next(request)
        
        path = request.url.path
        
        # Allow certain endpoints without tenant
        if any(path.startswith(endpoint) for endpoint in self.allowed_endpoints):
            return await call_next(request)
        
        # Check if this is a tenant-only endpoint accessed without tenant
        if any(path.startswith(endpoint) for endpoint in self.tenant_only_endpoints):
            return JSONResponse(
                status_code=400,
                content={
                    "detail": f"This endpoint requires a tenant prefix. Use /{'{tenant}'}{path} instead."
                }
            )
        
        # Allow all other requests
        return await call_next(request)


tiles_settings = TilesApiSettings()
auth_settings = OpenIdConnectSettings(_env_prefix="VEDA_STAC_")


class TenantAwareVedaCrudClient(VedaCrudClient):
    """Extended CRUD client that applies tenant filtering."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def all_collections(self, request: FastAPIRequest, tenant: Optional[str] = None, **kwargs):
        """Get all collections with optional tenant filtering."""
        if tenant:
            # Add tenant filter to the database query
            # This assumes your collections table has a tenant column
            # Adjust based on your actual database schema
            logger.info(f"Filtering collections by tenant: {tenant}")
        
        # Call the parent method
        collections = await super().all_collections(request, **kwargs)
        
        # If tenant is specified, filter the results
        if tenant and hasattr(collections, 'collections'):
            filtered_collections = [
                col for col in collections.collections 
                if col.get('tenant') == tenant or col.get('properties', {}).get('tenant') == tenant
            ]
            collections.collections = filtered_collections
            if hasattr(collections, 'context') and hasattr(collections.context, 'returned'):
                collections.context.returned = len(filtered_collections)
        elif tenant and isinstance(collections, dict) and 'collections' in collections:
            filtered_collections = [
                col for col in collections['collections'] 
                if col.get('tenant') == tenant or col.get('properties', {}).get('tenant') == tenant
            ]
            collections['collections'] = filtered_collections
            if 'numberReturned' in collections:
                collections['numberReturned'] = len(filtered_collections)
        
        return collections
    
    async def get_collection(self, collection_id: str, request: FastAPIRequest, tenant: Optional[str] = None, **kwargs):
        """Get collection with tenant filtering."""
        collection = await super().get_collection(collection_id, request, **kwargs)
        
        if tenant and collection:
            # Check if collection belongs to tenant
            collection_tenant = collection.get('tenant') or collection.get('properties', {}).get('tenant')
            if collection_tenant != tenant:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Collection not found")
        
        return collection
    
    async def item_collection(self, collection_id: str, request: FastAPIRequest, tenant: Optional[str] = None, **kwargs):
        """Get items with tenant filtering."""
        if tenant:
            logger.info(f"Filtering items by tenant: {tenant}")
        
        return await super().item_collection(collection_id, request, **kwargs)
    
    async def post_search(self, search_request, request: FastAPIRequest, tenant: Optional[str] = None, **kwargs):
        """Search with tenant filtering."""
        if tenant:
            logger.info(f"Filtering search by tenant: {tenant}")
            # Modify search request to include tenant filter
            # This depends on your search implementation
        
        return await super().post_search(search_request, request, **kwargs)
    
    async def get_search(self, request: FastAPIRequest, tenant: Optional[str] = None, **kwargs):
        """GET search with tenant filtering."""
        if tenant:
            logger.info(f"Filtering GET search by tenant: {tenant}")
        
        return await super().get_search(request, **kwargs)


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
    client=TenantAwareVedaCrudClient(post_request_model=POSTModel),
    search_get_request_model=GETModel,
    search_post_request_model=POSTModel,
    items_get_request_model=items_get_request_model,
    response_class=ORJSONResponse,
    middlewares=[
        Middleware(CompressionMiddleware),
        Middleware(ValidationMiddleware),
    ],
    router=APIRouter(route_class=LoggerRouteHandler),
)
app = api.app

# Add tenant-specific routes
tenant_router = APIRouter()

@tenant_router.get("/{tenant}/collections")
async def get_tenant_collections(
    tenant: str = Path(..., description="Tenant identifier"),
    request: FastAPIRequest = None,
):
    """Get collections for a specific tenant."""
    logger.info(f"Getting collections for tenant: {tenant}")
    collections = await api.client.all_collections(request, tenant=tenant)
    
    # Update links to include tenant prefix
    if collections and isinstance(collections, dict):
        collections = update_links_with_tenant(collections, tenant)
    
    return collections


@tenant_router.get("/{tenant}/collections/{collection_id}")
async def get_tenant_collection(
    tenant: str = Path(..., description="Tenant identifier"),
    collection_id: str = Path(..., description="Collection identifier"),
    request: FastAPIRequest = None,
):
    """Get a specific collection for a tenant."""
    logger.info(f"Getting collection {collection_id} for tenant: {tenant}")
    collection = await api.client.get_collection(collection_id, request, tenant=tenant)
    
    # Update links to include tenant prefix
    if collection and isinstance(collection, dict):
        collection = update_links_with_tenant(collection, tenant)
    
    return collection


@tenant_router.get("/{tenant}/collections/{collection_id}/items")
async def get_tenant_collection_items(
    tenant: str = Path(..., description="Tenant identifier"),
    collection_id: str = Path(..., description="Collection identifier"),
    request: FastAPIRequest = None,
):
    """Get items from a collection for a specific tenant."""
    logger.info(f"Getting items from collection {collection_id} for tenant: {tenant}")
    items = await api.client.item_collection(collection_id, request, tenant=tenant)
    
    # Update links to include tenant prefix
    if items and isinstance(items, dict):
        items = update_links_with_tenant(items, tenant)
    
    return items


@tenant_router.get("/{tenant}/collections/{collection_id}/items/{item_id}")
async def get_tenant_item(
    tenant: str = Path(..., description="Tenant identifier"),
    collection_id: str = Path(..., description="Collection identifier"),
    item_id: str = Path(..., description="Item identifier"),
    request: FastAPIRequest = None,
):
    """Get a specific item for a tenant."""
    logger.info(f"Getting item {item_id} from collection {collection_id} for tenant: {tenant}")
    return await api.client.get_item(item_id, collection_id, request, tenant=tenant)


@tenant_router.get("/{tenant}/search")
async def get_tenant_search(
    tenant: str = Path(..., description="Tenant identifier"),
    request: FastAPIRequest = None,
):
    """Search items for a specific tenant using GET."""
    logger.info(f"GET search for tenant: {tenant}")
    return await api.client.get_search(request, tenant=tenant)


@tenant_router.post("/{tenant}/search")
async def post_tenant_search(
    tenant: str = Path(..., description="Tenant identifier"),
    search_request: POSTModel = None,
    request: FastAPIRequest = None,
):
    """Search items for a specific tenant using POST."""
    logger.info(f"POST search for tenant: {tenant}")
    return await api.client.post_search(search_request, request, tenant=tenant)


@tenant_router.get("/{tenant}/")
@tenant_router.get("/{tenant}")
async def get_tenant_landing_page(
    tenant: str = Path(..., description="Tenant identifier"),
    request: FastAPIRequest = None,
):
    """Get landing page for a specific tenant."""
    logger.info(f"Getting landing page for tenant: {tenant}")
    
    # Get the base landing page
    base_landing = await api.landing_page(request)
    
    # Modify links to include tenant prefix
    if isinstance(base_landing, dict):
        # Clone the response
        tenant_landing = base_landing.copy()
        
        # Update links to include tenant prefix
        if 'links' in tenant_landing:
            for link in tenant_landing['links']:
                if 'href' in link and link['href'].startswith('/'):
                    if not link['href'].startswith(f'/{tenant}/'):
                        link['href'] = f'/{tenant}{link["href"]}'
        
        # Update title to include tenant
        if 'title' in tenant_landing:
            tenant_landing['title'] = f"{tenant.upper()} - {tenant_landing['title']}"
        
        return tenant_landing
    
    return base_landing


# Include the tenant router
app.include_router(tenant_router, tags=["Tenant-specific endpoints"])

# Add tenant-only enforcement middleware (set to False if you want to keep original routes)
app.add_middleware(TenantOnlyMiddleware, enforce_tenant_only=True)

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


@app.get("/{tenant}/index.html", response_class=HTMLResponse)
async def tenant_viewer_page(request: Request, tenant: str):
    """Tenant-specific search viewer."""
    return templates.TemplateResponse(
        "stac-viewer.html",
        {
            "request": request, 
            "endpoint": str(request.url).replace("/index.html", f"/{tenant}"),
            "tenant": tenant
        },
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
