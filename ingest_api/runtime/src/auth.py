from typing import Annotated, Any

from eoapi.auth_utils import OpenIdConnectAuth, OpenIdConnectSettings
from fastapi import Depends

auth_settings = OpenIdConnectSettings(_env_prefix="")

oidc_auth = OpenIdConnectAuth(
    openid_configuration_url=auth_settings.openid_configuration_url,
    allowed_jwt_audiences="account",
)


def get_username(
    token: Annotated[dict[Any, Any], Depends(oidc_auth.valid_token_dependency)],
) -> str:
    return (
        token["preferred_username"]
        if "preferred_username" in token
        else str(token.get("sub"))
    )
