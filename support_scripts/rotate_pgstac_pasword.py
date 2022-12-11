"""
A boto3 utility to rotate pgstac user database password, update corresponding AWS secret, and reboot lambdas using secret
"""

import argparse
import base64
import json
from datetime import datetime
from sys import exit
from typing import Optional

import boto3
import psycopg
from botocore.exceptions import ClientError
from psycopg import sql

parser = argparse.ArgumentParser()
parser.add_argument(
    "-a",
    "--admin",
    dest="admin_secret_name",
    type=str,
    required=True,
    help="Name of AWS secret containing admin role database credentials",
)
parser.add_argument(
    "-p",
    "--pgstac",
    dest="pgstac_secret_name",
    type=str,
    required=True,
    help="Name of AWS secret containing pgstac role database credentials",
)
parser.add_argument(
    "-s",
    "--stac",
    dest="stac_lambda_name",
    type=str,
    required=True,
    help="Name of STAC API lambda",
)
parser.add_argument(
    "-r",
    "--raster",
    dest="raster_lambda_name",
    type=str,
    required=True,
    help="Name of raster/tiler lambda",
)
parser.add_argument(
    "-profile",
    "--profile_name",
    dest="profile_name",
    type=str,
    required=False,
    default=None,
    help="Optional name of AWS config profile",
)
parser.add_argument(
    "-d",
    "--dry",
    dest="dry_run",
    required=False,
    action="store_true",
    default=False,
    help="Optional Dry run to confirm current AWS config profile can read database secrets and connect to postgres",
)
args = parser.parse_args()


def get_secret_dict(secret_name: str, profile_name: Optional[str] = None) -> dict:
    """Retrieve secrets from AWS Secrets Manager

    Args:
        secret_name (str): name of aws secrets manager secret containing database connection secrets
        profile_name (str, optional): optional name of aws profile for use in debugger only

    Returns:
        secrets (dict): decrypted secrets in dict
    """

    # Create a Secrets Manager client
    if profile_name:
        session = boto3.session.Session(profile_name=profile_name)
    else:
        session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise e
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if "SecretString" in get_secret_value_response:
            return json.loads(get_secret_value_response["SecretString"])
        else:
            return json.loads(
                base64.b64decode(get_secret_value_response["SecretBinary"])
            )


def update_secret(
    secret_name: str, updated_secret: dict, profile_name: Optional[str] = None
) -> None:
    """Update an aws secretsmanager secret"""
    # Create a Secrets Manager client
    if profile_name:
        session = boto3.session.Session(profile_name=profile_name)
    else:
        session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    client.update_secret(SecretId=secret_name, SecretString=json.dumps(updated_secret))


def get_random_password(profile_name: Optional[str] = None) -> str:
    """Get new password"""
    if profile_name:
        session = boto3.session.Session(profile_name=profile_name)
    else:
        session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")
    return client.get_random_password(
        ExcludePunctuation=True,
    )["RandomPassword"]


def get_dsn_string(secret: dict) -> str:
    """Form database connection string from a dictionary of connection secrets

    Args:
        secret (dict): dictionary containing connection secrets including username, database name, host, and password

    Returns:
        dsn (str): full database data source name
    """

    try:
        return "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(
            dbname=secret.get("dbname", "postgres"),
            user=secret["username"],
            password=secret["password"],
            host=secret["host"],
            port=secret["port"],
        )
    except Exception as e:
        raise e


def create_user(cursor, username: str, password: str) -> None:
    """Create or update User."""
    cursor.execute(
        sql.SQL(
            "DO $$ "
            "BEGIN "
            "  IF NOT EXISTS ( "
            "       SELECT 1 FROM pg_roles "
            "       WHERE rolname = {user}) "
            "  THEN "
            "    CREATE USER {username} "
            "    WITH PASSWORD {password}; "
            "  ELSE "
            "    ALTER USER {username} "
            "    WITH PASSWORD {password}; "
            "  END IF; "
            "END "
            "$$; "
        ).format(username=sql.Identifier(username), password=password, user=username)
    )


def force_update_lambda(
    function_name: str, new_description: str, profile_name: Optional[str] = None
) -> None:
    """Force lambda to reboot by providing a new description string"""
    if profile_name:
        session = boto3.session.Session(profile_name=profile_name)
    else:
        session = boto3.session.Session()
    client = session.client(service_name="lambda")
    client.update_function_configuration(
        FunctionName=function_name,
        Description=new_description,
    )


# Load admin connection info
print(f"Loading admin credentials from secret={args.admin_secret_name}")
admin_secret_dict = get_secret_dict(
    args.admin_secret_name, profile_name=args.profile_name
)
admin_dsn = get_dsn_string(admin_secret_dict)

# Get pgstac user secret to update
print(f"Loading pgstac veda user credentials from secret={args.pgstac_secret_name}")
pgstac_secret_dict = get_secret_dict(
    args.pgstac_secret_name, profile_name=args.profile_name
)

# Create a new secret password and update local dict
print("Getting new random password from secretsmanager")
new_password = get_random_password()
pgstac_secret_dict["password"] = new_password

# Use admin role to update password for pgstac user role
autocommit = True if args.dry_run is False else False
print(
    f"Updating postgres password for username={pgstac_secret_dict['username']} autocommit={autocommit}"
)
with psycopg.connect(admin_dsn, autocommit=autocommit) as conn:
    with conn.cursor() as cur:
        # Update user password
        create_user(
            cursor=cur,
            username=pgstac_secret_dict["username"],
            password=pgstac_secret_dict["password"],
        )

    if args.dry_run:
        print(
            "Exiting dry run, not committing postgres role update or updating aws secret"
        )
        exit()

    print("Commiting user password changes...")
    conn.commit()

# Test pgstac db connection with new password
pgstac_dsn = get_dsn_string(pgstac_secret_dict)
conn = psycopg.connect(pgstac_dsn)
if conn:
    print(
        "Connection succeeded with new pgstac user credentials, updating AWS Secret..."
    )
    conn.close()
else:
    print(
        "Connection failed with new pgstac user credentials, rollback role change in postgres"
    )
    current_pgstac_secret_dict = get_secret_dict(args.pgstac_secret_name)
    with psycopg.connect(admin_dsn, autocommit=autocommit) as conn:
        with conn.cursor() as cur:
            # Rollback user password
            create_user(
                cursor=cur,
                username=current_pgstac_secret_dict["username"],
                password=current_pgstac_secret_dict["password"],
            )
    exit()

# Update aws secrets manager
print(f"Updating password in secret_name={args.pgstac_secret_name}...")
update_secret(secret_name=args.pgstac_secret_name, updated_secret=pgstac_secret_dict)

# Force lambdas to reboot and retrieve the new secrets by updating the description string in function configuration
print(f"Restarting {args.stac_lambda_name} and {args.raster_lambda_name}...")
ts = datetime.utcnow().isoformat()
new_description = f"Updated at {ts}"
force_update_lambda(args.stac_lambda_name, new_description=new_description)
force_update_lambda(args.raster_lambda_name, new_description=new_description)

print("fin.")
