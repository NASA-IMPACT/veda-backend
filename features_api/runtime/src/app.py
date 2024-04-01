""""""
from contextlib import asynccontextmanager

from src.config import FeaturesAPISettings as APISettings

from tipg import __version__ as tipg_version
from tipg.collections import register_collection_catalog
from tipg.database import close_db_connection, connect_to_db
from tipg.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from tipg.factory import Endpoints
from tipg.middleware import CacheControlMiddleware, CatalogUpdateMiddleware
from tipg.settings import (
    CustomSQLSettings,
    DatabaseSettings,
)

from fastapi import FastAPI, Request

from starlette.middleware.cors import CORSMiddleware
from starlette_cramjam.middleware import CompressionMiddleware

settings = APISettings()
postgres_settings = settings.load_postgres_settings()
db_settings = DatabaseSettings()
custom_sql_settings = CustomSQLSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """reload catalogs"""
    await connect_to_db(
        app,
        settings=postgres_settings,
    )

    # Register Collection Catalog
    await register_collection_catalog(
        app,
        schemas=db_settings.schemas,
        tables=db_settings.tables,
        exclude_tables=db_settings.exclude_tables,
        exclude_table_schemas=db_settings.exclude_table_schemas,
        functions=db_settings.functions,
        exclude_functions=db_settings.exclude_functions,
        exclude_function_schemas=db_settings.exclude_function_schemas,
        spatial=db_settings.only_spatial_tables,
    )

    yield

    # Close the Connection Pool
    await close_db_connection(app)


app = FastAPI(
    title=settings.name,
    version=tipg_version,
    openapi_url="/api",
    docs_url="/api.html",
    lifespan=lifespan,
    root_path=settings.root_path,
)

ogc_api = Endpoints(
    title=settings.name,
    with_tiles_viewer=settings.add_tiles_viewer,
)
app.include_router(ogc_api.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=[settings.cors_origins],
)
app.add_middleware(CacheControlMiddleware, cachecontrol=settings.cachecontrol)
app.add_middleware(CompressionMiddleware)
app.add_middleware(
    CatalogUpdateMiddleware,
    func=register_collection_catalog,
    ttl=settings.catalog_ttl,
    schemas=db_settings.schemas,
    tables=db_settings.tables,
    exclude_tables=db_settings.exclude_tables,
    exclude_table_schemas=db_settings.exclude_table_schemas,
    functions=db_settings.functions,
    exclude_functions=db_settings.exclude_functions,
    exclude_function_schemas=db_settings.exclude_function_schemas,
    spatial=db_settings.only_spatial_tables,
    spatial_extent=db_settings.spatial_extent,
    datetime_extent=db_settings.datetime_extent,
)

add_exception_handlers(app, DEFAULT_STATUS_CODES)


@app.get(
    "/healthz",
    description="Health Check.",
    summary="Health Check.",
    operation_id="healthCheck",
    tags=["Health Check"],
)
def ping():
    """Health check."""
    return {"ping": "pong!"}


@app.get("/refresh")
async def refresh(request: Request):
    """refresh catalog"""
    await register_collection_catalog(
        request.app,
        schemas=db_settings.schemas,
        tables=db_settings.tables,
        exclude_tables=db_settings.exclude_tables,
        exclude_table_schemas=db_settings.exclude_table_schemas,
        functions=db_settings.functions,
        exclude_functions=db_settings.exclude_functions,
        exclude_function_schemas=db_settings.exclude_function_schemas,
        spatial=db_settings.only_spatial_tables,
        spatial_extent=db_settings.spatial_extent,
        datetime_extent=db_settings.datetime_extent,
    )
    return request.app.state.collection_catalog
