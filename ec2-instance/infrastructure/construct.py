"""CDK Construct for EC2 Instance with Session Manager support"""
from typing import List, Optional

from aws_cdk import CfnOutput, Stack, aws_ec2, aws_iam
from constructs import Construct

from .config import ec2_instance_settings


class Ec2InstanceConstruct(Construct):
    """CDK Construct for EC2 Instance with Session Manager enabled"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: aws_ec2.IVpc,
        stage: str,
        database_security_groups: Optional[List[aws_ec2.ISecurityGroup]] = None,
        **kwargs,
    ) -> None:
        """Initialize the EC2 instance construct

        Args:
            scope: parent construct
            construct_id: Unique id for construct
            vpc: VPC where the EC2 instance will be deployed
            database_security_groups: Optional list of database security groups
                to allow EC2 to connect to databases
            stage: stage
        """
        super().__init__(scope, construct_id, **kwargs)

        stack_name = Stack.of(self).stack_name

        ec2_sg = aws_ec2.SecurityGroup(
            self,
            "ec2-security-group",
            vpc=vpc,
            description=f"Security group for {stack_name} EC2 instance",
            allow_all_outbound=True,
        )

        if ec2_instance_settings.enable_database_access and database_security_groups:
            for db_sg in database_security_groups:
                db_sg.add_ingress_rule(
                    ec2_sg,
                    aws_ec2.Port.tcp(5432),  # PostgreSQL port
                    f"Allow EC2 instance to connect to database from {stack_name}",
                )

        ec2_role = aws_iam.Role(
            self,
            "ec2-role",
            assumed_by=aws_iam.ServicePrincipal("ec2.amazonaws.com"),
            description=f"IAM role for {stack_name} EC2 instance with Session Manager",
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        user_data = aws_ec2.UserData.for_linux()
        user_data.add_commands(
            "sudo amazon-linux-extras enable -y postgresql14",
            "sudo yum install -y postgresql",
            "psql --version || true",
        )

        instance_config = {
            "vpc": vpc,
            "instance_type": aws_ec2.InstanceType.of(
                aws_ec2.InstanceClass[ec2_instance_settings.instance_type_class],
                aws_ec2.InstanceSize[ec2_instance_settings.instance_type_size],
            ),
            "machine_image": aws_ec2.MachineImage.latest_amazon_linux2(),
            "vpc_subnets": aws_ec2.SubnetSelection(
                subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            "security_group": ec2_sg,
            "role": ec2_role,
            "user_data": user_data,
        }

        if ec2_instance_settings.key_pair_name:
            instance_config["key_name"] = ec2_instance_settings.key_pair_name

        instance = aws_ec2.Instance(
            self,
            "ec2-instance",
            **instance_config,
        )

        self.instance = instance
        self.security_group = ec2_sg
        self.role = ec2_role

        CfnOutput(
            self,
            "ec2-instance-id",
            value=instance.instance_id,
            description=f"EC2 Instance ID for {stack_name}",
        )

        CfnOutput(
            self,
            "ec2-connection-instructions",
            value=(
                f"Connect using Session Manager: "
                f"aws ssm start-session --target {instance.instance_id}"
            ),
            description="Instructions to connect to EC2 instance via Session Manager",
        )

        if ec2_instance_settings.key_pair_name:
            CfnOutput(
                self,
                "ec2-ssh-instructions",
                value=(
                    f"SSH connection (if in public subnet): "
                    f"ssh -i <key-file> ec2-user@{instance.instance_public_ip}"
                ),
                description="SSH connection instructions (if key pair is configured)",
            )
