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

from fastapi import APIRouter, FastAPI, Request as FastAPIRequest, Depends, Path, HTTPException
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
import os
from eoapi.auth_utils import OpenIdConnectAuth, OpenIdConnectSettings

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore


templates = Jinja2Templates(directory=str(resources_files(__package__) / "templates"))  # type: ignore

def update_links_with_tenant(data: dict, tenant: str) -> dict:
    """Update all links in a response to include tenant prefix."""
    base_url = os.getenv('BASE_URL', "http://localhost:8081")
    def update_link(link: dict):
        if 'href' in link and not "token=next:" in link['href']:
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
    
    async def _validate_tenant_access(self, collection: dict, tenant: str, collection_id: str = ""):
        """Raise HTTP 404 if the collection does not belong to the given tenant."""
        collection_tenant = collection.get("tenant") or collection.get("properties", {}).get("tenant")
        if collection_tenant != tenant:
            detail = f"Collection {collection_id} not found for tenant {tenant}" if collection_id else "Collection not found"
            raise HTTPException(status_code=404, detail=detail)

    async def get_collection(self, collection_id: str, request: FastAPIRequest, tenant: Optional[str] = None, **kwargs):
        """Get collection with tenant filtering."""
        collection = await super().get_collection(collection_id, request, **kwargs)

        if tenant and collection:
            await self._validate_tenant_access(collection, tenant, collection_id)

        return collection

    async def item_collection(
        self,
        collection_id: str,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        limit: int = 10,  # Add limit
        token: Optional[str] = None,  # Add token
        **kwargs,
    ):
        """Get items with tenant filtering."""
        if tenant:
            logger.info(f"Filtering items by tenant: {tenant} with token: {token}")

            # Your existing tenant validation logic is good
            collection = await super().get_collection(collection_id, request, **kwargs)
            if not collection:
                raise HTTPException(
                    status_code=404,
                    detail=f"Collection {collection_id} not found for tenant {tenant}",
                )
            await self._validate_tenant_access(collection, tenant, collection_id)

        # Pass the pagination parameters to the parent method
        return await super().item_collection(
            collection_id=collection_id,
            request=request,
            limit=limit,
            token=token,
            **kwargs
        )
    async def get_item(self, item_id: str, collection_id: str, request: FastAPIRequest, tenant: Optional[str] = None, **kwargs):
        """Get item with tenant filtering."""
        if tenant:
            logger.info(f"Filtering item {item_id} in collection {collection_id} by tenant: {tenant}")
            
            # Fetch and validate the collection belongs to the tenant
            collection = await super().get_collection(collection_id, request, **kwargs)
            if not collection:
                raise HTTPException(
                    status_code=404,
                    detail=f"Collection {collection_id} not found for tenant {tenant}"
                )
            await self._validate_tenant_access(collection, tenant, collection_id)

        return await super().get_item(item_id, collection_id, request, **kwargs)
    async def post_search(
        self,
        search_request: POSTModel,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs
    ):
        """Search with tenant filtering."""
        if tenant:
            logger.info(f"Filtering search by tenant: {tenant}")
            # IMPORTANT: You must actually filter the search by the tenant.
            # This assumes you have a 'tenant' property in your collection's 'properties'.
            # pgstac search function can take a filter
            tenant_filter = {"op": "=", "args": [{"property": "collection"}, {"property": "tenant"}, tenant]}

            if search_request.filter:
                # If a filter already exists, combine with an 'and'
                search_request.filter = {
                    "op": "and",
                    "args": [
                        search_request.filter,
                        tenant_filter,
                    ],
                }
            else:
                search_request.filter = tenant_filter
            search_request.filter_lang = "cql2-json"

        return await super().post_search(search_request, request, **kwargs)
    
    async def get_search(
        self,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs,
    ):
        """GET search with tenant filtering."""
        if tenant:
            logger.info(f"Filtering GET search by tenant: {tenant}")
            # IMPORTANT: You must also modify the GET search to filter by tenant.
            # This requires modifying the kwargs that will be used to build the search request.
            tenant_filter = {"op": "=", "args": [{"property": "collection"}, {"property": "tenant"}, tenant]}

            if "filter" in kwargs and kwargs["filter"]:
                # Combine with existing filter
                kwargs["filter"] = {
                    "op": "and",
                    "args": [
                        kwargs["filter"],
                        tenant_filter,
                    ],
                }
            else:
                kwargs["filter"] = tenant_filter
            kwargs["filter-lang"] = "cql2-json"

        # The CoreCrudClient.get_search will use the modified kwargs
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
tenant_router = APIRouter(redirect_slashes=True)

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
    request: FastAPIRequest, # It's good practice to have request as the first arg
    tenant: str = Path(..., description="Tenant identifier"),
    collection_id: str = Path(..., description="Collection identifier"),
    limit: int = 10, # Add limit
    token: Optional[str] = None, # Add token
):
    """Get items from a collection for a specific tenant."""
    logger.info(f"Getting items from collection {collection_id} for tenant: {tenant}")

    # Pass the captured parameters to the client method
    items = await api.client.item_collection(
        collection_id=collection_id,
        request=request,
        tenant=tenant,
        limit=limit,
        token=token
    )

    # Your link updater will correctly rewrite the new `next` link if one is present
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
    logger.info(f"======> Getting item {item_id} from collection {collection_id} for tenant: {tenant} <=====")

    item = await api.client.get_item(item_id, collection_id, request, tenant=tenant)
    if item and isinstance(item, dict):
        item = update_links_with_tenant(item, tenant)

    return item

