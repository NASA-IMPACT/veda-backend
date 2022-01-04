import os
from aws_cdk import (
    aws_apigateway,
    aws_lambda,
    CfnOutput, Duration
)
from constructs import Construct

from database.infrastructure.custom_resource.bootstrapper import BootstrapPgStac

class StacApiLambdaConstruct(Construct):
    def __init__(
        self, 
        scope: Construct,
        construct_id: str, 
        vpc,
        database,
        code_dir: str = "./",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id)

        lambda_function = aws_lambda.Function(
            self,
            "LambdaFunction",
            handler="handler.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath("./"),
                file="stac_api/infrastructure/runtime/Dockerfile",
            ),
            vpc=vpc,
            allow_public_subnet=True,
            # memory_size=eostac_settings.memory,
            timeout=Duration.minutes(2), # TODO config
            # environment=eostac_settings.env or {},
        )
        
        # # TODO 
        # database.secret.grant_read(lambda_function)
    
        # # lambda_function.add_environment(key="TITILER_ENDPOINT", value=raster_api.url)
        # database.secret.grant_read(lambda_function)
        # database.connections.allow_from(lambda_function, port_range=aws_ec2.Port.tcp(5432))

        
        stac_api = aws_apigateway.LambdaRestApi(
            self,
            "StacEndpoint",
            handler=lambda_function,
        )
        
        CfnOutput(self, "DeltaBackendStacApi", value=stac_api.url)