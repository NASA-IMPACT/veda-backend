"""Stac Viewer Extension."""

from dataclasses import dataclass

import jinja2

from fastapi import Depends
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from titiler.core.factory import BaseTilerFactory, FactoryExtension

DEFAULT_TEMPLATES = Jinja2Templates(
    directory="",
    loader=jinja2.ChoiceLoader([jinja2.PackageLoader(__package__, "templates")]),
)  # type:ignore


@dataclass
class stacViewerExtension(FactoryExtension):
    """Add /viewer endpoint to the TilerFactory."""

    templates: Jinja2Templates = DEFAULT_TEMPLATES

    def register(self, factory: BaseTilerFactory):
        """Register endpoint to the tiler factory."""

        @factory.router.get("/viewer", response_class=HTMLResponse)
        def stac_viewer(
            request: Request,
            item=Depends(factory.path_dependency),
        ):
            """STAC Viewer."""
            return self.templates.TemplateResponse(
                name="stac-viewer.html",
                context={
                    "request": request,
                    "endpoint": request.url.path.replace("/viewer", ""),
                    "collection": item.collection_id,
                    "item": item.id,
                },
                media_type="text/html",
            )
