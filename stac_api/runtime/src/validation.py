import json
import re

from fastapi import Request, HTTPException
from pydantic import parse_obj_as, ValidationError
from stac_pydantic import Item, Collection
from starlette.middleware.base import BaseHTTPMiddleware


class ValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT"):
            try:
                body = await request.body()
                request_data = json.loads(body)
                if re.match(r"^/collections(?:/[^/]+)?$", request.url.path):
                    Collection(**request_data)
                elif re.match(
                    r"^/collections/[^/]+/items(?:/[^/]+)?$", request.url.path
                ):
                    Item(**request_data)
                elif re.match(r"^/collections/[^/]+/bulk-items$", request.url.path):
                    parse_obj_as(list[Item], request_data)
            except (ValidationError, json.JSONDecodeError) as e:
                raise HTTPException(status_code=400, detail=str(e))

        response = await call_next(request)
        return response
