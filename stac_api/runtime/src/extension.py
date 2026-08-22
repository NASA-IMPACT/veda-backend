"""TiTiler extension."""

from typing import Annotated
from urllib.parse import urlencode

import attr
from fastapi import APIRouter, FastAPI, HTTPException, Path, Query
from fastapi.responses import RedirectResponse
from stac_fastapi.types.extension import ApiExtension
from starlette.requests import Request

from src.config import ApiSettings

from .monitoring import tracer

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
        router = APIRouter()

        @tracer.capture_method
        @router.get(
            "/collections/{collectionId}/items/{itemId}/{tileMatrixSetId}/tilejson.json",
        )
        async def tilejson(
            request: Request,
            collectionId: Annotated[str, Path(description="Collection ID")],
            itemId: Annotated[str, Path(description="Item ID")],
            tileMatrixSetId: Annotated[
                str, Path(description="TileMatrixSet name (e.g. WebMercatorQuad).")
            ],
            tile_format: Annotated[
                str | None,
                Query(description="Output image type. Default is auto."),
            ] = None,
            tile_scale: Annotated[
                int,
                Query(
                    gt=0,
                    lt=4,
                    description="Tile size scale. 1=256x256, 2=512x512...",
                ),
            ] = 1,
            minzoom: Annotated[
                int | None,
                Query(description="Overwrite default minzoom."),
            ] = None,
            maxzoom: Annotated[
                int | None,
                Query(description="Overwrite default maxzoom."),
            ] = None,
            assets: Annotated[
                str | None,
                Query(description="comma (',') delimited asset names."),
            ] = None,
            expression: Annotated[
                str | None,
                Query(
                    description="rio-tiler's band math expression between "
                    "assets (e.g asset1/asset2)"
                ),
            ] = None,
            bidx: Annotated[
                str | None,
                Query(
                    description="comma (',') delimited band indexes to apply "
                    "to each asset"
                ),
            ] = None,
            asset_expression: Annotated[
                str | None,
                Query(
                    description="rio-tiler's band math expression (e.g b1/b2) "
                    "to apply to each asset"
                ),
            ] = None,
        ):
            """Get items and redirect to stac tiler."""
            if not assets and not expression:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "assets must be defined either via expression or "
                        "assets options."
                    ),
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
                f"{titiler_endpoint}/stac/{tileMatrixSetId}/tilejson.json?{urlencode(qs)}"
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
            collectionId: Annotated[str, Path(description="Collection ID")],
            itemId: Annotated[str, Path(description="Item ID")],
        ):
            """Get items and redirect to stac tiler."""
            qs = [(key, value) for (key, value) in request.query_params._list]
            qs.append(("item", itemId))
            qs.append(("collection", collectionId))

            return RedirectResponse(f"{titiler_endpoint}/stac/viewer?{urlencode(qs)}")

        app.include_router(router, tags=["TiTiler Extension"])
