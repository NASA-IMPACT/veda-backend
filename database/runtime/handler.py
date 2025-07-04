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
    """Add permissions and user-specific pgstac configuration."""
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
            "ALTER ROLE {username} SET SEARCH_PATH TO pgstac, dashboard, public;"
        ).format(username=sql.Identifier(username))
    )


def create_collection_search_functions(cursor) -> None:
    """Create custom functions for collection-level search."""

    search_collection_ids_sql = """
    CREATE OR REPLACE FUNCTION pgstac.collection_id_search(_search jsonb = '{}'::jsonb) RETURNS SETOF text AS $$
    DECLARE
        searches searches%ROWTYPE;
        _where text;
        token_where text;
        full_where text;
        orderby text;
        query text;
        token_type text := substr(_search->>'token',1,4);
        curs refcursor;
        iter_record items%ROWTYPE;
        prev_query text;
        next text;
        prev_id text;
        has_next boolean := false;
        has_prev boolean := false;
        prev text;
        total_count bigint;
        context jsonb;
        includes text[];
        excludes text[];
        exit_flag boolean := FALSE;
        batches int := 0;
        timer timestamptz := clock_timestamp();
        pstart timestamptz;
        pend timestamptz;
        pcurs refcursor;
        search_where search_wheres%ROWTYPE;
        id text;
        collections text[];
    BEGIN
    CREATE TEMP TABLE results (collection text, content jsonb) ON COMMIT DROP;
    -- if ids is set, short circuit and just use direct ids query for each id
    -- skip any paging or caching
    -- hard codes ordering in the same order as the array of ids
    searches := search_query(_search);
    _where := searches._where;
    orderby := searches.orderby;
    search_where := where_stats(_where);
    total_count := coalesce(search_where.total_count, search_where.estimated_count);

    IF token_type='prev' THEN
        token_where := get_token_filter(_search, null::jsonb);
        orderby := sort_sqlorderby(_search, TRUE);
    END IF;
    IF token_type='next' THEN
        token_where := get_token_filter(_search, null::jsonb);
    END IF;

    full_where := concat_ws(' AND ', _where, token_where);
    RAISE NOTICE 'FULL QUERY % %', full_where, clock_timestamp()-timer;
    timer := clock_timestamp();

    FOR query IN SELECT partition_queries(full_where, orderby, search_where.partitions)
    LOOP
        timer := clock_timestamp();
        RAISE NOTICE 'Partition Query: %', query;
        batches := batches + 1;
        -- curs = create_cursor(query);
        RAISE NOTICE 'cursor_tuple_fraction: %', current_setting('cursor_tuple_fraction');
        OPEN curs FOR EXECUTE query;
        LOOP
            FETCH curs into iter_record;
            EXIT WHEN NOT FOUND;

            INSERT INTO results (collection, content) VALUES (iter_record.collection, iter_record.content);

        END LOOP;
        CLOSE curs;
        RAISE NOTICE 'Query took %.', clock_timestamp()-timer;
        timer := clock_timestamp();
        EXIT WHEN exit_flag;
    END LOOP;
    RAISE NOTICE 'Scanned through % partitions.', batches;

    RETURN QUERY SELECT DISTINCT collection FROM results WHERE content is not NULL;

    DROP TABLE results;

    RETURN;
    END;
    $$ LANGUAGE PLPGSQL SECURITY DEFINER SET SEARCH_PATH TO pgstac, public SET cursor_tuple_fraction TO 1;
    """
    cursor.execute(sql.SQL(search_collection_ids_sql))


def create_collection_extents_functions(cursor) -> None:
    """
    Functions to update spatial and temporal extents off all items in a collection
    This is slightly different from the inbuilt pgstac.update_collection_extents function which describes the range of nominal datetimes,
    here we capture the maximum range which must include max end datetime.
    """

    collection_temporal_extent_max_sql = """
    CREATE OR REPLACE FUNCTION dashboard.collection_temporal_extent_max(id text) RETURNS jsonb
    LANGUAGE sql
    IMMUTABLE PARALLEL SAFE
    SET search_path TO 'pgstac', 'public'
    AS $function$
        SELECT to_jsonb(array[array[min(datetime)::text, max(end_datetime)::text]])
        FROM items WHERE collection=$1;
    $function$
    ;
    """
    cursor.execute(sql.SQL(collection_temporal_extent_max_sql))

    update_collection_extents_max_sql = """
    CREATE OR REPLACE FUNCTION dashboard.update_collection_extents_max(id text)
    RETURNS void
    LANGUAGE sql
    SET search_path TO 'pgstac', 'public'
    AS $function$
        UPDATE collections SET
            content = content ||
            jsonb_build_object(
                'extent', jsonb_build_object(
                    'spatial', jsonb_build_object(
                        'bbox', collection_bbox(collections.id)
                    ),
                    'temporal', jsonb_build_object(
                        'interval', dashboard.collection_temporal_extent_max(collections.id)
                    )
                )
            )
        WHERE collections.id=$1;
    $function$
    ;
    """
    cursor.execute(sql.SQL(update_collection_extents_max_sql))


def create_collection_summaries_functions(cursor) -> None:
    """
    Functions to summarize datetimes and raster statistics for 'default' collections of items
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
                to_char(max(end_datetime) at time zone 'Z', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
            ])​
        FROM items WHERE collection=$1;
    ;
    $function$
    ;
    """
    cursor.execute(sql.SQL(periodic_datetime_summary_sql))

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
    SELECT dashboard.update_collection_default_summaries(collections.id)
    FROM collections
    WHERE collections."content" ?| array['dashboard:is_periodic']
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

        # As admin, create custom search functions
        with psycopg.connect(stac_db_conninfo, autocommit=True) as conn:
            with conn.cursor() as cur:
                print("Creating custom STAC search functions...")
                create_collection_search_functions(cursor=cur)

        with psycopg.connect(stac_db_conninfo, autocommit=True) as conn:
            with conn.cursor() as cur:
                print("Creating dashboard schema...")
                create_dashboard_schema(cursor=cur, username=user_params["username"])

                print("Creating functions for summarizing collection datetimes...")
                create_collection_summaries_functions(cursor=cur)

                print(
                    "Creating functions for setting the maximum end_datetime temporal extent of a collection..."
                )
                create_collection_extents_functions(cursor=cur)

    except Exception as e:
        print(f"Unable to bootstrap database with exception={e}")
        return send(event, context, "FAILED", {"message": str(e)})

    print("Complete.")
    return send(event, context, "SUCCESS", {})
