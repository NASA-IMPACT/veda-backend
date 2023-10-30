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
        if isinstance(v, (dict, list)):
            params[k] = json.dumps(v)  # colormap needs to be json encoded
    return urlencode(params)


def get_param_str_raw(params: Dict[str, Any]) -> str:
    """Get unescaped parameter string from a dictionary of parameters."""
    parts = []
    for k, v in params.items():
        if isinstance(v, list):
            for v2 in v:
                parts.append(f"{k}={str(v2)}")
        else:
            parts.append(f"{k}={str(v)}")

    return "&".join(parts)


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

    def get_full_render_qs(self, collection: str, item: Optional[str] = None) -> str:
        """
        Return the full render query string, including the
        item, collection, render and assets parameters.
        """
        collection_part = f"collection={collection}" if collection else ""
        item_part = f"&item={item}" if item else ""
        asset_part = self.get_assets_params()
        render_part = self.get_render_params()

        return "".join([collection_part, item_part, asset_part, render_part])

    def get_full_render_qs_raw(
        self, collection: str, item: Optional[str] = None
    ) -> str:
        """
        Return the full render query string, including the
        item, collection, render and assets parameters.
        """
        collection_part = f"collection={collection}" if collection else ""
        item_part = f"&item={item}" if item else ""
        asset_part = self.get_assets_params()
        render_part = self.get_render_params_raw()

        return "".join([collection_part, item_part, asset_part, render_part])

    def get_assets_params(self) -> str:
        """
        Convert listed assets to a query string format with multiple `asset` keys
            None -> ""
            [data1] -> "&asset=data1"
            [data1, data2] -> "&asset=data1&asset=data2"
        """
        assets = self.assets or []
        keys = ["&assets="] * len(assets)
        params = ["".join(item) for item in zip(keys, assets)]

        return "".join(params)

    def get_render_params_raw(self) -> str:
        """Get the render parameters as a query string (raw)."""
        return f"&{get_param_str_raw(self.render_params)}"

    def get_render_params(self) -> str:
        """Get the render parameters as a query string."""
        return f"&{get_param_str(self.render_params)}"

    class Config:
        """Pydantic config class for RenderConfig."""

        json_loads = orjson.loads
        json_dumps = orjson_dumps


def get_render_config(render_params) -> RenderConfig:
    """This is a placeholder for what may be a more complex function in the future.
    As of now, it isn't clear how we should get this rendering information as it should
    likely be sourced from the dashboard's configuration."""
    return RenderConfig(render_params=render_params)
