"""TiTiler+PgSTAC FastAPI application."""
import logging
from contextlib import asynccontextmanager

from aws_lambda_powertools.metrics import MetricUnit
from src.algorithms import PostProcessParams
from src.config import ApiSettings
from src.dependencies import ItemPathParams
from src.extensions import stacViewerExtension
from src.monitoring import LoggerRouteHandler, logger, metrics, tracer
from src.version import __version__ as veda_raster_version

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette_cramjam.middleware import CompressionMiddleware
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import MultiBaseTilerFactory, TilerFactory, TMSFactory
from titiler.core.middleware import CacheControlMiddleware
from titiler.core.resources.enums import OptionalHeader
from titiler.core.resources.responses import JSONResponse
from titiler.extensions import cogValidateExtension, cogViewerExtension
from titiler.mosaic.errors import MOSAIC_STATUS_CODES
from titiler.pgstac.db import close_db_connection, connect_to_db
from titiler.pgstac.factory import MosaicTilerFactory
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
    await connect_to_db(app, settings=settings.load_postgres_settings())
    yield
    # Close the Connection Pool
    await close_db_connection(app)


app = FastAPI(
    title=settings.name,
    version=veda_raster_version,
    openapi_url="/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

# router to be applied to all titiler route factories (improves logs with FastAPI context)
router = APIRouter(route_class=LoggerRouteHandler)
add_exception_handlers(app, DEFAULT_STATUS_CODES)
add_exception_handlers(app, MOSAIC_STATUS_CODES)

###############################################################################
# /mosaic - PgSTAC Mosaic titiler endpoint
###############################################################################
mosaic = MosaicTilerFactory(
    router_prefix="/mosaic",
    optional_headers=optional_headers,
    environment_dependency=settings.get_gdal_config,
    process_dependency=PostProcessParams,
    router=APIRouter(route_class=LoggerRouteHandler),
    # add /list (default to False)
    add_mosaic_list=settings.enable_mosaic_search,
    # add /statistics [POST] (default to False)
    add_statistics=True,
    # add /map viewer (default to False)
    add_viewer=False,
    # add /bbox [GET] and /feature  [POST] (default to False)
    add_part=True,
)
app.include_router(mosaic.router, prefix="/mosaic", tags=["Mosaic"])
# TODO
# prefix will be replaced by `/mosaics/{search_id}` in titiler-pgstac 0.9.0

###############################################################################
# /stac - Custom STAC titiler endpoint
###############################################################################
stac = MultiBaseTilerFactory(
    reader=PgSTACReader,
    path_dependency=ItemPathParams,
    optional_headers=optional_headers,
    router_prefix="/stac",
    environment_dependency=settings.get_gdal_config,
    router=APIRouter(route_class=LoggerRouteHandler),
    extensions=[
        stacViewerExtension(),
    ],
)
app.include_router(stac.router, tags=["Items"], prefix="/stac")
# TODO
# in titiler-pgstac we replaced the prefix to `/collections/{collection_id}/items/{item_id}`

###############################################################################
# /cog - External Cloud Optimized GeoTIFF endpoints
###############################################################################
cog = TilerFactory(
    router_prefix="/cog",
    optional_headers=optional_headers,
    environment_dependency=settings.get_gdal_config,
    router=APIRouter(route_class=LoggerRouteHandler),
    extensions=[
        cogValidateExtension(),
        cogViewerExtension(),
    ],
)

app.include_router(cog.router, tags=["Cloud Optimized GeoTIFF"], prefix="/cog")


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
