from getpass import getuser
from typing import Optional

import aws_cdk
from pydantic import BaseSettings, Field, constr

AwsArn = constr(regex=r"^arn:aws:iam::\d{12}:role/.+")
AwsStepArn = constr(regex=r"^arn:aws:states:.+:\d{12}:stateMachine:.+")
AwsOidcArn = constr(regex=r"^arn:aws:iam::\d{12}:oidc-provider/.+")


class IngestorConfig(BaseSettings):
    stage: str = Field(
        description=" ".join(
            [
                "Stage of deployment (e.g. 'dev', 'prod').",
                "Used as suffix for stack name.",
                "Defaults to current username.",
            ]
        ),
        default_factory=getuser,
    )
    owner: str = Field(
        description=" ".join(
            [
                "Name of primary contact for Cloudformation Stack.",
                "Used to tag generated resources",
                "Defaults to current username.",
            ]
        ),
        default_factory=getuser,
    )

    aws_account: str = Field(
        description="AWS account used for deployment",
        alias="CDK_DEFAULT_ACCOUNT",
    )
    aws_region: str = Field(
        default="us-west-2",
        description="AWS region used for deployment",
        alias="CDK_DEFAULT_REGION",
    )

    userpool_id: str = Field(description="The Cognito Userpool used for authentication")
    client_id: str = Field(description="The Cognito APP client ID")
    client_secret: str = Field(description="The Cognito APP client secret")

    stac_db_secret_name: str = Field(
        description="Name of secret containing pgSTAC DB connection information"
    )
    stac_db_vpc_id: str = Field(description="ID of VPC running pgSTAC DB")
    stac_db_security_group_id: str = Field(
        description="ID of Security Group used by pgSTAC DB"
    )
    stac_db_public_subnet: bool = Field(
        description="Boolean indicating whether or not pgSTAC DB is in a public subnet",
        default=True,
    )

    data_access_role: AwsArn = Field(  # type: ignore
        description="ARN of AWS Role used to validate access to S3 data"
    )

    mwaa_env: Optional[str] = Field(
        description="Environment of Airflow deployment",
    )

    class Config:
        env_prefix = ""
        case_sentive = False
        env_file = ".env"

    @property
    def stack_name(self) -> str:
        return f"veda-stac-ingestion-{self.stage}"

    @property
    def env(self) -> aws_cdk.Environment:
        return aws_cdk.Environment(
            account=self.aws_account,
            region=self.aws_region,
        )
