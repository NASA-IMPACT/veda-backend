"""This module contains functions and classes for defining titiler rendering query parameters STAC items."""
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import orjson
from pydantic import BaseModel


def orjson_dumps(v: Dict[str, Any], *args: Any, default: Any) -> str:
    """orjson.dumps returns bytes, to match standard json.dumps we need to decode."""
    return orjson.dumps(v, default=default).decode()


def get_param_str(params: Dict[str, Any]) -> str:
    """Get parameter string from a dictionary of parameters."""
    for k, v in params.items():
        if k == "colormap":
            params[k] = json.dumps(v)  # colormap needs to be json encoded
        elif k == "rescale":
            params[k] = [",".join([str(j) for j in i]) for i in v]

    return urlencode(params, True)


class RenderConfig(BaseModel):
    """
    A class used to represent information convenient for accessing
    the rendered assets of a collection.

    The parameters stored by this class are not the only parameters
    by which rendering is possible or useful but rather represent the
    most convenient renderings for human consumption and preview.
    For example, if a TIF asset can be viewed as an RGB approximating
    normal human vision, parameters will likely encode this rendering.
    """

    render_params: Dict[str, Any] = {}
    minzoom: int = 14
    assets: Optional[List[str]] = ["cog_default"]
    maxzoom: Optional[int] = 30
    mosaic_preview_zoom: Optional[int] = None
    mosaic_preview_coords: Optional[List[float]] = None

    def get_full_render_qs(self) -> str:
        """
        Return the full render query string including render and assets parameters.
        """
        return self.get_render_params()

    def get_render_params(self) -> str:
        """Get the render parameters as a query string."""
        params = self.render_params.copy()
        return f"{get_param_str(params)}"

    class Config:
        """Pydantic config class for RenderConfig."""

        json_loads = orjson.loads
        json_dumps = orjson_dumps


def get_render_config(render_params) -> RenderConfig:
    """This is a placeholder for what may be a more complex function in the future.
    As of now, it isn't clear how we should get this rendering information as it should
    likely be sourced from the dashboard's configuration."""
    return RenderConfig(render_params=render_params)
