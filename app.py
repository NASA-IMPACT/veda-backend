#!/usr/bin/env python3
""" CDK Configuration for the veda-backend stack."""

import json
import subprocess

from aws_cdk import App, Stack, Tags, aws_iam
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

from config import veda_app_settings
from database.infrastructure.construct import RdsConstruct
from domain.infrastructure.construct import DomainConstruct
from network.infrastructure.construct import VpcConstruct
from raster_api.infrastructure.construct import RasterApiLambdaConstruct
from stac_api.infrastructure.construct import StacApiLambdaConstruct

app = App()


class VedaStack(Stack):
    """CDK stack for the veda-backend stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        if veda_app_settings.permissions_boundary_policy_name:
            permission_boundary_policy = aws_iam.Policy.from_policy_name(
                self,
                "permission-boundary",
                veda_app_settings.permissions_boundary_policy_name,
            )
            aws_iam.PermissionsBoundary.of(self).apply(permission_boundary_policy)

    def build_oidc(
        self, oidc_provider_arn: str, oidc_repo_id: str, secret_arn: str, stage: str
    ):
        """Create OIDC role for veda-backend repo to use"""
        # Locate an IAM OIDC provider for the specified provider ARN
        oidc_provider = aws_iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self, "OIDCProvider", oidc_provider_arn
        )
        # create IAM role for provider access from specified repo
        # the role will allow a github action in that repo
        # to deploy resources and read a secret
        oidc_role = aws_iam.Role(
            self,
            f"veda-backend-oidc-role-{stage}",
            assumed_by=aws_iam.WebIdentityPrincipal(
                oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        f"{oidc_provider.open_id_connect_provider_issuer}:sub": f"repo:{oidc_repo_id}"
                    }
                },
            ),
        )
        oidc_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=["sts:AssumeRoleWithWebIdentity"],
                resources=[oidc_provider_arn],
            )
        )

        # Create an IAM policy statement that allows getting the secret value
        get_secret_statement = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["secretsmanager:GetSecretValue"],
            resources=[secret_arn],
        )

        oidc_policy = aws_iam.Policy(
            self,
            f"veda-backend-oidc-policy-{stage}",
            policy_name=f"veda-backend-oidc-policy-{stage}",
            roles=[oidc_role],
            statements=[get_secret_statement],
        )
        return oidc_role, oidc_policy, oidc_provider

    def build_env_secret(self, stage: str, env_config: dict) -> secretsmanager.ISecret:
        """Create secret to store environment variables"""
        return secretsmanager.Secret(
            self,
            f"veda-backend-env-secret-{stage}",
            secret_name=f"veda-backend-env-secret-{stage}",
            description="Contains env vars used for deployment of veda-backend",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps(env_config),
                generate_string_key="password",
                exclude_punctuation=True,
            ),
        )


veda_stack = VedaStack(
    app,
    f"{veda_app_settings.app_name}-{veda_app_settings.stage_name()}",
    env=veda_app_settings.cdk_env(),
)

if veda_app_settings.vpc_id:
    vpc = VpcConstruct(
        veda_stack,
        "network",
        vpc_id=veda_app_settings.vpc_id,
        stage=veda_app_settings.stage_name(),
    )
else:
    vpc = VpcConstruct(veda_stack, "network", stage=veda_app_settings.stage_name())

database = RdsConstruct(
    veda_stack, "database", vpc.vpc, stage=veda_app_settings.stage_name()
)

domain = DomainConstruct(veda_stack, "domain", stage=veda_app_settings.stage_name())

raster_api = RasterApiLambdaConstruct(
    veda_stack,
    "raster-api",
    vpc=vpc.vpc,
    database=database,
    domain_name=domain.raster_domain_name,
)

stac_api = StacApiLambdaConstruct(
    veda_stack,
    "stac-api",
    vpc=vpc.vpc,
    database=database,
    raster_api=raster_api,
    domain_name=domain.stac_domain_name,
)

env_secret = veda_stack.build_env_secret(
    stage=veda_app_settings.stage_name(),
    env_config=veda_app_settings.dict(),
)

if veda_app_settings.oidc_provider_arn:
    oidc_resources = veda_stack.build_oidc(
        oidc_provider_arn=veda_app_settings.oidc_provider_arn,
        oidc_repo_id=veda_app_settings.oidc_repo_id,
        secret_arn=env_secret.secret_arn,
        stage=veda_app_settings.stage_name(),
    )

# TODO this conditional supports deploying a second set of APIs to a separate custom domain and should be removed if no longer necessary
if veda_app_settings.alt_domain():
    alt_domain = DomainConstruct(
        veda_stack,
        "alt-domain",
        stage=veda_app_settings.stage_name(),
        alt_domain=True,
    )

    alt_raster_api = RasterApiLambdaConstruct(
        veda_stack,
        "alt-raster-api",
        vpc=vpc.vpc,
        database=database,
        domain_name=alt_domain.raster_domain_name,
    )

    alt_stac_api = StacApiLambdaConstruct(
        veda_stack,
        "alt-stac-api",
        vpc=vpc.vpc,
        database=database,
        raster_api=raster_api,
        domain_name=alt_domain.stac_domain_name,
    )

git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
try:
    git_tag = subprocess.check_output(["git", "describe", "--tags"]).decode().strip()
except subprocess.CalledProcessError:
    git_tag = "no-tag"

for key, value in {
    "Project": veda_app_settings.app_name,
    "Stack": veda_app_settings.stage_name(),
    "Client": "nasa-impact",
    "Owner": veda_app_settings.owner,
    "GitCommit": git_sha,
    "GitTag": git_tag,
}.items():
    if value:
        Tags.of(app).add(key=key, value=value)

app.synth()
