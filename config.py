import pydantic
from typing import Optional, Union
import typing

import jsii
from aws_cdk import aws_iam, CfnResource, IAspect
from constructs import IConstruct
from jsii._reference_map import _refs
from jsii._utils import Singleton

class deltaAppSettings(pydantic.BaseSettings):
    """Application settings."""

    # App name and deployment stage
    app_name: Optional[str] = "delta-backend"
    stage: str

    # Optional specify vpc-id in target account
    vpc_id: Optional[str] = None
    cdk_default_account: Optional[str] = None
    cdk_default_region: Optional[str] = None

    # Optional permissions boundary policy
    permissions_boundary_policy: Optional[str] = None

    def cdk_env(self) -> dict:
        """Load a cdk environment dict for stack"""

        if self.vpc_id:
            return {
                "account": self.cdk_default_account,
                "region": self.cdk_default_region
            }
        else:
            return {}


    class Config:
        """model config."""

        env_file = ".env"

delta_app_settings = deltaAppSettings()

# @jsii.implements(IAspect)
# class PermissionBoundaryAspect:
#     """
#     This aspect finds all aws_iam.Role objects in a node (ie. CDK stack) and
#     sets permission boundary to the given ARN.
#     https://github.com/aws/aws-cdk/issues/3242#issuecomment-553815373
#     """

#     def __init__(
#         self,
#         permission_boundary: Union[aws_iam.ManagedPolicy, str],
#     ) -> None:
#         """
#         :param permission_boundary: Either aws_iam.ManagedPolicy object or
#         managed policy's ARN string
#         """
#         self.permission_boundary = permission_boundary

#     def visit(self, construct_ref: IConstruct) -> None:
#         """
#         construct_ref only contains a string reference to an object. To get the
#         actual object, we need to resolve it using JSII mapping.
#         :param construct_ref: ObjRef object with string reference to the actual object.
#         :return: None
#         """
#         if isinstance(construct_ref, jsii._kernel.ObjRef) and hasattr(  # type: ignore
#             construct_ref, "ref"
#         ):
#             kernel = Singleton._instances[
#                 jsii._kernel.Kernel  # type: ignore
#             ]  # The same object is available as: jsii.kernel
#             resolve = _refs.resolve(kernel, construct_ref)
#         else:
#             resolve = construct_ref

#         def _walk(obj):
#             if isinstance(obj, aws_iam.Role):
#                 cfn_role = typing.cast(
#                     CfnResource, obj.node.find_child("Resource")
#                 )
#                 policy_arn = (
#                     self.permission_boundary
#                     if isinstance(self.permission_boundary, str)
#                     else self.permission_boundary.managed_policy_arn
#                 )
#                 cfn_role.add_property_override("PermissionsBoundary", policy_arn)
#             else:
#                 if hasattr(obj, "permissions_node"):
#                     for c in obj.permissions_node.children:
#                         _walk(c)
#                 if hasattr(obj, "node") and obj.node.children:
#                     for c in obj.node.children:
#                         _walk(c)

#         _walk(resolve)