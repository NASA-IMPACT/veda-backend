from typing import Any, Dict

from typing_extensions import Annotated

from src.config import VedaOpenIdConnectSettings
from fastapi import Depends

from eoapi.auth_utils import OpenIdConnectAuth

auth_settings = VedaOpenIdConnectSettings()

oidc_auth = OpenIdConnectAuth(
    openid_configuration_url=auth_settings.openid_configuration_url,
)


def get_username(
    token: Annotated[Dict[Any, Any], Depends(oidc_auth.valid_token_dependency)],
) -> str:
    result = (
        token["preferred_username"]
        if "preferred_username" in token
        else str(token.get("sub"))
    )
    return result
