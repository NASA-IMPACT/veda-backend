from datetime import datetime
from typing import List, Union

from pydantic import BaseModel, model_validator
from stac_pydantic.collection import Extent, TimeInterval

# Smaller utility models to support the larger models in schemas.py


class DatetimeInterval(TimeInterval):
    # reimplement stac_pydantic's TimeInterval to leverage datetime types
    interval: List[List[Union[datetime, None]]]


class SpatioTemporalExtent(Extent):
    # reimplement stac_pydantic's Extent to leverage datetime types
    temporal: DatetimeInterval


# TODO we should make these more consistent with stac_pydantic's existing models
class BboxExtent(BaseModel):
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @model_validator(mode="before")
    def check_extent(cls, v):
        # mins must be below maxes
        if v["xmin"] >= v["xmax"] or v["ymin"] >= v["ymax"]:
            raise ValueError(
                "Invalid extent - xmin must be less than xmax, ymin less than ymax"
            )
        # ys must be within -90 and 90, x between -180 and 180
        if v["xmin"] < -180 or v["xmax"] > 180 or v["ymin"] < -90 or v["ymax"] > 90:
            raise ValueError(
                "Invalid extent - coordinates must be within -180, 180 and -90, 90"
            )
        return v


class TemporalExtent(BaseModel):
    startdate: Union[datetime, None] = None
    enddate: Union[datetime, None] = None

    @model_validator(mode="before")
    def check_dates(cls, v):
        if (v["enddate"] is not None) and (v["startdate"] >= v["enddate"]):
            raise ValueError("Invalid extent - startdate must be before enddate")
        return v
