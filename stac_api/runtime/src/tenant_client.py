
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, Request as FastAPIRequest
from stac_fastapi.types.stac import Item, ItemCollection, Collections, Collection, LandingPage
from starlette.requests import Request
from urllib.parse import urlparse

from .core import VedaCrudClient
from .tenant_models import TenantValidationError

class TenantAwareVedaCrudClient(VedaCrudClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_tenant_from_request(self, request: Request) -> Optional[str]:
        if hasattr(request, 'path_params') and 'tenant' in request.path_params:
            return request.path_params['tenant']
        return None

    async def get_tenant_collections(
        self,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        collections = await super().all_collections(request, **kwargs)

        collections_dict = collections

        if tenant and isinstance(collections_dict, dict) and 'collections' in collections_dict:
            filtered_collections = [
                col for col in collections_dict['collections']
                if col.get('properties', {}).get('tenant') == tenant
            ]
            collections_dict['collections'] = filtered_collections
            if 'numberReturned' in collections_dict:
                collections_dict['numberReturned'] = len(filtered_collections)

        return collections_dict

    async def get_collection(
        self,
        collection_id: str,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs
    ) -> Collection:
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
        if tenant:
            collection = await super().get_collection(collection_id, request, **kwargs)
            if not collection:
                raise HTTPException(
                    status_code=404,
                    detail=f"Collection {collection_id} not found for tenant {tenant}"
                )
            self.validate_tenant_access(collection, tenant, collection_id)

        return await super().item_collection(
            collection_id=collection_id,
            request=request,
            limit=limit,
            token=token,
            **kwargs
        )

    async def get_item(
        self,
        item_id: str,
        collection_id: str,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs
    ) -> Item:
        if tenant:
            collection = await super().get_collection(collection_id, request, **kwargs)
            if not collection:
                raise HTTPException(
                    status_code=404,
                    detail=f"Collection {collection_id} not found for tenant {tenant}"
                )
            self.validate_tenant_access(collection, tenant, collection_id)

        return await super().get_item(item_id, collection_id, request, **kwargs)

    async def post_search(
        self,
        search_request,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs
    ) -> ItemCollection:
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
        result = await super().get_search(request, **kwargs)

        if tenant:
            result = self._filter_search_results_by_tenant(result, tenant)

        return result

    def _filter_search_results_by_tenant(
        self,
        result: ItemCollection,
        tenant: str
    ) -> ItemCollection:
        if isinstance(result, dict) and 'features' in result:
            filtered_features = [
                feature for feature in result['features']
                if feature.get('properties', {}).get('tenant') == tenant
            ]
            result['features'] = filtered_features
            if 'numberReturned' in result:
                result['numberReturned'] = len(filtered_features)

        return result

    async def landing_page(
        self,
        request: FastAPIRequest,
        tenant: Optional[str] = None,
        **kwargs
    ) -> LandingPage:
        landing_page = await super().landing_page(request=request, **kwargs)

        if tenant:
            landing_page = self._customize_landing_page_for_tenant(landing_page, tenant)

        return landing_page

    def _customize_landing_page_for_tenant(self, landing_page: LandingPage, tenant: str) -> LandingPage:
        if 'title' in landing_page:
            landing_page['title'] = f"{tenant.upper()} - {landing_page['title']}"

        if 'links' in landing_page:
            for link in landing_page['links']:
                if 'href' in link:
                    href = link['href']

                    skip_links = ['self', 'root', 'service-desc', 'service-doc']
                    if link.get('link') in skip_links:
                        continue

                    if href.startswith('http'):
                        parsed = urlparse(href)
                        path_parts = parsed.path.split('/')
                        # a URL should follow this structure scheme://netloc/path;parameters?query#fragment generally
                        # source: https://docs.python.org/3/library/urllib.parse.html
                        if len(path_parts) > 2 and path_parts[1] == 'api' and path_parts[2] == 'stac':
                            new_path = '/'.join(path_parts[:3])
                            link['href'] = f"{parsed.scheme}://{parsed.netloc}{new_path}"
                    else:
                        link['href'] = f"/{tenant}{href}"

                if 'href' in link and not link['href'].startswith('http'):
                    link['href'] = f"/{tenant}{link['href']}"

        return landing_page
