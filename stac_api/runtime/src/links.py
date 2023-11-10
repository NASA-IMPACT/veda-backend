"""A module for injecting links to STAC entries"""
from typing import Any, Dict
from urllib.parse import urljoin

import pystac

from fastapi import Request
from stac_fastapi.types.stac import Item

from src.config import TilesApiSettings
from .render import get_render_config

tiles_settings = TilesApiSettings()


class LinkInjector:
    """
    A class which organizes information relating STAC entries
    to endpoints which render associated assets. Used to inject
    links from catalog entries to tiling endpoints

    ...

    Attributes
    ----------
    collection_id : str
        The ID of a STAC Collection in the PC
    """

    def __init__(
        self,
        collection_id: str,
        render_params: Dict[str, Any],
        request: Request,
    ) -> None:
        """Initialize a LinkInjector"""

        render_params = render_params.get("dashboard", {})
        render_params.pop("title", render_params)

        self.collection_id = collection_id
        self.render_config = get_render_config(render_params)
        self.tiler_href = tiles_settings.titiler_endpoint or ""

    def inject_item(self, item: Item) -> None:
        """Inject rendering links to an item"""
        item_id = item.get("id", "")
        item["links"] = item.get("links", [])
        if self.tiler_href:
            item["links"].append(self._get_item_map_link(item_id))
            item["assets"]["rendered_preview"] = self._get_item_preview_link(item_id)

    def _get_item_map_link(self, item_id: str) -> Dict[str, Any]:
        qs = self.render_config.get_full_render_qs(self.collection_id, item_id)
        href = urljoin(self.tiler_href, f"stac/map?{qs}")

        return {
            "title": "Map of Item",
            "href": href,
            "rel": "preview",
            "type": "text/html"
        }

    def _get_item_preview_link(self, item_id: str) -> Dict[str, Any]:
        qs = self.render_config.get_full_render_qs(self.collection_id, item_id)
        href = urljoin(self.tiler_href, f"stac/preview.png?{qs}")

        return {
            "title": "Rendered preview",
            "href": href,
            "rel": "preview",
            "roles": ["overview"],
            "type": pystac.MediaType.PNG,
        }