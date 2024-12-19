"""Custom search models"""
from datetime import datetime as dt
from typing import Dict, Optional, Union

import attr
from geojson_pydantic.geometries import (  # type: ignore
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    _GeometryBase,
)
from pydantic import BaseModel, field_validator
from stac_pydantic.shared import BBox

from stac_fastapi.types.rfc3339 import rfc3339_str_to_datetime, str_to_interval
from stac_fastapi.types.search import APIRequest, str2list

Intersection = Union[
    Point,
    MultiPoint,
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    GeometryCollection,
]


class CollectionSearchPost(BaseModel):
    """
    The class for STAC API collection searches.
    """

    bbox: Optional[BBox] = None
    intersects: Optional[Intersection] = None
    datetime: Optional[str] = None
    conf: Optional[Dict] = None

    @property
    def start_date(self) -> Optional[dt]:
        """Extract the start date from the datetime string."""
        interval = str_to_interval(self.datetime)
        return interval[0] if interval else None

    @property
    def end_date(self) -> Optional[dt]:
        """Extract the end date from the datetime string."""
        interval = str_to_interval(self.datetime)
        return interval[1] if interval else None

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @field_validator("intersects")
    def validate_spatial(cls, v, values):
        """Check bbox and intersects are not both supplied."""
        if v and values["bbox"]:
            raise ValueError("intersects and bbox parameters are mutually exclusive")
        return v

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: BBox):
        """Check order of supplied bbox coordinates."""
        if v:
            # Validate order
            if len(v) == 4:
                xmin, ymin, xmax, ymax = v
            else:
                xmin, ymin, min_elev, xmax, ymax, max_elev = v
                if max_elev < min_elev:
                    raise ValueError(
                        "Maximum elevation must greater than minimum elevation"
                    )

            if xmax < xmin:
                raise ValueError(
                    "Maximum longitude must be greater than minimum longitude"
                )

            if ymax < ymin:
                raise ValueError(
                    "Maximum longitude must be greater than minimum longitude"
                )

            # Validate against WGS84
            if xmin < -180 or ymin < -90 or xmax > 180 or ymax > 90:
                raise ValueError("Bounding box must be within (-180, -90, 180, 90)")

        return v

    @field_validator("datetime")
    @classmethod
    def validate_datetime(cls, v):
        """Validate datetime."""
        if "/" in v:
            values = v.split("/")
        else:
            # Single date is interpreted as end date
            values = ["..", v]

        dates = []
        for value in values:
            if value == ".." or value == "":
                dates.append("..")
                continue

            # throws ValueError if invalid RFC 3339 string
            dates.append(rfc3339_str_to_datetime(value))

        if dates[0] == ".." and dates[1] == "..":
            raise ValueError(
                "Invalid datetime range, both ends of range may not be open"
            )

        if ".." not in dates and dates[0] > dates[1]:
            raise ValueError(
                "Invalid datetime range, must match format (begin_date, end_date)"
            )

        return v

    @property
    def spatial_filter(self) -> Optional[_GeometryBase]:
        """Return a geojson-pydantic object representing the spatial filter for the search request.
        Check for both because the ``bbox`` and ``intersects`` parameters are mutually exclusive.
        """
        if self.bbox:
            return Polygon(
                coordinates=[
                    [
                        [self.bbox[0], self.bbox[3]],
                        [self.bbox[2], self.bbox[3]],
                        [self.bbox[2], self.bbox[1]],
                        [self.bbox[0], self.bbox[1]],
                        [self.bbox[0], self.bbox[3]],
                    ]
                ]
            )
        if self.intersects:
            return self.intersects
        return None


@attr.s
class CollectionSearchGet(APIRequest):
    """Base arguments for GET Request."""

    bbox: Optional[str] = attr.ib(default=None, converter=str2list)  # type: ignore
    intersects: Optional[str] = attr.ib(default=None, converter=str2list)  # type: ignore
    datetime: Optional[str] = attr.ib(default=None)
