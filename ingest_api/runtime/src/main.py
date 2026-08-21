from aws_lambda_powertools.metrics import MetricUnit
from fastapi import Annotated, Depends, FastAPI, HTTPException, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from veda_auth.keycloak_client import KeycloakPDPClient, parse_keycloak_from_openid_url

import src.dependencies as dependencies
import src.schemas as schemas
import src.services as services
from src.auth import auth_settings, get_username, oidc_auth
from src.collection_publisher import CollectionPublisher
from src.config import settings
from src.doc import DESCRIPTION
from src.monitoring import ObservabilityMiddleware, logger, metrics, tracer
from src.utils import get_keycloak_client_credentials

app = FastAPI(
    title="VEDA Ingestion API",
    description=DESCRIPTION,
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    contact={"url": "https://github.com/NASA-IMPACT/veda-backend"},
    root_path=settings.root_path,
    openapi_url="/openapi.json",
    docs_url="/docs",
    swagger_ui_init_oauth={
        "appName": "Ingest API",
        "clientId": auth_settings.client_id,
        "usePkceWithAuthorizationCodeGrant": True,
        "scopes": (
            "openid stac:item:create stac:item:update stac:item:delete "
            "stac:collection:create stac:collection:update stac:collection:delete"
        ),
    },
)

collection_publisher = CollectionPublisher()


@app.get(
    "/ingestions", response_model=schemas.ListIngestionResponse, tags=["Ingestion"]
)
async def list_ingestions(
    list_request: Annotated[schemas.ListIngestionRequest, Depends()],
    db: Annotated[services.Database, Depends(dependencies.get_db)],
):
    """
    Lists the STAC items from ingestion.
    """
    return db.fetch_many(
        status=list_request.status, next=list_request.next, limit=list_request.limit
    )


@app.post(
    "/ingestions",
    response_model=schemas.Ingestion,
    tags=["Ingestion"],
    status_code=201,
    dependencies=[
        Security(
            oidc_auth.valid_token_dependency, scopes="stac:item:create stac:item:update"
        )
    ],
)
async def enqueue_ingestion(
    item: schemas.AccessibleItem,
    username: Annotated[str, Depends(get_username)],
    db: Annotated[services.Database, Depends(dependencies.get_db)],
) -> schemas.Ingestion:
    """
    Queues a STAC item for ingestion.
    """
    logger.info(f"\nUsername {username}")
    return schemas.Ingestion(
        id=item.id,
        created_by=username,
        item=item,
        status=schemas.Status.queued,
    ).enqueue(db)


@app.get(
    "/ingestions/{ingestion_id}",
    response_model=schemas.Ingestion,
    tags=["Ingestion"],
)
def get_ingestion(
    ingestion: Annotated[schemas.Ingestion, Depends(dependencies.fetch_ingestion)],
) -> schemas.Ingestion:
    """
    Gets the status of an ingestion.
    """
    return ingestion


@app.patch(
    "/ingestions/{ingestion_id}",
    response_model=schemas.Ingestion,
    tags=["Ingestion"],
    dependencies=[
        Security(oidc_auth.valid_token_dependency, scopes="stac:item:update")
    ],
)
def update_ingestion(
    update: schemas.UpdateIngestionRequest,
    ingestion: Annotated[schemas.Ingestion, Depends(dependencies.fetch_ingestion)],
    db: Annotated[services.Database, Depends(dependencies.get_db)],
):
    """
    Updates the STAC item with the provided item.
    """
    updated_item = ingestion.copy(update=update.dict(exclude_unset=True))
    return updated_item.save(db)


@app.delete(
    "/ingestions/{ingestion_id}",
    response_model=schemas.Ingestion,
    tags=["Ingestion"],
    dependencies=[
        Security(oidc_auth.valid_token_dependency, scopes="stac:item:delete")
    ],
)
def cancel_ingestion(
    ingestion: Annotated[schemas.Ingestion, Depends(dependencies.fetch_ingestion)],
    db: Annotated[services.Database, Depends(dependencies.get_db)],
) -> schemas.Ingestion:
    """
    Cancels an ingestion in queued state."""
    if ingestion.status != schemas.Status.queued:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unable to delete ingestion if status is not {schemas.Status.queued}"
            ),
        )
    return ingestion.cancel(db)


