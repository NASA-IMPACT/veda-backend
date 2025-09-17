"""
Tenant Client for Tenant Middleware
"""
import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

from fastapi import HTTPException
from fastapi import Request as FastAPIRequest
from stac_fastapi.types.stac import Collection, Item, ItemCollection, LandingPage
from starlette.requests import Request

from .core import VedaCrudClient
from .tenant_models import TenantValidationError

logger = logging.getLogger(__name__)


class TenantValidationMixin:
    """Tenant Validation Mixin"""

    def validate_tenant_access(
        self,
        resource: Union[Dict[str, Any], Collection],
        tenant: str,
        resource_id: str = "",
    ) -> None:
        """Validate that a collection resource belongs to a tenant"""
        resource_tenant = self._extract_tenant_from_resource(resource)

        if resource_tenant != tenant:
            raise TenantValidationError(
                resource_type="Collection" if "collection" in resource else "Item",
                resource_id=resource_id,
                tenant=tenant,
                actual_tenant=resource_tenant,
            )

    def _extract_tenant_from_resource(
        self, resource: Union[Dict[str, Any], Collection]
    ) -> Optional[str]:
        return resource.get("properties", {}).get("tenant")


class TenantAwareVedaCrudClient(VedaCrudClient, TenantValidationMixin):
    """Tenant Aware VEDA Crud Client"""

    def __init__(self, *args, **kwargs):
        """Initializes tenant-aware VEDA CRUD client by extending
        the base VEDA CRUD client with tenant functionality such as filtering,
        validation, and customized landing page links.

        Args:
          *args: positional args passed to parent VedaCrudClient
          **kwargs: keyword args passed to parent VedaCrudClient such as
            pgstac_search_model

        """
        super().__init__(*args, **kwargs)

    def get_tenant_from_request(self, request: Request) -> Optional[str]:
        """Gets tenant string from request

        Args:
          request: Incoming request

        Returns:
          tenant, if there is one. None otherwise.

        """
        if hasattr(request, "path_params") and "tenant" in request.path_params:
            return request.path_params["tenant"]
        return None

    async def get_tenant_collections(
        self, request: FastAPIRequest, tenant: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Gets collections belonging to a tenant

        Args:
          request: Incoming request
          tenant: Tenant ID

        Returns:
          Collections belonging to tenant

        """
        collections = await super().all_collections(request, **kwargs)

        collections_dict = collections

        if (
            tenant
            and isinstance(collections_dict, dict)
            and "collections" in collections_dict
        ):
            filtered_collections = [
                col
                for col in collections_dict["collections"]
                if col.get("properties", {}).get("tenant") == tenant
            ]
            collections_dict["collections"] = filtered_collections
            if "numberReturned" in collections_dict:
                collections_dict["numberReturned"] = len(filtered_collections)

        return collections_dict

    async def get_collection(
        self,
        collection_id: str,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs,
    ) -> Collection:
        """Get a specific collection belonging to a tenant by collection, tenant IDs"""

        collection = await super().get_collection(collection_id, request, **kwargs)

        if tenant and collection:
            self.validate_tenant_access(collection, tenant, collection_id)

        return collection

    async def item_collection(
        self,
        collection_id: str,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        limit: int = 10,
        token: Optional[str] = None,
        **kwargs,
    ) -> ItemCollection:
        """Get all items from collection using collection ID and tenant ID"""
        if tenant:
            collection = await super().get_collection(collection_id, request, **kwargs)
            if not collection:
                raise HTTPException(
                    status_code=404,
                    detail=f"Collection {collection_id} not found for tenant {tenant}",
                )
            self.validate_tenant_access(collection, tenant, collection_id)

        return await super().item_collection(
            collection_id=collection_id,
            request=request,
            limit=limit,
            token=token,
            **kwargs,
        )

    async def get_item(
        self,
        item_id: str,
        collection_id: str,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs,
    ) -> Item:
        """Get specific item from collection using collection ID and tenant ID"""
        if tenant:
            collection = await super().get_collection(collection_id, request, **kwargs)
            if not collection:
                raise HTTPException(
                    status_code=404,
                    detail=f"Collection {collection_id} not found for tenant {tenant}",
                )
            self.validate_tenant_access(collection, tenant, collection_id)

        return await super().get_item(item_id, collection_id, request, **kwargs)

    async def post_search(
        self,
        search_request,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs,
    ) -> ItemCollection:
        """POST Search request with tenant filtering

        Args:
          search_request: the search request parameters
          request: the FastAPI request object
          tenant: optional tenant identifier for filtering search
          **kwargs: additional arguments to pass to the parent method

        Returns:
          ItemCollection of the filtered search results

        """
        result = await super().post_search(search_request, request, **kwargs)

        if tenant:
            result = self._filter_search_results_by_tenant(result, tenant)

        return result

    async def get_search(
        self,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs,
    ) -> ItemCollection:
        """GET Search request with tenant filtering

        Args:
          search_request: the search request parameters
          request: the FastAPI request object
          tenant: optional tenant identifier for filtering search
          **kwargs: additional arguments to pass to the parent method

        Returns:
          ItemCollection of the filtered search results

        """
        result = await super().get_search(request, **kwargs)

        if tenant:
            result = self._filter_search_results_by_tenant(result, tenant)

        return result

    def _filter_search_results_by_tenant(
        self, result: ItemCollection, tenant: str
    ) -> ItemCollection:
        """Internal function to filter search results by tenant

        Args:
          result: ItemCollection to filter
          tenant: Tenant identifier to filter on

        Returns:
          Filtered ItemCollection
        """
        if isinstance(result, dict) and "features" in result:
            filtered_features = [
                feature
                for feature in result["features"]
                if feature.get("properties", {}).get("tenant") == tenant
            ]
            result["features"] = filtered_features
            if "numberReturned" in result:
                result["numberReturned"] = len(filtered_features)

        return result

    async def landing_page(
        self, request: FastAPIRequest, tenant: Optional[str] = None, **kwargs
    ) -> LandingPage:
        """Get or generate landing page if a tenant is provided

        Args:
          request: Fast API request object
          tenant: Optional tenant identifier
          **kwargs: Optional key word args to pass to parent method

        Returns:
          Landing Page, customized if tenant provided
        """
        tenant_context = getattr(request.state, "tenant_context", None)

        logger.info(
            f"Landing page requested for tenant: {tenant}",
            extra={
                "tenant_id": tenant,
                "request_id": tenant_context.request_id if tenant_context else None,
                "endpoint": "landing_page",
            },
        )

        landing_page = await super().landing_page(request=request, **kwargs)

        if tenant:
            landing_page = self._customize_landing_page_for_tenant(landing_page, tenant)

            logger.info(
                f"Landing page customized for tenant: {tenant}",
                extra={
                    "tenant_id": tenant,
                    "request_id": tenant_context.request_id if tenant_context else None,
                    "links_modified": len(landing_page.get("links", [])),
                },
            )

        return landing_page

    def _customize_landing_page_for_tenant(
        self, landing_page: LandingPage, tenant: str
    ) -> LandingPage:
        """
        Customized landing page with tenant route path injected into url
        """

        if "title" in landing_page:
            landing_page["title"] = f"{tenant.upper()} - {landing_page['title']}"

        if "links" in landing_page:
            for link in landing_page["links"]:
                logger.info("Inspecting links to inject tenant...")
                if "href" in link:
                    href = link["href"]

                    skip_rels = [
                        "self",
                        "root",
                        "service-desc",
                        "service-doc",
                        "conformance",
                    ]
                    if link.get("rel") in skip_rels:
                        logger.info(f"Skipping link with rel {link.get('rel')}")
                        continue

                    if href.startswith("http"):
                        parsed = urlparse(href)
                        path_parts = parsed.path.split("/")
                        # a URL should follow this structure scheme://netloc/path;parameters?query#fragment generally
                        # source: https://docs.python.org/3/library/urllib.parse.html
                        if (
                            len(path_parts) >= 3
                            and path_parts[1] == "api"
                            and path_parts[2] == "stac"
                        ):
                            new_path_parts = path_parts[:3] + [tenant] + path_parts[3:]
                            new_path = "/".join(new_path_parts)
                            link[
                                "href"
                            ] = f"{parsed.scheme}://{parsed.netloc}{new_path}"
                    else:
                        if href.startswith("/api/stac"):
                            link["href"] = href.replace(
                                "/api/stac", f"/api/stac/{tenant}"
                            )

        return landing_page
