"""
Custom resource lambda handler to bootstrap Postgres db.
Source: https://github.com/developmentseed/eoAPI/blob/master/deployment/handlers/db_handler.py
"""
import json

import boto3
import psycopg
import requests
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pypgstac.db import PgstacDB
from pypgstac.migrate import Migrate


def send(
    event,
    context,
    responseStatus,
    responseData,
    physicalResourceId=None,
    noEcho=False,
):
    """
    Copyright 2016 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
    This file is licensed to you under the AWS Customer Agreement (the "License").
    You may not use this file except in compliance with the License.
    A copy of the License is located at http://aws.amazon.com/agreement/ .
    This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied.
    See the License for the specific language governing permissions and limitations under the License.

    Send response from AWS Lambda.

    Note: The cfnresponse module is available only when you use the ZipFile property to write your source code.
    It isn't available for source code that's stored in Amazon S3 buckets.
    For code in buckets, you must write your own functions to send responses.
    """
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


def get_secret(secret_name):
    """Get Secrets from secret manager."""
    print(f"Fetching {secret_name}")
    client = boto3.client(service_name="secretsmanager")
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
            "GRANT pgstac_read TO {username};"
            "GRANT pgstac_ingest TO {username};"
            "GRANT pgstac_admin TO {username};"
        ).format(
            db_name=sql.Identifier(db_name),
            username=sql.Identifier(username),
        )
    )


def register_extensions(cursor) -> None:
    """Add PostGIS extension."""
    cursor.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS postgis;"))


def create_dashboard_schema(cursor, username: str) -> None:
    """Create custom schema for dashboard-specific functions."""
    cursor.execute(
        sql.SQL(
            "CREATE SCHEMA IF NOT EXISTS dashboard;"
            "GRANT ALL ON SCHEMA dashboard TO {username};"
            "ALTER ROLE {username} SET SEARCH_PATH TO dashboard, pgstac, public;"
        ).format(username=sql.Identifier(username))
    )