@tenant_router.get("/{tenant}/search")
async def get_tenant_search(
    tenant: str = Path(..., description="Tenant identifier"),
    request: FastAPIRequest = None,
):
    """Search items for a specific tenant using GET."""
    logger.info(f"GET search for tenant: {tenant}")
    return await api.client.get_search(request, tenant=tenant)


@tenant_router.get("/{tenant}/search")
async def get_tenant_search(
    request: FastAPIRequest, # Request should come first
    tenant: str = Path(..., description="Tenant identifier"),
    # Add ALL possible GET search parameters here that stac-fastapi uses
    collections: Optional[str] = None,
    ids: Optional[str] = None,
    bbox: Optional[str] = None,
    datetime: Optional[str] = None,
    limit: int = 10,
    query: Optional[str] = None,
    token: Optional[str] = None,
    filter_lang: Optional[str] = None,
    filter: Optional[str] = None,
    sortby: Optional[str] = None,
    # **kwargs: Any # Avoid using this if possible, be explicit
):
    """Search items for a specific tenant using GET."""
    logger.info(f"GET search for tenant: {tenant}")

    # The base `get_search` method in stac-fastapi unpacks the request itself.
    # What's important is that our `TenantAwareVedaCrudClient.get_search` can access these params.
    # The default behavior of stac-fastapi `get_search` is to parse these from the request query params.
    # Our modification in the client (step 1) will handle the tenant injection.
    
    # We create a dictionary of the GET parameters to pass them explicitly
    # to avoid ambiguity.
    params = {
        "collections": collections.split(",") if collections else None,
        "ids": ids.split(",") if ids else None,
        "bbox": [float(x) for x in bbox.split(",")] if bbox else None,
        "datetime": datetime,
        "limit": limit,
        "query": json.loads(query) if query else None,
        "token": token,
        "filter-lang": filter_lang,
        "filter": json.loads(filter) if filter else None,
        "sortby": sortby,
    }
    # Filter out None values
    clean_params = {k: v for k, v in params.items() if v is not None}

    search_result = await api.client.get_search(request, tenant=tenant, **clean_params)

    # Update links
    if search_result and isinstance(search_result, dict):
        search_result = update_links_with_tenant(search_result, tenant)

    return search_result

@tenant_router.get("/{tenant}/index.html", response_class=HTMLResponse)
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
@tenant_router.get("/{tenant}/")
async def get_tenant_landing_page(
    tenant: str = Path(..., description="Tenant identifier"),
    request: FastAPIRequest = None,
):
    """Get landing page for a specific tenant."""
    logger.info(f"Getting landing page for tenant: {tenant}")

    # Get the base landing page by calling the method on the CLIENT, not the API object
    # Corrected line:
    base_landing = await api.client.landing_page(request=request)

    # The rest of your logic for modifying the links is correct
    if isinstance(base_landing, ORJSONResponse):
        # The client returns a response object, so we need to decode its content
        body = base_landing.body
        tenant_landing = json.loads(body)
        
        # Update links to include tenant prefix
        if 'links' in tenant_landing:
            # Using your update_links_with_tenant function is more robust
            tenant_landing = update_links_with_tenant(tenant_landing, tenant)

        # Update title to include tenant
        if 'title' in tenant_landing:
            tenant_landing['title'] = f"{tenant.upper()} - {tenant_landing['title']}"
        
        # Return a new JSONResponse with the modified content
        return ORJSONResponse(tenant_landing)

    # Fallback in case the response is not what we expect
    return base_landing

# Include the tenant router
app.include_router(tenant_router, tags=["Tenant-specific endpoints"])

# Add tenant-only enforcement middleware (set to False if you want to keep original routes)
# app.add_middleware(TenantOnlyMiddleware, enforce_tenant_only=True)

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
