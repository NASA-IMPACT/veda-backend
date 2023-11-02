"""veda.raster.dependencies."""

import pystac
from rio_tiler.colormap import cmap as default_cmap
from typing_extensions import Annotated

from fastapi import Query
from starlette.requests import Request
from titiler.core.dependencies import create_colormap_dependency
from titiler.pgstac.dependencies import get_stac_item

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore


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


VEDA_CMAPS_FILES = {
    f.stem: str(f) for f in (resources_files(__package__) / "cmap_data").glob("*.npy")  # type: ignore
}
cmap = default_cmap.register(VEDA_CMAPS_FILES)
ColorMapParams = create_colormap_dependency(cmap)
