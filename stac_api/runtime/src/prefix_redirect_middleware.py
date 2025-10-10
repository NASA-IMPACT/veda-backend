"""
Prefix Redirect Middleware

This middleware handles redirects to make sure that the root_path is preserved when
FastAPI handles automatic redirects

"""
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware


class PrefixRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware that preserves root path for redirects"""

    async def dispatch(self, request, call_next):
        """Processes request and fixes redirect location headers"""
        resp = await call_next(request)

        if resp.status_code not in (301, 302, 303, 307, 308):
            return resp

        loc = resp.headers.get("location")
        if not loc:
            return resp

        try:
            parsed_request_url = urlparse(str(request.url))
            parsed_response_url = urlparse(loc)

            print(f"{parsed_request_url=}")
            print(f"{parsed_response_url=}")

            # Check if response host is the same as redirect host
            if parsed_request_url.netloc == parsed_response_url.netloc:
                # If so, strip the host from response location
                parsed_location = urlparse(loc)
                stripped_path = parsed_location.path
                print(f"{stripped_path=}")

                rp = request.scope.get("root_path", "")
                print(f"{rp=}", flush=True)

                if (
                    stripped_path
                    and stripped_path.startswith("/")
                    and rp
                    and not stripped_path.startswith(rp)
                ):

                    print(f"Before: {resp.headers['location']}")
                    resp.headers["location"] = rp + stripped_path
                    print(f"After: {resp.headers['location']}")

        except Exception as e:
            print(f"Error processing redirect: {e}")

        return resp
