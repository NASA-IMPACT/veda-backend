"""A module for injecting links to STAC entries"""
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import pystac
from src.config import TENANT_ITEM_LINK_TEMPLATES, TilesApiSettings

from fastapi import Request
from stac_fastapi.types.stac import Item

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
        tenant: Optional[str] = None,
    ) -> None:
        """Initialize a LinkInjector"""

        render_params.pop("title", render_params)

        self.collection_id = collection_id
        self.render_config = get_render_config(render_params)
        self.tiler_href = tiles_settings.titiler_endpoint or ""
        self.tenant = tenant

    def inject_item(self, item: Item) -> None:
        """Inject rendering links to an item"""
        item_id = item.get("id", "")
        item["links"] = item.get("links", [])
        if self.tiler_href:
            item["links"].append(self._get_item_map_link(item_id, self.collection_id))
            item["assets"]["rendered_preview"] = self._get_item_preview_link(
                item_id, self.collection_id
            )

        # If tenant is provided, add tenant links
        if self.tenant:
            self._inject_tenant_links(item, item_id)

    def _get_item_map_link(self, item_id: str, collection_id: str) -> Dict[str, Any]:
        qs = self.render_config.get_full_render_qs()
        href = urljoin(
            self.tiler_href,
            f"collections/{collection_id}/items/{item_id}/WebMercatorQuad/map?{qs}",
        )

        return {
            "title": "Map of Item",
            "href": href,
            "rel": "preview",
            "type": "text/html",
        }

    def _get_item_preview_link(
        self, item_id: str, collection_id: str
    ) -> Dict[str, Any]:
        qs = self.render_config.get_full_render_qs()
        href = urljoin(
            self.tiler_href,
            f"collections/{collection_id}/items/{item_id}/preview.png?{qs}",
        )

        return {
            "title": "Rendered preview",
            "href": href,
            "rel": "preview",
            "roles": ["overview"],
            "type": pystac.MediaType.PNG,
        }

    def _inject_tenant_links(self, item: Item, item_id: str) -> None:
        """Inject tenant links to an item"""
        tenant_links = self._build_tenant_item_links(item_id)
        item["links"].extend(tenant_links)

    def _build_tenant_item_links(self, item_id: str) -> list:
        """Build tenant links for an item using tenant item link template"""
        if not self.tenant:
            return []

        tenant_links = []

        for template in TENANT_ITEM_LINK_TEMPLATES:
            link = {
                "rel": template["rel"],
                "type": template["type"],
                "href": template["href_template"].format(
                    tenant=self.tenant,
                    item_id=item_id,
                    collection_id=self.collection_id,
                ),
            }
            tenant_links.append(link)

        return tenant_links
