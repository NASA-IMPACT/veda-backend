"""veda custom algorithms"""

import math

import numpy
from rio_tiler.models import ImageData

from titiler.core.algorithm import Algorithms
from titiler.core.algorithm.base import BaseAlgorithm

# https://github.com/cogeotiff/rio-tiler/blob/master/rio_tiler/reader.py#L35-L37

# From eoAPI datasetparams edl_auth branch https://github.com/NASA-IMPACT/eoAPI/blob/edl_auth/src/eoapi/raster/eoapi/raster/datasetparams.py


class SWIR(BaseAlgorithm):
    """SWIR Custom Algorithm."""

    low_value: float = math.e
    high_value: float = 255
    low_threshold: float = math.log(1000)
    high_threshold: float = math.log(7500)

    def __call__(self, img: ImageData) -> ImageData:
        """Apply processing."""
        data = numpy.log(img.array)
        data[numpy.where(data <= self.low_threshold)] = self.low_value
        data[numpy.where(data >= self.high_threshold)] = self.high_value
        indices = numpy.where((data > self.low_value) & (data < self.high_value))
        data[indices] = (
            self.high_value
            * (data[indices] - self.low_threshold)
            / (self.high_threshold - self.low_threshold)
        )
        img.array = data.astype("uint8")
        return img


algorithms = Algorithms(
    {
        "swir": SWIR,
    }
)

PostProcessParams = algorithms.dependency
