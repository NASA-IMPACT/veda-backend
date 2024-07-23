"""Middleware for validating transaction endpoints"""

import json
import re
from typing import Dict

from pydantic import BaseModel, Field, ValidationError
from src.config import api_settings

from pystac import STACObjectType
from pystac.validation import validate_dict
from pystac.errors import STACValidationError

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

path_prefix = api_settings.root_path or ""


class BulkItems(BaseModel):
    """Validation model for bulk-items endpoint request"""

    items: Dict[str, dict]
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
                    f"^{path_prefix}/collections(?:/[^/]+)?$",
                    request.url.path,
                ):
                    validate_dict(request_data, STACObjectType.COLLECTION)
                elif re.match(
                    f"^{path_prefix}/collections/[^/]+/items(?:/[^/]+)?$",
                    request.url.path,
                ):
                    validate_dict(request_data, STACObjectType.ITEM)
                elif re.match(
                    f"^{path_prefix}/collections/[^/]+/bulk-items$",
                    request.url.path,
                ):
                    bulk_items = BulkItems(**request_data)
                    for item_data in bulk_items.items.items.values():
                        validate_dict(item_data, STACObjectType.ITEM)
            except STACValidationError as e:
                return JSONResponse(
                    status_code=422,
                    content={"detail": "Validation Error", "errors": str(e)},
                )

        response = await call_next(request)
        return response
