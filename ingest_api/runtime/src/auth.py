from typing import Any, Dict

from typing_extensions import Annotated

from fastapi import Depends

from eoapi.auth_utils import OpenIdConnectAuth, OpenIdConnectSettings

auth_settings = OpenIdConnectSettings(_env_prefix="STAC_")

oidc_auth = OpenIdConnectAuth(
    openid_configuration_url=auth_settings.openid_configuration_url,
)


def get_username(
    token: Annotated[Dict[Any, Any], Depends(oidc_auth.valid_token_dependency)],
) -> str:
    result = token["username"] if "username" in token else str(token.get("sub"))
    return result