def create_collection_summaries_functions(cursor) -> None:
    """
    Functions to summarize datetimes and raster statistics for 'default' collections of items with single band COG assets
    """

    periodic_datetime_summary_sql = """
    CREATE OR REPLACE FUNCTION dashboard.periodic_datetime_summary(id text) RETURNS jsonb
    LANGUAGE sql
    IMMUTABLE PARALLEL SAFE
    SET search_path TO 'pgstac', 'public'
    AS $function$
        SELECT to_jsonb(
            array[
                to_char(min(datetime) at time zone 'Z', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                to_char(max(datetime) at time zone 'Z', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
            ])​
        FROM items WHERE collection=$1;
    ;
    $function$
    ;
    """
    cursor.execute(sql.SQL(periodic_datetime_summary_sql))

    search_collections_sql = """
    CREATE OR REPLACE FUNCTION collectionsearch(_search jsonb) RETURNS setof text AS $$
        DECLARE
            where_segments text[];
            _where text;
            geom geometry;
            dtrange tstzrange;
            sdate timestamptz;
            edate timestamptz;
        BEGIN
            IF j ? 'datetime' THEN
                dtrange := parse_dtrange(j->'datetime');
                sdate := lower(dtrange);
                edate := upper(dtrange);

                where_segments := where_segments || format(' temporalmin <= %L::timestamptz AND temporalmax >= %L::timestamptz ',
                    edate,
                    sdate
                );
            END IF;

            geom := stac_geom(j);
            IF geom IS NOT NULL THEN
                where_segments := where_segments || format('st_intersects(geometry, %L)',geom);
            END IF;

            _where := array_to_string(array_remove(where_segments, NULL), ' AND ');

        RETURN QUERY
        SELECT
            id
        FROM
            (SELECT
                id as id,
                ST_MakeEnvelope(
                    (inner.spatial->0)::INTEGER, (inner.spatial->1)::INTEGER, (inner.spatial->2)::INTEGER, (inner.spatial->3)::INTEGER, 4326
                ) as geometry,
                inner.temporalmin as temporalmin,
                inner.temporalmax as temporalmax
            FROM
                (SELECT
                    id,
                    (content::jsonb->'extent'->'spatial'->'bbox'->0) as spatial,
                    (content::jsonb->'extent'->'temporal'->'interval'->0->0)::text::timestamptz as temporalmin,
                    (content::jsonb->'extent'->'temporal'->'interval'->0->1)::text::timestamptz as temporalmax
                FROM collections
                ) as inner
            ) as outer
        WHERE _where;
    END;
    $$ LANGUAGE PLPGSQL STABLE;
    """
    cursor.execute(sql.SQL(search_collections_sql))

    distinct_datetime_summary_sql = """
    CREATE OR REPLACE FUNCTION dashboard.discrete_datetime_summary(id text) RETURNS jsonb
    LANGUAGE sql
    IMMUTABLE PARALLEL SAFE
    SET search_path TO 'pgstac', 'public'
    AS $function$
        SELECT jsonb_agg(distinct to_char(datetime at time zone 'Z', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
        FROM items WHERE collection=$1;
    ;
    $function$
    ;
    """
    cursor.execute(sql.SQL(distinct_datetime_summary_sql))

    cog_default_summary_sql = """
    CREATE OR REPLACE FUNCTION dashboard.cog_default_summary(id text) RETURNS jsonb
    LANGUAGE sql
    IMMUTABLE PARALLEL SAFE
    SET search_path TO 'pgstac', 'public'
    AS $function$
        SELECT jsonb_build_object(
            'min', min((items."content"->'assets'->'cog_default'->'raster:bands'-> 0 ->'statistics'->>'minimum')::float),
            'max', max((items."content"->'assets'->'cog_default'->'raster:bands'-> 0 ->'statistics'->>'maximum')::float)
        )
        FROM items WHERE collection=$1;
    ;
    $function$
    ;
    """
    cursor.execute(sql.SQL(cog_default_summary_sql))

    update_collection_default_summaries_sql = """
    CREATE OR REPLACE FUNCTION dashboard.update_collection_default_summaries(id text)
    RETURNS void
    LANGUAGE sql
    SET search_path TO 'pgstac', 'public'
    AS $function$
    UPDATE collections SET
        "content" = "content" ||
        jsonb_build_object(
            'summaries', jsonb_build_object(
                'datetime', (
                    CASE
                    WHEN (collections."content"->>'dashboard:is_periodic')::boolean
                    THEN dashboard.periodic_datetime_summary(collections.id)
                    ELSE dashboard.discrete_datetime_summary(collections.id)
                    END
                ),
                'cog_default', (
                    CASE
                    WHEN collections."content"->'item_assets' ? 'cog_default'
                    THEN dashboard.cog_default_summary(collections.id)
                    ELSE NULL
                    END
                )
            )
        )
        WHERE collections.id=$1
    ;
    $function$
    ;
    """
    cursor.execute(sql.SQL(update_collection_default_summaries_sql))

    update_all_collection_default_summaries_sql = """
    CREATE OR REPLACE FUNCTION dashboard.update_all_collection_default_summaries()
    RETURNS void
    LANGUAGE sql
    SET search_path TO 'pgstac', 'public'
    AS $function$
    UPDATE collections SET
        "content" = "content" ||
        jsonb_build_object(
            'summaries', jsonb_build_object(
                'datetime', (
                    CASE
                    WHEN (collections."content"->>'dashboard:is_periodic')::boolean
                    THEN dashboard.periodic_datetime_summary(collections.id)
                    ELSE dashboard.discrete_datetime_summary(collections.id)
                    END
                ),
                'cog_default', (
                    CASE
                    WHEN collections."content"->'item_assets' ? 'cog_default'
                    THEN dashboard.cog_default_summary(collections.id)
                    ELSE NULL
                    END
                )
            )
        )
        WHERE collections."content" ?| array['item_assets', 'dashboard:is_periodic']
    ;
    $function$
    ;
    """
    cursor.execute(sql.SQL(update_all_collection_default_summaries_sql))


