"""TiTiler extension."""

from typing import Optional
from urllib.parse import urlencode

from typing import Any, Dict, Optional

import attr
from src.config import ApiSettings

from fastapi import APIRouter, FastAPI, HTTPException, Path, Query
from fastapi.responses import RedirectResponse
from stac_fastapi.types.extension import ApiExtension
from starlette.requests import Request

from stac_fastapi.pgstac.core import CoreCrudClient
from stac_fastapi.pgstac.types.search import PgstacSearch
from stac_fastapi.types.stac import Item, ItemCollection

from .monitoring import LoggerRouteHandler, tracer
from .links import LinkInjector

api_settings = ApiSettings()

MAX_B64_ITEM_SIZE = 2000


@attr.s
class TiTilerExtension(ApiExtension):
    """TiTiler extension."""

    def register(self, app: FastAPI, titiler_endpoint: str) -> None:
        """Register the extension with a FastAPI application.
        Args:
            app: target FastAPI application.
        Returns:
            None

        """
        router = APIRouter(route_class=LoggerRouteHandler)

        @tracer.capture_method
        @router.get(
            "/collections/{collectionId}/items/{itemId}/tilejson.json",
        )
        async def tilejson(
            request: Request,
            collectionId: str = Path(..., description="Collection ID"),
            itemId: str = Path(..., description="Item ID"),
            tile_format: Optional[str] = Query(
                None, description="Output image type. Default is auto."
            ),
            tile_scale: int = Query(
                1, gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."
            ),
            minzoom: Optional[int] = Query(
                None, description="Overwrite default minzoom."
            ),
            maxzoom: Optional[int] = Query(
                None, description="Overwrite default maxzoom."
            ),
            assets: Optional[str] = Query(  # noqa
                None,
                description="comma (',') delimited asset names.",
            ),
            expression: Optional[str] = Query(  # noqa
                None,
                description="rio-tiler's band math expression between assets (e.g asset1/asset2)",
            ),
            bidx: Optional[str] = Query(  # noqa
                None,
                description="comma (',') delimited band indexes to apply to each asset",
            ),
            asset_expression: Optional[str] = Query(  # noqa
                None,
                description="rio-tiler's band math expression (e.g b1/b2) to apply to each asset",
            ),
        ):
            """Get items and redirect to stac tiler."""
            if not assets and not expression:
                raise HTTPException(
                    status_code=500,
                    detail="assets must be defined either via expression or assets options.",
                )

            qs_key_to_remove = [
                "tile_format",
                "tile_scale",
                "minzoom",
                "maxzoom",
            ]
            qs = [
                (key, value)
                for (key, value) in request.query_params._list
                if key.lower() not in qs_key_to_remove
            ]
            qs.append(("item", itemId))
            qs.append(("collection", collectionId))

            return RedirectResponse(
                f"{titiler_endpoint}/stac/tilejson.json?{urlencode(qs)}"
            )

        @tracer.capture_method
        @router.get(
            "/collections/{collectionId}/items/{itemId}/viewer",
            responses={
                200: {
                    "description": "Redirect to TiTiler STAC viewer.",
                    "content": {"text/html": {}},
                }
            },
        )
        async def stac_viewer(
            request: Request,
            collectionId: str = Path(..., description="Collection ID"),
            itemId: str = Path(..., description="Item ID"),
        ):
            """Get items and redirect to stac tiler."""
            qs = [(key, value) for (key, value) in request.query_params._list]
            qs.append(("item", itemId))
            qs.append(("collection", collectionId))

            return RedirectResponse(f"{titiler_endpoint}/stac/viewer?{urlencode(qs)}")

        app.include_router(router, tags=["TiTiler Extension"])


class RenderExtension(CoreCrudClient):
    """Render extension."""

    stage: str = None
    domain_name: str = None

    def inject_item_links(
        self, item: Item, render_params: Dict[str, Any], request: Request
    ) -> Item:
        """Add extra/non-mandatory links to an Item"""
        collection_id = item.get("collection", "")
        if collection_id:
            LinkInjector(collection_id, render_params, request).inject_item(item)

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
        render_params = {}

        if len(result["features"]) > 0:
            collection_id = result["features"][0]["collection"]
            collection = await _super.get_collection(collection_id, request=request)

            render_params = collection.get("renders", {})

        item_collection = ItemCollection(
            **{
                **result,
                "features": [
                    self.inject_item_links(i, render_params, request)
                    for i in result.get("features", [])
                ],
            }
        )

        return item_collection