import base64
import binascii
import enum
import json
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from urllib.parse import urlparse

import src.validators as validators
from pydantic import (
    BaseModel,
    Field,
    Json,
    PositiveInt,
    error_wrappers,
    validator,
)
from src.schema_helpers import SpatioTemporalExtent
from stac_pydantic import Collection, Item, shared
from stac_pydantic.links import Link

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError

if TYPE_CHECKING:
    from src import services


class Link(Link, extra="allow"):
    pass


class AccessibleAsset(shared.Asset):
    @validator("href")
    def is_accessible(cls, href):
        url = urlparse(href)

        if url.scheme in ["https", "http"]:
            validators.url_is_accessible(href)
        elif url.scheme in ["s3"]:
            validators.s3_object_is_accessible(
                bucket=url.hostname, key=url.path.lstrip("/")
            )
        else:
            ValueError(f"Unsupported scheme: {url.scheme}")

        return href


class AccessibleItem(Item):
    assets: Dict[str, AccessibleAsset]

    @validator("collection")
    def exists(cls, collection):
        validators.collection_exists(collection_id=collection)
        return collection


class DashboardCollection(Collection):
    is_periodic: Optional[bool] = Field(default=False, alias="dashboard:is_periodic")
    time_density: Optional[str] = Field(default=None, alias="dashboard:time_density")
    item_assets: Optional[Dict]
    links: Optional[List[Link]]
    assets: Optional[Dict]
    extent: SpatioTemporalExtent

    class Config:
        allow_population_by_field_name = True


class Status(str, enum.Enum):
    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        return cls.unknown

    started = "started"
    queued = "queued"
    failed = "failed"
    succeeded = "succeeded"
    cancelled = "cancelled"


class AuthResponse(BaseModel):
    AccessToken: str = Field(..., description="Token used to authenticate the user.")
    ExpiresIn: int = Field(
        ..., description="Number of seconds before the AccessToken expires."
    )
    TokenType: str = Field(
        ..., description="Type of token being returned (e.g. 'Bearer')."
    )
    RefreshToken: str = Field(
        ..., description="Token used to refresh the AccessToken when it expires."
    )
    IdToken: str = Field(
        ..., description="Token containing information about the authenticated user."
    )


class Ingestion(BaseModel):
    id: str = Field(..., description="ID of the STAC item")
    status: Status = Field(..., description="Status of the ingestion")
    message: Optional[str] = Field(
        None, description="Message returned from the step function."
    )
    created_by: str = Field(..., description="User who created the ingestion")
    created_at: datetime = Field(None, description="Timestamp of ingestion creation")
    updated_at: datetime = Field(None, description="Timestamp of ingestion update")

    item: Union[Item, Json[Item]] = Field(..., description="STAC item to ingest")

    @validator("created_at", pre=True, always=True, allow_reuse=True)
    @validator("updated_at", pre=True, always=True, allow_reuse=True)
    def set_ts_now(cls, v):
        return v or datetime.now()

    def enqueue(self, db: "services.Database"):
        self.status = Status.queued
        return self.save(db)

    def cancel(self, db: "services.Database"):
        self.status = Status.cancelled
        return self.save(db)

    def save(self, db: "services.Database"):
        self.updated_at = datetime.now()
        db.write(self)
        return self

    def dynamodb_dict(self, by_alias=True):
        """DynamoDB-friendly serialization"""
        # convert to dictionary
        output = self.dict(exclude={"item"})

        # add STAC item as string
        output["item"] = self.item.json()

        # make JSON-friendly (will be able to do with Pydantic V2, https://github.com/pydantic/pydantic/issues/1409#issuecomment-1423995424)
        return jsonable_encoder(output)


class ListIngestionRequest(BaseModel):
    status: Status = Field(Status.queued, description="Status of the ingestion")
    limit: PositiveInt = Field(None, description="Limit number of results")
    next: Optional[str] = Field(None, description="Next token (json) to load")

    def __post_init_post_parse__(self) -> None:
        # https://github.com/tiangolo/fastapi/issues/1474#issuecomment-1049987786
        if self.next is None:
            return

        try:
            self.next = json.loads(base64.b64decode(self.next))
        except (UnicodeDecodeError, binascii.Error):
            raise RequestValidationError(
                [
                    error_wrappers.ErrorWrapper(
                        ValueError(
                            "Unable to decode next token. Should be base64 encoded JSON"
                        ),
                        "query.next",
                    )
                ]
            )


class ListIngestionResponse(BaseModel):
    items: List[Ingestion] = Field(
        ..., description="List of STAC items from ingestion."
    )
    next: Optional[str] = Field(None, description="Next token (json) to load")

    @validator("next", pre=True)
    def b64_encode_next(cls, next):
        """
        Base64 encode next parameter for easier transportability
        """
        if isinstance(next, dict):
            return base64.b64encode(json.dumps(next).encode())
        return next


class UpdateIngestionRequest(BaseModel):
    status: Status = Field(None, description="Status of the ingestion")
    message: str = Field(None, description="Message of the ingestion")
