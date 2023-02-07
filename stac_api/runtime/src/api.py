"""FastAPI extensions for the VEDA STAC API."""
from typing import List

import attr

from stac_fastapi.api.app import StacApi
from stac_fastapi.api.routes import create_async_endpoint

from .core import VedaCrudClient
from .search import CollectionSearchGet, CollectionSearchPost


class VedaStacApi(StacApi):
    """Veda STAC API."""

    client: VedaCrudClient = attr.ib()

    def register_post_search(self):
        """Register search endpoint (POST /search).
        Returns:
            None
        """
        super().register_post_search()
        self.router.add_api_route(
            name="Search",
            path="/collection-id-search",
            response_model=List[str] if self.settings.enable_response_models else None,
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["POST"],
            endpoint=create_async_endpoint(
                self.client.collection_id_post_search,
                CollectionSearchPost,
                self.response_class,
            ),
        )

    def register_get_search(self):
        """Register search endpoint (GET /search).
        Returns:
            None
        """
        super().register_get_search()
        self.router.add_api_route(
            name="Search",
            path="/collection-id-search",
            response_model=List[str] if self.settings.enable_response_models else None,
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["GET"],
            endpoint=create_async_endpoint(
                self.client.collection_id_get_search,
                CollectionSearchGet,
                self.response_class,
            ),
        )
