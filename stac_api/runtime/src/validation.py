"""Middleware for validating transaction endpoints"""

import json
import re
from typing import Dict

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError, BaseModel, Field
from stac_pydantic import Item, Collection
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import ApiSettings


api_settings = ApiSettings()
prepend_path = api_settings.root_path or ""


class Items(BaseModel):
    """Validation model for items used in BulkItems"""

    items: Dict[str, Item]


class BulkItems(BaseModel):
    """Validation model for bulk-items endpoint request"""

    items: Items
    method: str = Field(default="insert")


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware that handles STAC collection and item validation in transaction endpoints"""

    async def dispatch(self, request: Request, call_next):
        """Middleware dispatch"""
        if request.method in ("POST", "PUT"):
            try:
                body = await request.body()
                request_data = json.loads(body)
                if re.match(
                    f"^{prepend_path}/collections(?:/[^/]+)?$",
                    request.url.path,
                ):
                    Collection(**request_data)
                elif re.match(
                    f"^{prepend_path}/collections/[^/]+/items(?:/[^/]+)?$",
                    request.url.path,
                ):
                    Item(**request_data)
                elif re.match(
                    f"^{prepend_path}/collections/[^/]+/bulk-items$",
                    request.url.path,
                ):
                    BulkItems(**request_data)
            except ValidationError as e:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Validation Error", "errors": e.errors()},
                )

        response = await call_next(request)
        return response
