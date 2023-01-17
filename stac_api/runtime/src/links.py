"""A module for injecting links to STAC entries"""
from typing import Any, Dict
from urllib.parse import urljoin

import pystac

from fastapi import Request
from stac_fastapi.types.stac import Collection, Item

from .config import tiles_settings
from .render import get_render_config


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
        request: Request,
    ) -> None:
        """Initialize a LinkInjector"""
        self.collection_id = collection_id
        # The collection_id should be suitable for getting a RenderConfig with more details
        self.render_config = get_render_config()
        self.tiler_href = tiles_settings.titiler_endpoint or ""

    def inject_collection(self, collection: Collection) -> None:
        """Inject rendering links to a collection"""
        collection.get("links", []).append(self._get_collection_map_link())

        collection["links"] = collection.get("links", [])
        if tiles_settings.titiler_endpoint:
            collection["links"].append(self._get_collection_tilejson_link())

    def inject_item(self, item: Item) -> None:
        """Inject rendering links to an item"""
        item_id = item.get("id", "")
        item["links"] = item.get("links", [])
        if tiles_settings.titiler_endpoint:
            item["links"].append(self._get_item_map_link(item_id))
            item["links"].append(self._get_item_wmts_link(item_id))
            item["links"].append(self._get_item_tilejson_link(item_id))
            item["links"].append(self._get_item_preview_link(item_id))

    def _get_collection_tilejson_link(self) -> Dict[str, Any]:
        qs = self.render_config.get_full_render_qs(self.collection_id)
        href = urljoin(self.tiler_href, f"collection/tilejson.json?{qs}")

        return {
            "title": "Mosaic TileJSON with default rendering",
            "href": href,
            "type": pystac.MediaType.JSON,
            "roles": ["tiles"],
        }

    def _get_collection_map_link(self) -> Dict[str, Any]:
        href = urljoin(
            self.tiler_href,
            f"collection/map?collection={self.collection_id}",
        )

        return {
            "title": "Map of collection mosaic",
            "href": href,
            "type": "text/html",
            "rel": pystac.RelType.PREVIEW,
        }

    def _get_item_preview_link(self, item_id: str) -> Dict[str, Any]:
        qs = self.render_config.get_full_render_qs(self.collection_id, item_id)
        href = urljoin(self.tiler_href, f"item/preview.png?{qs}")

        return {
            "title": "Rendered preview",
            "href": href,
            "rel": "preview",
            "roles": ["overview"],
            "type": pystac.MediaType.PNG,
        }

    def _get_item_tilejson_link(self, item_id: str) -> Dict[str, Any]:
        qs = self.render_config.get_full_render_qs(self.collection_id, item_id)
        href = urljoin(self.tiler_href, f"item/tilejson.json?{qs}")

        return {
            "title": "TileJSON with default rendering",
            "href": href,
            "type": pystac.MediaType.JSON,
            "roles": ["tiles"],
        }

    def _get_item_map_link(self, item_id: str) -> Dict[str, Any]:
        href = urljoin(
            self.tiler_href,
            f"item/map?collection={self.collection_id}&item={item_id}",
        )

        return {
            "title": "Map of item",
            "href": href,
            "rel": pystac.RelType.PREVIEW,
            "type": "text/html",
        }

    def _get_item_wmts_link(self, item_id: str) -> Dict[str, Any]:
        qs = self.render_config.get_full_render_qs_raw(self.collection_id, item_id)
        href = urljoin(
            self.tiler_href,
            f"item/WebMercatorQuad/WMTSCapabilities.xml?{qs}",
        )

        return {
            "title": "WMTS capabilities for item",
            "href": href,
            "rel": "WMTS",
            "type": "text/xml",
        }
