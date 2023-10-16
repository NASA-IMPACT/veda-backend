"""veda.raster.dependencies."""

import pystac
from typing_extensions import Annotated

from fastapi import Query
from starlette.requests import Request
from titiler.pgstac.dependencies import get_stac_item


def ItemPathParams(
    request: Request,
    collection: Annotated[
        str,
        Query(description="STAC Collection ID"),
    ],
    item: Annotated[
        str,
        Query(description="STAC Item ID"),
    ],
) -> pystac.Item:
    """STAC Item dependency."""
    return get_stac_item(request.app.state.dbpool, collection, item)
