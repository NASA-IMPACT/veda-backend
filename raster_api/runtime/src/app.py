"""TiTiler+PgSTAC FastAPI application."""
import logging

from aws_lambda_powertools.metrics import MetricUnit
from rio_cogeo.cogeo import cog_info as rio_cogeo_info
from rio_cogeo.models import Info
from src.config import ApiSettings
from src.datasetparams import DatasetParams
from src.factory import MosaicTilerFactory, MultiBaseTilerFactory
from src.version import __version__ as veda_raster_version

from fastapi import APIRouter, Depends, FastAPI, Query
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
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

from .monitoring import LoggerRouteHandler, logger, metrics, tracer

logging.getLogger("botocore.credentials").disabled = True
logging.getLogger("botocore.utils").disabled = True
logging.getLogger("rio-tiler").setLevel(logging.ERROR)

settings = ApiSettings()

if settings.debug:
    optional_headers = [OptionalHeader.server_timing, OptionalHeader.x_assets]
else:
    optional_headers = []

app = FastAPI(title=settings.name, version=veda_raster_version)
# router to be applied to all titiler route factories (improves logs with FastAPI context)
router = APIRouter(route_class=LoggerRouteHandler)
add_exception_handlers(app, DEFAULT_STATUS_CODES)
add_exception_handlers(app, MOSAIC_STATUS_CODES)

# Custom PgSTAC mosaic tiler
mosaic = MosaicTilerFactory(
    router_prefix="/mosaic",
    enable_mosaic_search=settings.enable_mosaic_search,
    optional_headers=optional_headers,
    gdal_config=settings.get_gdal_config(),
    dataset_dependency=DatasetParams,
    router=APIRouter(route_class=LoggerRouteHandler),
)
app.include_router(mosaic.router, prefix="/mosaic", tags=["Mosaic"])

# Custom STAC titiler endpoint (not added to the openapi docs)
stac = MultiBaseTilerFactory(
    reader=PgSTACReader,
    path_dependency=ItemPathParams,
    optional_headers=optional_headers,
    router_prefix="/stac",
    gdal_config=settings.get_gdal_config(),
    router=APIRouter(route_class=LoggerRouteHandler),
)
app.include_router(stac.router, tags=["Items"], prefix="/stac")

cog = TilerFactory(
    router_prefix="/cog",
    optional_headers=optional_headers,
    gdal_config=settings.get_gdal_config(),
    router=APIRouter(route_class=LoggerRouteHandler),
)


@cog.router.get("/validate", response_model=Info)
def cog_validate(
    src_path: str = Depends(DatasetPathParams),
    strict: bool = Query(False, description="Treat warnings as errors"),
):
    """Validate a COG"""
    return rio_cogeo_info(src_path, strict=strict, config=settings.get_gdal_config())


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


@app.on_event("startup")
async def startup_event() -> None:
    """Connect to database on startup."""
    await connect_to_db(app, settings=settings.load_postgres_settings())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Close database connection."""
    await close_db_connection(app)
