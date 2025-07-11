"""TiTiler+PgSTAC FastAPI application."""
import logging
from contextlib import asynccontextmanager

from aws_lambda_powertools.metrics import MetricUnit
from src.algorithms import PostProcessParams
from src.alternate_reader import PgSTACReaderAlt
from src.config import ApiSettings
from src.dependencies import ColorMapParams, cmap
from src.extensions import stacViewerExtension
from src.monitoring import LoggerRouteHandler, logger, metrics, tracer
from src.version import __version__ as veda_raster_version

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette_cramjam.middleware import CompressionMiddleware
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import (
    ColorMapFactory,
    MultiBaseTilerFactory,
    TilerFactory,
    TMSFactory,
)
from titiler.core.middleware import CacheControlMiddleware
from titiler.core.resources.enums import OptionalHeader
from titiler.core.resources.responses import JSONResponse
from titiler.extensions import cogValidateExtension, cogViewerExtension
from titiler.mosaic.errors import MOSAIC_STATUS_CODES
from titiler.pgstac.db import close_db_connection, connect_to_db
from titiler.pgstac.dependencies import CollectionIdParams, ItemIdParams, SearchIdParams
from titiler.pgstac.extensions import searchInfoExtension
from titiler.pgstac.factory import (
    MosaicTilerFactory,
    add_search_list_route,
    add_search_register_route,
)
from titiler.pgstac.reader import PgSTACReader

logging.getLogger("botocore.credentials").disabled = True
logging.getLogger("botocore.utils").disabled = True
logging.getLogger("rio-tiler").setLevel(logging.ERROR)

settings = ApiSettings()


if settings.debug:
    optional_headers = [OptionalHeader.server_timing, OptionalHeader.x_assets]
