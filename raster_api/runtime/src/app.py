"""TiTiler+PgSTAC FastAPI application."""
import logging
import os

from rasterio.session import AWSSession

# from titiler.application.routers.cog import cog
from rio_cogeo.cogeo import cog_info as rio_cogeo_info
from rio_cogeo.models import Info
from src.config import ApiSettings
from src.factory import MosaicTilerFactory, MultiBaseTilerFactory
from src.version import __version__ as delta_raster_version

from fastapi import Depends, FastAPI, Query
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette_cramjam.middleware import CompressionMiddleware
from titiler.application.custom import templates
from titiler.core.dependencies import DatasetPathParams
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import TilerFactory
from titiler.core.middleware import CacheControlMiddleware
from titiler.core.resources.enums import OptionalHeader
from titiler.mosaic.errors import MOSAIC_STATUS_CODES
from titiler.pgstac.db import close_db_connection, connect_to_db
from titiler.pgstac.dependencies import ItemPathParams
from titiler.pgstac.reader import PgSTACReader

logging.getLogger("botocore.credentials").disabled = True
logging.getLogger("botocore.utils").disabled = True
logging.getLogger("rio-tiler").setLevel(logging.ERROR)

settings = ApiSettings()

if settings.debug:
    optional_headers = [OptionalHeader.server_timing, OptionalHeader.x_assets]
else:
    optional_headers = []

app = FastAPI(title=settings.name, version=delta_raster_version)
add_exception_handlers(app, DEFAULT_STATUS_CODES)
add_exception_handlers(app, MOSAIC_STATUS_CODES)

try:
    gdal_config = {
        # We use Custom AWS session with credential created by the EDL lambda
        "session": AWSSession(
            aws_access_key_id=os.environ["ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["SECRET_ACCESS_KEY"],
            aws_session_token=os.environ["SESSION_TOKEN"],
        )
    }
except KeyError:
    gdal_config = {}


# Custom PgSTAC mosaic tiler
mosaic = MosaicTilerFactory(
    router_prefix="/mosaic",
    enable_mosaic_search=settings.enable_mosaic_search,
    optional_headers=optional_headers,
    gdal_config=gdal_config,
)
app.include_router(mosaic.router, prefix="/mosaic", tags=["Mosaic"])

# Custom STAC titiler endpoint (not added to the openapi docs)
stac = MultiBaseTilerFactory(
    reader=PgSTACReader,
    path_dependency=ItemPathParams,
    optional_headers=optional_headers,
    router_prefix="/stac",
    gdal_config=gdal_config,
)
app.include_router(stac.router, tags=["Items"], prefix="/stac")

cog = TilerFactory(
    router_prefix="/cog", optional_headers=optional_headers, gdal_config=gdal_config
)


@cog.router.get("/validate", response_model=Info)
def cog_validate(
    src_path: str = Depends(DatasetPathParams),
    strict: bool = Query(False, description="Treat warnings as errors"),
):
    """Validate a COG"""
    return rio_cogeo_info(src_path, strict=strict)


@cog.router.get("/viewer", response_class=HTMLResponse)
def cog_demo(request: Request):
    """COG Viewer."""
    return templates.TemplateResponse(
        name="cog_index.html",
        context={
            "request": request,
            "tilejson_endpoint": cog.url_for(request, "tilejson"),
            "info_endpoint": cog.url_for(request, "info"),
            "statistics_endpoint": cog.url_for(request, "statistics"),
        },
        media_type="text/html",
    )


app.include_router(cog.router, tags=["Cloud Optimized GeoTIFF"], prefix="/cog")


@app.get("/healthz", description="Health Check", tags=["Health Check"])
def ping():
    """Health check."""
    return {"ping": "pong!!"}


# Set all CORS enabled origins
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

app.add_middleware(
    CacheControlMiddleware,
    cachecontrol=settings.cachecontrol,
    exclude_path={r"/healthz"},
)
app.add_middleware(
    CompressionMiddleware,
    exclude_mediatype={
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/jp2",
        "image/webp",
    },
)


@app.on_event("startup")
async def startup_event() -> None:
    """Connect to database on startup."""
    await connect_to_db(app, settings=settings.load_postgres_settings())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Close database connection."""
    await close_db_connection(app)
