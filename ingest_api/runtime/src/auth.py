from typing import Any, Dict

from typing_extensions import Annotated

from fastapi import Depends

from eoapi.auth_utils import OpenIdConnectAuth, OpenIdConnectSettings

auth_settings = OpenIdConnectSettings(_env_prefix="")

oidc_auth = OpenIdConnectAuth(
    openid_configuration_url=auth_settings.openid_configuration_url,
    allowed_jwt_audiences="account",
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