@app.post(
    "/collections",
    tags=["Collection"],
    status_code=201,
    dependencies=[
        Security(
            oidc_auth.valid_token_dependency,
            scopes="stac:collection:create stac:collection:update",
        )
    ],
)
def publish_collection(collection: schemas.DashboardCollection):
    """
    Publish a collection to the STAC database.
    """
    # pgstac create collection
    try:
        collection_publisher.ingest(collection)
        return {f"Successfully published: {collection.id}"}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=(f"Unable to publish collection: {e}"),
        ) from e


@app.delete(
    "/collections/{collection_id}",
    tags=["Collection"],
    dependencies=[
        Security(oidc_auth.valid_token_dependency, scopes="stac:collection:delete")
    ],
)
def delete_collection(collection_id: str):
    """
    Delete a collection from the STAC database.
    """
    try:
        collection_publisher.delete(collection_id=collection_id)
        return {f"Successfully deleted: {collection_id}"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=(f"{e}")) from e


@app.get("/auth/me", tags=["Auth"])
def who_am_i(claims=Depends(oidc_auth.valid_token_dependency)):
    """
    Return claims for the provided JWT
    """
    return claims


def _extract_access_token(request: Request) -> str:
    """Extract and validate Bearer token from Authorization header"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
        )
    return auth_header[7:]


def _parse_keycloak_config() -> tuple[str, str]:
    """Extract Keycloak URL and realm from OIDC configuration URL."""
    try:
        return parse_keycloak_from_openid_url(auth_settings.openid_configuration_url)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


def _get_keycloak_credentials() -> tuple[str, str]:
    """Retrieve Keycloak UMA resource server credentials from the Secrets Manager"""
    if not settings.keycloak_uma_resource_server_client_secret_name:
        raise HTTPException(
            status_code=503,
            detail=(
                "UMA authorization not configured "
                "(missing KEYCLOAK_UMA_RESOURCE_SERVER_CLIENT_SECRET_NAME)"
            ),
        )

    try:
        keycloak_creds = get_keycloak_client_credentials(
            settings.keycloak_uma_resource_server_client_secret_name
        )
        client_id = keycloak_creds.get("id")
        client_secret = keycloak_creds.get("secret")
        if not client_id:
            raise HTTPException(
                status_code=503,
                detail="Keycloak secret missing id",
            )
        return client_id, client_secret
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve Keycloak credentials: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to retrieve Keycloak credentials: {str(e)}",
        ) from e


@app.get(
    "/auth/tenants/writable", response_model=schemas.TenantAccessResponse, tags=["Auth"]
)
async def get_writable_tenant_access(
    request: Request,
    claims=Depends(oidc_auth.valid_token_dependency),
):
    """
    Returns the list of tenants the user has create and update access to.
    """
    user_access_token = _extract_access_token(request)
    keycloak_url, realm = _parse_keycloak_config()
    client_id, client_secret = _get_keycloak_credentials()

    pdp_client = None
    try:
        pdp_client = KeycloakPDPClient(
            keycloak_url=keycloak_url,
            realm=realm,
            client_id=client_id,
            client_secret=client_secret,
            timeout=10.0,
        )

        # Get tenants with create/update access for collections
        collection_tenants = pdp_client.get_tenants_with_create_update_access(
            access_token=user_access_token,
            resource_type="collection",
        )

        # Get tenants with create/update access for items
        item_tenants = pdp_client.get_tenants_with_create_update_access(
            access_token=user_access_token,
            resource_type="item",
        )

        all_tenants = sorted(set(collection_tenants + item_tenants))

        return schemas.TenantAccessResponse(tenants=all_tenants)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant access: {e}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to retrieve tenant access: {str(e)}",
        ) from e
    finally:
        if pdp_client:
            pdp_client.close()


app.add_middleware(ObservabilityMiddleware)


# If the correlation header is used in the UI,
# we can analyze traces that originate from a given user or client
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


# exception handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(str(exc), status_code=422)


@app.exception_handler(Exception)
async def general_exception_handler(request, err):
    """Handle exceptions that aren't caught elsewhere"""
    metrics.add_metric(name="UnhandledExceptions", unit=MetricUnit.Count, value=1)
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
