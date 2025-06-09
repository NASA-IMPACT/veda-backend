"""Middleware to handle tenant filtering in STAC URLs."""

import json
from typing import Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp


class TenantFilteringMiddleware(BaseHTTPMiddleware):
    """Middleware to extract tenant from URL and apply filtering."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Process request and apply tenant filtering."""
        
        # Extract tenant from URL path
        path_parts = request.url.path.split('/')
        tenant = None
        
        # Check if URL matches pattern /stac/{tenant}/...
        if len(path_parts) >= 3 and path_parts[1] == 'stac':
            tenant = path_parts[2]
            
            # Store tenant in request state for later use
            request.state.tenant_filter = tenant
            
            # Modify the path to remove tenant part for upstream processing
            # /stac/ghg/collections -> /collections
            new_path = '/' + '/'.join(path_parts[3:]) if len(path_parts) > 3 else '/'
            
            # Update request scope with modified path
            scope = request.scope.copy()
            scope['path'] = new_path
            scope['raw_path'] = new_path.encode()
            
            # Create new request with modified scope
            modified_request = Request(scope, request.receive)
            
            # Add tenant filter to query parameters for GET requests
            if request.method == "GET" and "collections" in new_path:
                # Modify query params to include tenant filter
                query_params = dict(request.query_params)
                query_params['tenant'] = tenant
                
                # Update query string
                from urllib.parse import urlencode
                new_query = urlencode(query_params)
                scope['query_string'] = new_query.encode()
                modified_request = Request(scope, request.receive)
            
            # For POST requests (search), modify the body
            elif request.method == "POST" and ("search" in new_path or new_path.endswith('/search')):
                # Read and modify request body
                body = await request.body()
                if body:
                    try:
                        search_data = json.loads(body.decode())
                        
                        # Add tenant filter to search
                        if 'filter' not in search_data:
                            search_data['filter'] = {}
                        
                        # Add tenant filter (adjust based on your filter implementation)
                        search_data['filter']['tenant'] = tenant
                        
                        # Create new body
                        modified_body = json.dumps(search_data).encode()
                        
                        # Create new receive function with modified body
                        async def receive():
                            return {
                                "type": "http.request",
                                "body": modified_body,
                                "more_body": False
                            }
                        
                        modified_request = Request(scope, receive)
                    except json.JSONDecodeError:
                        # If body is not valid JSON, proceed with original request
                        modified_request = Request(scope, request.receive)
            
            # Process the modified request
            response = await call_next(modified_request)
            
            # Post-process response if needed (e.g., filter collections)
            if request.method == "GET" and "collections" in request.url.path:
                response = await self._filter_collections_response(response, tenant)
            
            return response
        
        # If no tenant in URL, proceed normally
        return await call_next(request)
    
    async def _filter_collections_response(self, response: Response, tenant: str) -> Response:
        """Filter collections in response by tenant."""
        
        if response.status_code != 200:
            return response
        
        try:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Parse JSON response
            data = json.loads(body.decode())
            
            # Filter collections by tenant
            if 'collections' in data:
                filtered_collections = []
                for collection in data['collections']:
                    if collection.get('tenant') == tenant:
                        filtered_collections.append(collection)
                
                data['collections'] = filtered_collections
                
                # Update collection count if present
                if 'numberReturned' in data:
                    data['numberReturned'] = len(filtered_collections)
            
            # Return filtered response
            return JSONResponse(
                content=data,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except (json.JSONDecodeError, UnicodeDecodeError):
            # If response is not JSON, return original
            return response


# Usage in your main app file:
# Add this middleware to your app
# app.add_middleware(TenantFilteringMiddleware)
