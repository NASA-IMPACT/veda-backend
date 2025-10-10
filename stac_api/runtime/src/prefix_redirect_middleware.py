"""
Prefix Redirect Middleware

This middleware handles redirects to make sure that the root_path is preserved when
FastAPI handles automatic redirects

"""
import logging
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PrefixRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware that preserves root path for redirects"""

    async def dispatch(self, request, call_next):
        """Processes request and fixes redirect location headers"""
        resp = await call_next(request)

        if resp.status_code not in (301, 302, 303, 307, 308):
            return resp

        root_path = request.scope.get("root_path", "")
        if not root_path:
            return resp

        redirect_target = resp.headers.get("location")
        if not redirect_target:
            return resp

        parsed_target_url = urlparse(redirect_target)

        # Only alter redirect locations that match the request host
        if request.url.netloc != parsed_target_url.netloc:
            return resp

        redirect_path = parsed_target_url.path
        if (
            redirect_path.startswith("/")
            and not redirect_path.startswith(rp)
        ):
            resp.headers["location"] = root_path + stripped_path
            logger.debug(
                "Redirect location header changed from '%' to '%s'",
                redirect_target,
                resp.headers["location"],
            )

        return resp
