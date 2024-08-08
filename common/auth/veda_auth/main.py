"""Authentication handler for veda.stac and veda.ingest"""

import base64
import hashlib
import hmac
import logging
from typing import Annotated, Any, Dict

import boto3
import jwt

from fastapi import Depends, HTTPException, Security, security, status

logger = logging.getLogger(__name__)


class VedaAuth:
    """Class for handling authentication"""

    def __init__(self, settings) -> None:
        """
        Args:
            settings: pydantic settings object containing cognito details
        Returns:
            None

        """
        self.oauth2_scheme = security.OAuth2AuthorizationCodeBearer(
            authorizationUrl=settings.cognito_authorization_url,
            tokenUrl=settings.cognito_token_url,
            refreshUrl=settings.cognito_token_url,
        )

        self.jwks_client = jwt.PyJWKClient(settings.jwks_url)  # Caches JWKS

        def validated_token(
            token_str: Annotated[str, Security(self.oauth2_scheme)],
            required_scopes: security.SecurityScopes,
        ) -> Dict:
            # Parse & validate token
            logger.info(f"\nToken String {token_str}")
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

        self.validated_token = validated_token

        def get_username(
            token: Annotated[Dict[Any, Any], Depends(self.validated_token)]
        ) -> str:
            result = token["username"] if "username" in token else str(token.get("sub"))
            return result

        self.get_username = get_username

    def _get_secret_hash(
        self, username: str, client_id: str, client_secret: str
    ) -> str:
        # A keyed-hash message authentication code (HMAC) calculated using
        # the secret key of a user pool client and username plus the client
        # ID in the message.
        message = username + client_id
        dig = hmac.new(
            bytearray(client_secret, "utf-8"),
            msg=message.encode("UTF-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(dig).decode()

    def authenticate_and_get_token(
        self,
        username: str,
        password: str,
        user_pool_id: str,
        app_client_id: str,
        app_client_secret: str,
    ) -> Dict:
        """Authenticates the credentials and returns token"""
        client = boto3.client("cognito-idp")
        if app_client_secret:
            auth_params = {
                "USERNAME": username,
                "PASSWORD": password,
                "SECRET_HASH": self._get_secret_hash(
                    username, app_client_id, app_client_secret
                ),
            }
        else:
            auth_params = {
                "USERNAME": username,
                "PASSWORD": password,
            }
        try:
            resp = client.admin_initiate_auth(
                UserPoolId=user_pool_id,
                ClientId=app_client_id,
                AuthFlow="ADMIN_USER_PASSWORD_AUTH",
                AuthParameters=auth_params,
            )
        except client.exceptions.NotAuthorizedException:
            return {
                "message": "Login failed, please make sure the credentials are correct."
            }
        except Exception as e:
            return {"message": f"Login failed with exception {e}"}
        return resp["AuthenticationResult"]
