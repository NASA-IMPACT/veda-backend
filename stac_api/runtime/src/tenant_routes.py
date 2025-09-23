""" Tenant Route Handler """
import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from stac_fastapi.types.stac import Item, ItemCollection

from .tenant_client import TenantAwareVedaCrudClient
from .tenant_models import TenantSearchRequest

logger = logging.getLogger(__name__)


class TenantRouteHandler:
    """Route handler for tenant-aware STAC API endpoints"""

    def __init__(self, client: TenantAwareVedaCrudClient):
        """Initializes tenant-aware route handler"""
        self.client = client

    async def get_tenant_collection(
        self,
        request: Request,
        tenant: str = Path(..., description="Tenant identifier"),
        collection_id: str = Path(..., description="Collection identifier"),
    ) -> Dict:
        """Get a specific collection belonging to a specific tenant"""
        logger.info(f"Getting collection {collection_id} for tenant: {tenant}")

        try:
            collection = await self.client.get_collection(
                collection_id, request, tenant=tenant
            )
            return collection
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error getting collection {collection_id} for tenant {tenant}: {str(e)}"
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_tenant_collection_items(
        self,
        request: Request,
        tenant: str = Path(..., description="Tenant identifier"),
        collection_id: str = Path(..., description="Collection identifier"),
        limit: int = Query(10, description="Maximum number of items to return"),
        token: Optional[str] = Query(None, description="Pagination token"),
    ) -> ItemCollection:
        """Get all items from a collection filtered by a specific tenant"""
        logger.info(
            f"Getting items from collection {collection_id} for tenant: {tenant}"
        )

        try:
            items = await self.client.item_collection(
                collection_id=collection_id,
                request=request,
                tenant=tenant,
                limit=limit,
                token=token,
            )
            return items
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error getting items from collection {collection_id} for tenant {tenant}: {str(e)}"
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_tenant_item(
        self,
        request: Request,
        tenant: str = Path(..., description="Tenant identifier"),
        collection_id: str = Path(..., description="Collection identifier"),
        item_id: str = Path(..., description="Item identifier"),
    ) -> Item:
        """Get a specific item for a tenant"""
        logger.info(
            f"Getting item {item_id} from collection {collection_id} for tenant: {tenant}"
        )

        try:
            item = await self.client.get_item(
                item_id, collection_id, request, tenant=tenant
            )
            return item
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error getting item {item_id} from collection {collection_id} for tenant {tenant}: {str(e)}"
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_tenant_search(
        self,
        request: Request,
        tenant: str = Path(..., description="Tenant identifier"),
        collections: Optional[str] = Query(
            None, description="Comma-separated list of collection IDs"
        ),
        ids: Optional[str] = Query(
            None, description="Comma-separated list of item IDs"
        ),
        bbox: Optional[str] = Query(None, description="Bounding box"),
        datetime: Optional[str] = Query(None, description="Datetime range"),
        limit: int = Query(10, description="Maximum number of results"),
        query: Optional[str] = Query(None, description="Query parameters"),
        token: Optional[str] = Query(None, description="Pagination token"),
        filter_lang: Optional[str] = Query("cql2-text", description="Filter language"),
        filter: Optional[str] = Query(None, description="CQL2 filter"),
        sortby: Optional[str] = Query(None, description="Sort parameters"),
    ) -> ItemCollection:
        """Search items for a specific tenant using GET"""
        logger.info(f"GET search for tenant: {tenant}")

        try:
            search_params = {
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

            clean_params = {k: v for k, v in search_params.items() if v is not None}

            search_result = await self.client.get_search(
                request, tenant=tenant, **clean_params
            )

            return search_result
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in search parameters: {str(e)}")
            raise HTTPException(
                status_code=400, detail="Invalid JSON in search parameters"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error performing search for tenant {tenant}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def post_tenant_search(
        self,
        search_request: TenantSearchRequest,
        request: Request,
        tenant: str = Path(..., description="Tenant identifier"),
    ) -> ItemCollection:
        """Search items for a specific tenant using POST"""
        logger.info(f"POST search for tenant: {tenant}")

        try:
            search_request.add_tenant_filter(tenant)

            search_result = await self.client.post_search(
                search_request, request, tenant=tenant
            )

            return search_result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error performing POST search for tenant {tenant}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")


def create_tenant_router(client: TenantAwareVedaCrudClient) -> APIRouter:
    """Create tenant-specific router"""

    router = APIRouter(redirect_slashes=True)
    handler = TenantRouteHandler(client)

    logger.info("Creating tenant router with routes")

    router.add_api_route(
        "/{tenant}/collections/{collection_id}",
        handler.get_tenant_collection,
        methods=["GET"],
        summary="Get tenant collection",
        description="Retrieve a specific collection for a tenant",
    )

    router.add_api_route(
        "/{tenant}/collections/{collection_id}/items",
        handler.get_tenant_collection_items,
        methods=["GET"],
        summary="Get tenant collection items",
        description="Retrieve items from a collection for a tenant",
    )

    router.add_api_route(
        "/{tenant}/collections/{collection_id}/items/{item_id}",
        handler.get_tenant_item,
        methods=["GET"],
        summary="Get tenant item",
        description="Retrieve a specific item for a tenant",
    )

    # Search endpoints
    router.add_api_route(
        "/{tenant}/search",
        handler.get_tenant_search,
        methods=["GET"],
        summary="Search tenant items (GET)",
        description="Search items for a tenant using GET method",
    )

    router.add_api_route(
        "/{tenant}/search",
        handler.post_tenant_search,
        methods=["POST"],
        summary="Search tenant items (POST)",
        description="Search items for a tenant using POST method",
    )

    logger.info(f"Created tenant router with {len(router.routes)} routes")
    return router
