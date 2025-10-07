"""CoreCrudClient extensions for the VEDA STAC API."""
from typing import Any, Dict, Union

from stac_fastapi.pgstac.core import CoreCrudClient
from stac_fastapi.pgstac.types.search import PgstacSearch
from stac_fastapi.types.stac import Item, ItemCollection
from starlette.requests import Request

from .links import LinkInjector

NumType = Union[float, int]


class VedaCrudClient(CoreCrudClient):
    """Veda STAC API Client."""

    def inject_item_links(
        self, item: Item, render_params: Dict[str, Any], request: Request
    ) -> Item:
        """Add extra/non-mandatory links to an Item"""
        collection_id = item.get("collection", "")
        tenant = getattr(request.state, "tenant", None) if request else None

        if collection_id:
            LinkInjector(collection_id, render_params, request, tenant).inject_item(
                item
            )

        return item

    async def _search_base(
        self, search_request: PgstacSearch, **kwargs: Any
    ) -> ItemCollection:
        """Cross catalog search (POST).
        Called with `POST /search`.
        Args:
            search_request: search request parameters.
        Returns:
            ItemCollection containing items which match the search criteria.
        """
        _super: CoreCrudClient = super()
        request = kwargs["request"]

        result = await _super._search_base(search_request, **kwargs)
        # Without assigning item_collection here we will get the error
        # UnboundLocalError: local variable 'item_collection' referenced before assignment (cloudfront 500 error)
        # in case len(result["features"]) == 0
        item_collection = result

        if len(result["features"]) > 0:
            try:
                collection_id = result["features"][0]["collection"]
                collection = await _super.get_collection(collection_id, request=request)

                render_params = collection.get("renders", {})

                item_collection = ItemCollection(
                    **{
                        **result,
                        "features": [
                            self.inject_item_links(
                                i, render_params.get("dashboard", {}), request
                            )
                            for i in result.get("features", [])
                        ],
                    }
                )
            except Exception:
                item_collection = result

        return item_collection
