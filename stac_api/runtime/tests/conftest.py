import os

import boto3
import pytest
from moto import mock_aws

from fastapi.testclient import TestClient


@pytest.fixture
def test_environ():
    # Mocked AWS Credentials for moto (best practice recommendation from moto)
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "us-west-2"

    # Config mocks
    os.environ["ROOT_PATH"] = "/"
    os.environ["COGNITO_DOMAIN"] = "https://test-cognito.url"
    os.environ['VEDA_STAC_PGSTAC_SECRET_ARN'] = 'app_secret'



@pytest.fixture
def mock_ssm_parameter_store():
    with mock_aws():
        yield boto3.client("ssm", region_name="us-west-2")

@pytest.fixture
def mock_secrets_manager():
    with mock_aws():
        yield boto3.client("secretsmanager", region_name="us-west-2")

@pytest.fixture
def mock_create_secret(mock_secrets_manager):
    boto3.client("secretsmanager", region_name="us-west-2").create_secret(Name="app_secret", SecretString="{\"host\": \"test_host\", \"dbname\": \"test_dbname\", \"username\": \"test_username\", \"password\": \"test_password\", \"port\": \"test_port\"}")

@pytest.fixture
def app(test_environ, mock_create_secret):
    from src.app import app

    return app


@pytest.fixture
def api_client(app):
    return TestClient(app)