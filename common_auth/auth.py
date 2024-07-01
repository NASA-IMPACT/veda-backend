"""Authentication handler for veda.stac and veda.ingest"""

import base64
import hashlib
import hmac
import logging
from typing import Annotated, Any, Dict

# import boto3
import jwt

from fastapi import Depends, HTTPException, Security, security, status
from pydantic.dataclasses import dataclass
logger = logging.getLogger(__name__)

@dataclass
class Auth:
    """Class for handling authentication"""
    
    authorization_url: str
    token_url: str
    refresh_url: str
    jwks_url: str

    @property
    def jwks_client(self):
        return jwt.PyJWKClient(self.jwks_url)

    @property
    def oauth2_scheme(self):
        return security.OAuth2AuthorizationCodeBearer(
            authorizationUrl=self.authorization_url,
            tokenUrl=self.token_url,
            refreshUrl=self.refresh_url,
        )

    @property
    def validated_token_depency(self):
        def validated_token(
            token_str: Annotated[str, Security(self.oauth2_scheme)],
            required_scopes: security.SecurityScopes,
        ) -> Dict:
            # Parse & validate token
            try:
                token = jwt.decode(
                    token_str,
                    self.jwks_client.get_signing_key_from_jwt(token_str).key,
                    algorithms=["RS256"],
                )
            except jwt.exceptions.InvalidTokenError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from e

            # Validate scopes (if required)
            for scope in required_scopes.scopes:
                if scope not in token["scope"]:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Not enough permissions",
                        headers={
                            "WWW-Authenticate": f'Bearer scope="{required_scopes.scope_str}"'
                        },
                    )

            return token

        return validated_token

    # def authenticate_and_get_token(
    #     self,
    #     username: str,
    #     password: str,
    #     user_pool_id: str,
    #     app_client_id: str,
    #     app_client_secret: str,
    # ) -> Dict:
    #     """Authenticates the credentials and returns token"""
    #     client = boto3.client("cognito-idp")
    #     if app_client_secret:
    #         auth_params = {
    #             "USERNAME": username,
    #             "PASSWORD": password,
    #             "SECRET_HASH": self._get_secret_hash(
    #                 username, app_client_id, app_client_secret
    #             ),
    #         }
    #     else:
    #         auth_params = {
    #             "USERNAME": username,
    #             "PASSWORD": password,
    #         }
    #     try:
    #         resp = client.admin_initiate_auth(
    #             UserPoolId=user_pool_id,
    #             ClientId=app_client_id,
    #             AuthFlow="ADMIN_USER_PASSWORD_AUTH",
    #             AuthParameters=auth_params,
    #         )
    #     except client.exceptions.NotAuthorizedException:
    #         return {
    #             "message": "Login failed, please make sure the credentials are correct."
    #         }
    #     except Exception as e:
    #         return {"message": f"Login failed with exception {e}"}
    #     return resp["AuthenticationResult"]
