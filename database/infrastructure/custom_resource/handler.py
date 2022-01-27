"""
Custom resource lambda handler to bootstrap Postgres db. 
Source: https://github.com/developmentseed/eoAPI/blob/master/deployment/handlers/db_handler.py
"""

import json

import boto3
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore


###
"""response from aws lambda."""
#  Copyright 2016 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#  This file is licensed to you under the AWS Customer Agreement (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at http://aws.amazon.com/agreement/ .
#  This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS
#  OF ANY KIND, express or implied.
#  See the License for the specific language governing permissions and limitations
#  under the License.

import json

import requests

SUCCESS = "SUCCESS"
FAILED = "FAILED"


def send(
    event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False
):
    """Send response from AWS Lambda."""
    responseUrl = event["ResponseURL"]

    print(responseUrl)

    responseBody = {}
    responseBody["Status"] = responseStatus
    responseBody["Reason"] = (
        "See the details in CloudWatch Log Stream: " + context.log_stream_name
    )
    responseBody["PhysicalResourceId"] = physicalResourceId or context.log_stream_name
    responseBody["StackId"] = event["StackId"]
    responseBody["RequestId"] = event["RequestId"]
    responseBody["LogicalResourceId"] = event["LogicalResourceId"]
    responseBody["NoEcho"] = noEcho
    responseBody["Data"] = responseData

    json_responseBody = json.dumps(responseBody)

    print("Response body:\n" + json_responseBody)

    headers = {"content-type": "", "content-length": str(len(json_responseBody))}

    try:
        response = requests.put(responseUrl, data=json_responseBody, headers=headers)
        print("Status code: " + response.reason)
    except Exception as e:
        print("send(..) failed executing requests.put(..): " + str(e))
###


def get_secret(secret_name):
    """Get Secrets from secret manager."""
    print(f"Fetching {secret_name}")
    client = boto3.client(service_name="secretsmanager",)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def create_db(cursor, db_name: str) -> None:
    """Create DB."""
    cursor.execute(
        sql.SQL("SELECT 1 FROM pg_catalog.pg_database " "WHERE datname = %s"), [db_name]
    )
    if cursor.fetchone():
        print(f"database {db_name} exists, not creating DB")
    else:
        print(f"database {db_name} not found, creating...")
        cursor.execute(
            sql.SQL("CREATE DATABASE {db_name}").format(db_name=sql.Identifier(db_name))
        )


def create_user(cursor, username: str, password: str) -> None:
    """Create User."""
    cursor.execute(
        sql.SQL(
            "DO $$ "
            "BEGIN "
            "  IF NOT EXISTS ( "
            "       SELECT 1 FROM pg_roles "
            "       WHERE rolname = %(user)s) "
            "  THEN "
            "    CREATE USER {username} "
            "    WITH PASSWORD %(pass)s; "
            "  ELSE "
            "    ALTER USER {username} "
            "    WITH PASSWORD %(pass)s; "
            "  END IF; "
            "END "
            "$$; "
        ).format(username=sql.Identifier(username),),
        {"user": username, "pass": password},
    )


def create_permissions(cursor, db_name: str, username: str) -> None:
    """Add permissions."""
    cursor.execute(
        sql.SQL(
            "GRANT CONNECT ON DATABASE {db_name} TO {username};"
            "GRANT CREATE ON DATABASE {db_name} TO {username};"  # Allow schema creation
            "GRANT USAGE ON SCHEMA public TO {username};"
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT ALL PRIVILEGES ON TABLES TO {username};"
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT ALL PRIVILEGES ON SEQUENCES TO {username};"
        ).format(
            db_name=sql.Identifier(db_name), username=sql.Identifier(username),
        )
    )


def register_extensions(cursor) -> None:
    """Add PostGIS extension."""
    cursor.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS postgis;"))


def register_pgstac(cursor) -> None:
    """Register PgSTAC."""
    version = "0.3.4"
    pgstac_sql = str(
        resources_files("pypgstac") / "migrations" / f"pgstac.{version}.sql"
    )
    sqlstrs = []
    with open(pgstac_sql) as f:
        sqlstrs.extend(f.readlines())
        migration_sql = "\n".join(sqlstrs)
        cursor.execute(sql.SQL(migration_sql))


def handler(event, context):
    """Lambda Handler."""
    print(f"Handling {event}")

    if event["RequestType"] not in ["Create", "Update"]:
        print(f"RequestType={event['RequestType']}. No action to be taken")
        return send(
            event, context, "SUCCESS", {"msg": "No action to be taken"}
        )

    try:
        params = event["ResourceProperties"]
        connection_params = get_secret(params["conn_secret_arn"])
        user_params = get_secret(params["new_user_secret_arn"])

        print("Connecting to DB...")
        conn = psycopg2.connect(
            dbname=connection_params.get("dbname", "postgres"),
            user=connection_params["username"],
            password=connection_params["password"],
            host=connection_params["host"],
            port=connection_params["port"],
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        with conn.cursor() as cur:
            print("Creating database...")
            create_db(
                cursor=cur, db_name=user_params["dbname"],
            )

            print("Creating user...")
            create_user(
                cursor=cur,
                username=user_params["username"],
                password=user_params["password"],
            )

            print("Setting permissions...")
            create_permissions(
                cursor=cur,
                db_name=user_params["dbname"],
                username=user_params["username"],
            )

        # Install extensions on the user DB with
        # superuser permissions, since they will
        # otherwise fail to install when run as
        # the non-superuser within the pgstac
        # migrations.
        conn = psycopg2.connect(
            dbname=user_params["dbname"],
            user=connection_params["username"],
            password=connection_params["password"],
            host=connection_params["host"],
            port=connection_params["port"],
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            print("Registering extensions on pgstac db...")
            register_extensions(cursor=cur)

        conn = psycopg2.connect(
            dbname=user_params.get("dbname", "postgres"),
            user=user_params["username"],
            password=user_params["password"],
            host=connection_params["host"],
            port=connection_params["port"],
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            print("Register PgSTAC functions...")
            register_pgstac(cursor=cur)

    except Exception as e:
        print(f"Unable to bootstrap database with exception={e}")
        return send(event, context, "FAILED", {"message": str(e)})

    print("Complete.")
    return send(event, context, "SUCCESS", {})