else:
    optional_headers = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan."""
    # Create Connection Pool
    await connect_to_db(app, settings=settings.load_postgres_settings(), pool_kwargs={})
    yield
    # Close the Connection Pool
    await close_db_connection(app)


app = FastAPI(
    title=f"{settings.project_name} Raster API",
    version=veda_raster_version,
    openapi_url="/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
    root_path=settings.root_path,
)

# router to be applied to all titiler route factories (improves logs with FastAPI context)
router = APIRouter(route_class=LoggerRouteHandler)
add_exception_handlers(app, DEFAULT_STATUS_CODES)
add_exception_handlers(app, MOSAIC_STATUS_CODES)

###############################################################################
# /searches - STAC Search endpoint
###############################################################################
searches = MosaicTilerFactory(
    router_prefix="/searches/{search_id}",
    path_dependency=SearchIdParams,
    environment_dependency=settings.get_gdal_config,
    process_dependency=PostProcessParams,
    router=APIRouter(route_class=LoggerRouteHandler),
    # add /statistics [POST] (default to False)
    add_statistics=True,
    # add /map viewer (default to False)
    add_viewer=False,
    # add /bbox [GET] and /feature  [POST] (default to False)
    add_part=True,
    colormap_dependency=ColorMapParams,
    extensions=[
        searchInfoExtension(),
    ],
    optional_headers=optional_headers,
)
app.include_router(
    searches.router, prefix="/searches/{search_id}", tags=["STAC Search"]
)

# add /register endpoint
add_search_register_route(
    app,
    prefix="/searches",
    # any dependency we want to validate
    # when creating the tilejson/map links
    tile_dependencies=[
        searches.layer_dependency,
        searches.dataset_dependency,
        searches.pixel_selection_dependency,
        searches.process_dependency,
        searches.rescale_dependency,
        searches.colormap_dependency,
        searches.render_dependency,
        searches.pgstac_dependency,
        searches.reader_dependency,
        searches.backend_dependency,
    ],
    tags=["STAC Search"],
)
# add /list endpoint
if settings.enable_mosaic_search:
    add_search_list_route(app, prefix="/searches", tags=["STAC Search"])

###############################################################################
# STAC COLLECTION Endpoints
###############################################################################
collection = MosaicTilerFactory(
    path_dependency=CollectionIdParams,
    router_prefix="/collections/{collection_id}",
    add_statistics=True,
    add_viewer=True,
    add_part=True,
    extensions=[
        searchInfoExtension(),
    ],
    optional_headers=optional_headers,
)
app.include_router(
    collection.router, tags=["STAC Collection"], prefix="/collections/{collection_id}"
)


###############################################################################
# /collections/{collection_id}/items/{item_id} - Custom STAC titiler endpoint
###############################################################################
stac = MultiBaseTilerFactory(
    reader=PgSTACReader,
    path_dependency=ItemIdParams,
    router_prefix="/collections/{collection_id}/items/{item_id}",
    environment_dependency=settings.get_gdal_config,
    router=APIRouter(route_class=LoggerRouteHandler),
    extensions=[
        stacViewerExtension(),
    ],
    colormap_dependency=ColorMapParams,
)
app.include_router(
    stac.router,
    tags=["STAC Item"],
    prefix="/collections/{collection_id}/items/{item_id}",
)

###############################################################################
# /alt/collections/{collection_id}/items/{item_id} - Custom STAC titiler endpoint for alternate asset locations
###############################################################################
stac_alt = MultiBaseTilerFactory(
    reader=PgSTACReaderAlt,
    path_dependency=ItemIdParams,
    router_prefix="/alt/collections/{collection_id}/items/{item_id}",
    environment_dependency=settings.get_gdal_config,
    router=APIRouter(route_class=LoggerRouteHandler),
    extensions=[
        stacViewerExtension(),
    ],
    colormap_dependency=ColorMapParams,
)
app.include_router(
    stac_alt.router,
    tags=["Alt Href STAC Item"],
    prefix="/alt/collections/{collection_id}/items/{item_id}",
    include_in_schema=False,
)

###############################################################################
# /cog - External Cloud Optimized GeoTIFF endpoints
###############################################################################
cog = TilerFactory(
    router_prefix="/cog",
    environment_dependency=settings.get_gdal_config,
    router=APIRouter(route_class=LoggerRouteHandler),
    extensions=[
        cogValidateExtension(),
        cogViewerExtension(),
    ],
    colormap_dependency=ColorMapParams,
)

app.include_router(cog.router, tags=["Cloud Optimized GeoTIFF"], prefix="/cog")

###############################################################################
# Colormaps endpoints
###############################################################################
# Set supported colormaps to be the modified cmap list with added colormaps
cmaps = ColorMapFactory(supported_colormaps=cmap)
app.include_router(cmaps.router, tags=["ColorMaps"])


@app.get("/healthz", description="Health Check", tags=["Health Check"])
def ping():
    """Health check."""
    return {"ping": "pong!!"}


# Add support for non-default projections
tms = TMSFactory()
app.include_router(tms.router, tags=["Tiling Schemes"])

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
    minimum_size=0,
    exclude_mediatype={
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/jp2",
        "image/webp",
    },
)


# If the correlation header is used in the UI, we can analyze traces that originate from a given user or client
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ids to all requests and subsequent logs/traces"""
    # Get correlation id from X-Correlation-Id header if provided
    corr_id = request.headers.get("x-correlation-id")
    if not corr_id:
        try:
            # If empty, use request id from aws context
            corr_id = request.scope["aws.context"].aws_request_id
        except KeyError:
            # If empty, use uuid
            corr_id = "local"

    # Add correlation id to logs
    logger.set_correlation_id(corr_id)

    # Add correlation id to traces
    tracer.put_annotation(key="correlation_id", value=corr_id)

    response = await tracer.capture_method(call_next)(request)
    # Return correlation header in response
    response.headers["X-Correlation-Id"] = corr_id
    logger.info("Request completed")
    return response


@app.exception_handler(Exception)
async def validation_exception_handler(request, err):
    """Handle exceptions that aren't caught elsewhere"""
    metrics.add_metric(name="UnhandledExceptions", unit=MetricUnit.Count, value=1)
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
