import json
import re
from typing import Dict

from fastapi import Request, HTTPException
from pydantic import ValidationError, BaseModel, Field
from stac_pydantic import Item, Collection
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import ApiSettings


api_settings = ApiSettings()
prepend_path = api_settings.root_path or ""


class Items(BaseModel):
    items: Dict[str, Item]


class BulkItemsModel(BaseModel):
    items: Items
    method: str = Field(default="insert")


class ValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print("Request data", request)
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
                    BulkItemsModel(**request_data)
            except (ValidationError, json.JSONDecodeError) as e:
                raise HTTPException(status_code=400, detail=str(e))

        response = await call_next(request)
        return response
