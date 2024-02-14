import base64
import hashlib
import hmac
import logging
from typing import Dict

import boto3
import requests
import src.config as config
from authlib.jose import JsonWebKey, JsonWebToken, JWTClaims, KeySet, errors
from cachetools import TTLCache, cached

from fastapi import Depends, HTTPException, security

logger = logging.getLogger(__name__)

token_scheme = security.HTTPBearer()


def get_settings() -> config.Settings:
    import src.main as main

    return main.settings


def get_jwks_url(settings: config.Settings = Depends(get_settings)) -> str:
    return settings.jwks_url


@cached(TTLCache(maxsize=1, ttl=3600))
def get_jwks(jwks_url: str = Depends(get_jwks_url)) -> KeySet:
    with requests.get(jwks_url) as response:
        response.raise_for_status()
        return JsonWebKey.import_key_set(response.json())


def decode_token(
    token: security.HTTPAuthorizationCredentials = Depends(token_scheme),
    jwks: KeySet = Depends(get_jwks),
) -> JWTClaims:
    """
    Validate & decode JWT
    """
    try:
        claims = JsonWebToken(["RS256"]).decode(
            s=token.credentials,
            key=jwks,
            claims_options={
                # # Example of validating audience to match expected value
                # "aud": {"essential": True, "values": [APP_CLIENT_ID]}
            },
        )

        if "client_id" in claims:
            # Insert Cognito's `client_id` into `aud` claim if `aud` claim is unset
            claims.setdefault("aud", claims["client_id"])

        claims.validate()
        return claims
    except errors.JoseError:  #
        logger.exception("Unable to decode token")
        raise HTTPException(status_code=403, detail="Bad auth token")


def get_username(claims: security.HTTPBasicCredentials = Depends(decode_token)):
    return claims["sub"]


def _get_secret_hash(username: str, client_id: str, client_secret: str) -> str:
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
    username: str,
    password: str,
    user_pool_id: str,
    app_client_id: str,
    app_client_secret: str,
) -> Dict:
    client = boto3.client("cognito-idp")
    if app_client_secret:
        auth_params = {
            "USERNAME": username,
            "PASSWORD": password,
            "SECRET_HASH": _get_secret_hash(username, app_client_id, app_client_secret),
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