def handler(event, context):
    """Lambda Handler."""
    print(f"Handling {event}")

    if event["RequestType"] not in ["Create", "Update"]:
        return send(event, context, "SUCCESS", {"msg": "No action to be taken"})

    try:
        params = event["ResourceProperties"]
        connection_params = get_secret(params["conn_secret_arn"])
        user_params = get_secret(params["new_user_secret_arn"])

        print("Connecting to admin DB...")
        admin_db_conninfo = make_conninfo(
            dbname=connection_params.get("dbname", "postgres"),
            user=connection_params["username"],
            password=connection_params["password"],
            host=connection_params["host"],
            port=connection_params["port"],
        )
        with psycopg.connect(admin_db_conninfo, autocommit=True) as conn:
            with conn.cursor() as cur:
                print("Creating database...")
                create_db(
                    cursor=cur,
                    db_name=user_params["dbname"],
                )

                print("Creating user...")
                create_user(
                    cursor=cur,
                    username=user_params["username"],
                    password=user_params["password"],
                )

        # Install extensions on the user DB with
        # superuser permissions, since they will
        # otherwise fail to install when run as
        # the non-superuser within the pgstac
        # migrations.
        print("Connecting to STAC DB...")
        stac_db_conninfo = make_conninfo(
            dbname=user_params["dbname"],
            user=connection_params["username"],
            password=connection_params["password"],
            host=connection_params["host"],
            port=connection_params["port"],
        )
        with psycopg.connect(stac_db_conninfo, autocommit=True) as conn:
            with conn.cursor() as cur:
                print("Registering PostGIS ...")
                register_extensions(cursor=cur)

        stac_db_admin_dsn = (
            "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(
                dbname=user_params.get("dbname", "postgres"),
                user=connection_params["username"],
                password=connection_params["password"],
                host=connection_params["host"],
                port=connection_params["port"],
            )
        )

        pgdb = PgstacDB(dsn=stac_db_admin_dsn, debug=True)
        print(f"Current {pgdb.version=}")

        # As admin, run migrations
        print("Running migrations...")
        Migrate(pgdb).run_migration(params["pgstac_version"])

        # Assign appropriate permissions to user (requires pgSTAC migrations to have run)
        with psycopg.connect(admin_db_conninfo, autocommit=True) as conn:
            with conn.cursor() as cur:
                print("Setting permissions...")
                create_permissions(
                    cursor=cur,
                    db_name=user_params["dbname"],
                    username=user_params["username"],
                )

        print("Adding mosaic index...")
        with psycopg.connect(
            stac_db_admin_dsn,
            autocommit=True,
            options="-c search_path=pgstac,public -c application_name=pgstac",
        ) as conn:
            conn.execute(
                sql.SQL(
                    "CREATE INDEX IF NOT EXISTS searches_mosaic ON searches ((true)) WHERE metadata->>'type'='mosaic';"
                )
            )

        # As admin, create custom dashboard schema and functions and grant privileges to bootstrapped user
        with psycopg.connect(stac_db_conninfo, autocommit=True) as conn:
            with conn.cursor() as cur:
                print("Creating dashboard schema...")
                create_dashboard_schema(cursor=cur, username=user_params["username"])

                print(
                    "Creating functions for summarizing default collection datetimes and cog_default statistics..."
                )
                create_collection_summaries_functions(cursor=cur)

    except Exception as e:
        print(f"Unable to bootstrap database with exception={e}")
        return send(event, context, "FAILED", {"message": str(e)})

    print("Complete.")
    return send(event, context, "SUCCESS", {})
