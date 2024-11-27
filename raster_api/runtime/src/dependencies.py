"""veda.raster.dependencies."""

from rio_tiler.colormap import cmap as default_cmap

from titiler.core.dependencies import create_colormap_dependency

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore


VEDA_CMAPS_FILES = {
    f.stem: str(f) for f in (resources_files(__package__) / "cmap_data").glob("*.[npy json]*")  # type: ignore
}
cmap = default_cmap.register(VEDA_CMAPS_FILES)
ColorMapParams = create_colormap_dependency(cmap)
