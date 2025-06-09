# from typing import Any, Dict

# from typing_extensions import Annotated

# from fastapi import Depends

# from eoapi.auth_utils import OpenIdConnectAuth, OpenIdConnectSettings

# auth_settings = OpenIdConnectSettings(_env_prefix="")
# print(auth_settings)

# oidc_auth = OpenIdConnectAuth(
#     openid_configuration_url=auth_settings.openid_configuration_url,
#     allowed_jwt_audiences="account",
# )


# def get_username(
#     token: Annotated[Dict[Any, Any], Depends(oidc_auth.valid_token_dependency)],
# ) -> str:
#     result = (
#         token["preferred_username"]
#         if "preferred_username" in token
#         else str(token.get("sub"))
#     )
#     return result


import os
from typing import Any, Dict

from typing_extensions import Annotated

from fastapi import Depends

from eoapi.auth_utils import OpenIdConnectAuth, OpenIdConnectSettings

from dataclasses import dataclass



# Check if we're in development mode
IS_DEV = os.getenv("DEV_MODE", "false").lower() == "true"

if not IS_DEV:
    # Production: use real auth
    auth_settings = OpenIdConnectSettings(_env_prefix="")
    oidc_auth = OpenIdConnectAuth(
        openid_configuration_url=auth_settings.openid_configuration_url,
        allowed_jwt_audiences="account",
    )
else:
    # Development: create a mock auth object
    @dataclass
    class Auth_Setting:
        client_id = 12345
    
    class MockAuth:
        def valid_token_dependency(self):
            return {
                "preferred_username": "dev-user",
                "sub": "dev-user-id",
                "email": "dev-user@example.com",
                "roles": ["user"]
            }
    
    oidc_auth = MockAuth()
    auth_settings = Auth_Setting()

def get_username(
    token: Annotated[Dict[Any, Any], Depends(oidc_auth.valid_token_dependency)],
) -> str:
    result = (
        token["preferred_username"]
        if "preferred_username" in token
        else str(token.get("sub"))
    )
    return result
