"""Policy Enforcement Point Authorization Middleware for Ingest API

This module provides PEP middleware integration for the Ingest API"""

import logging
import os
from typing import Set

from common.auth.veda_auth.keycloak_pdp import KeycloakPDPClient
from common.auth.veda_auth.pep_middleware import PEPMiddleware
from common.auth.veda_auth.resource_extractors import extract_ingest_resource_id
from fastapi import FastAPI

from .auth import auth_settings

logger = logging.getLogger(__name__)


def add_pep_middleware(app: FastAPI) -> None:
    """Add PEP middleware to Ingest API app"""
    if not auth_settings.openid_configuration_url:
        logger.warning(
            "PEP middleware disabled: openid_configuration_url not configured"
        )
        return

    resource_server_client_id = os.getenv("VEDA_RESOURCE_SERVER_CLIENT_ID")
    if not resource_server_client_id:
        logger.warning(
            "PEP middleware disabled: VEDA_RESOURCE_SERVER_CLIENT_ID not configured"
        )
        return

    resource_server_client_secret = os.getenv("VEDA_RESOURCE_SERVER_CLIENT_SECRET")

    # Extract Keycloak URL from openid_configuration_url
    # https://keycloak.example.com/realms/veda -> https://keycloak.example.com
    oidc_url = str(auth_settings.openid_configuration_url)
    # Remove /realms/{realm} or /.well-known/openid-configuration
    keycloak_url = oidc_url.split("/realms/")[0]

    # Extract realm from openid_configuration_url
    # https://keycloak.example.com/realms/veda -> veda
    realm = "veda"  # Default, could be extracted from URL if needed
    if "/realms/" in oidc_url:
        parts = oidc_url.split("/realms/")
        if len(parts) > 1:
            realm = parts[1].split("/")[0]

    pdp_client = KeycloakPDPClient(
        keycloak_url=keycloak_url,
        realm=realm,
        client_id=resource_server_client_id,
        client_secret=resource_server_client_secret,
    )

    public_paths: Set[str] = {
        "/auth/me",
        "/health",
        "/docs",
        "/openapi.json",
    }

    logger.info(
        f"PEP middleware created for Ingest API: keycloak_url={keycloak_url}, realm={realm}, resource_server_client_id={resource_server_client_id}"
    )

    app.add_middleware(
        PEPMiddleware,
        pdp_client=pdp_client,
        resource_extractor=extract_ingest_resource_id,
        public_paths=public_paths,
    )
