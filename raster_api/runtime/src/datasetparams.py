"""From eoAPI datasetparams edl_auth branch https://github.com/NASA-IMPACT/eoAPI/blob/edl_auth/src/eoapi/raster/eoapi/raster/datasetparams.py"""
import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy

from fastapi import Query
from titiler.core import dependencies

# https://github.com/cogeotiff/rio-tiler/blob/master/rio_tiler/reader.py#L35-L37

# From eoAPI datasetparams edl_auth branch https://github.com/NASA-IMPACT/eoAPI/blob/edl_auth/src/eoapi/raster/eoapi/raster/datasetparams.py


def swir(data, mask) -> Tuple[numpy.ndarray, numpy.ndarray]:
    """SWIR"""
    low_value = math.e
    high_value = 255

    low_threshold = math.log(1000)
    high_threshold = math.log(7500)

    data = numpy.log(data)
    data[numpy.where(data <= low_threshold)] = low_value
    data[numpy.where(data >= high_threshold)] = high_value
    indices = numpy.where((data > low_value) & (data < high_value))
    data[indices] = (
        high_value * (data[indices] - low_threshold) / (high_threshold - low_threshold)
    )
    return data.astype("uint8"), mask


pp_methods = {
    "swir": swir,
}


@dataclass
class DatasetParams(dependencies.DatasetParams):
    """Post processing parameters for map layers"""

    post_process: Optional[str] = Query(None, description="Post Process Name.")

    def __post_init__(self):
        """."""
        super().__post_init__()

        if self.post_process is not None:
            self.post_process = pp_methods.get(self.post_process)  # type: ignore
