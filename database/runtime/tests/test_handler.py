"""Tests for handler.py.

These run against the database service in docker-compose.yml. The SQL
function tests run inside a transaction that is always rolled back.
"""

import psycopg
import pytest
from handler import (
    bootstrap,
    create_collection_extents_functions,
    create_collection_summaries_functions,
    create_dashboard_schema,
)
from psycopg import sql
from psycopg.types.json import Jsonb
from pypgstac.version import __version__ as PGSTAC_VERSION

# The secrets that bootstrap receives, as get_secret returns them.
ADMIN_SECRET = {
    "host": "localhost",
    "port": 5439,
    "dbname": "postgis",
    "username": "username",
    "password": "password",
}
DSN = "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(**ADMIN_SECRET)
RERUN_NAME = "rerun_test"
USER_SECRET = ADMIN_SECRET | {
    "dbname": RERUN_NAME,
    "username": RERUN_NAME,
    "password": RERUN_NAME,
}

COLLECTION = {
    "id": "test-summaries",
    "extent": {
        "spatial": {"bbox": [[-180, -90, 180, 90]]},
        "temporal": {"interval": [[None, None]]},
    },
}
ITEM = {
    "id": "test-item",
    "collection": COLLECTION["id"],
    "geometry": {"type": "Point", "coordinates": [0, 0]},
    "properties": {"datetime": "2021-01-01T00:00:00Z"},
}
DATETIME_SUMMARY = ["2021-01-01T00:00:00Z"]


@pytest.mark.parametrize(
    ("collection_fields", "expected"),
    [
        pytest.param(
            {"summaries": {"gsd": [30], "datetime": ["2020-01-01T00:00:00Z"]}},
            {"gsd": [30], "datetime": DATETIME_SUMMARY},
            id="other summaries",
        ),
        pytest.param(
            {},
            {"datetime": DATETIME_SUMMARY},
            id="no summaries",
        ),
        pytest.param(
            {"summaries": None},
            {"datetime": DATETIME_SUMMARY},
            id="null summaries",
        ),
        pytest.param(
            {"summaries": []},
            {"datetime": DATETIME_SUMMARY},
            id="array summaries",
        ),
    ],
)
def test_update_collection_default_summaries(collection_fields, expected):
    with psycopg.connect(DSN) as conn, conn.transaction(force_rollback=True):
        cur = conn.cursor()

        create_dashboard_schema(cur, conn.info.user)
        create_collection_summaries_functions(cur)

        cur.execute(
            "SELECT pgstac.create_collection(%s)",
            [Jsonb(COLLECTION | collection_fields)],
        )
        cur.execute("SELECT pgstac.create_item(%s)", [Jsonb(ITEM)])
        cur.execute(
            "SELECT dashboard.update_collection_default_summaries(%s)",
            [COLLECTION["id"]],
        )
        cur.execute(
            "SELECT content->'summaries' FROM pgstac.collections WHERE id = %s",
            [COLLECTION["id"]],
        )

        assert cur.fetchone() == (expected,)


def test_update_collection_extents_max():
    """Ingestion writes the temporal extent as UTC RFC 3339 date-times.

    The STAC collection schema requires each bound to be a JSON Schema
    `date-time` ending in `Z` or `+00:00`, thus Postgres's text form of a
    timestamp (`2023-01-15 00:00:00+00`) fails validation.
    """
    collection = {
        "id": "test-extents",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [[None, None]]},
        },
    }
    item = {
        "id": "test-item",
        "collection": "test-extents",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "properties": {
            "datetime": None,
            "start_datetime": "2023-01-15T00:00:00Z",
            "end_datetime": "2024-08-08T23:59:59Z",
        },
    }

    with psycopg.connect(DSN) as conn, conn.transaction(force_rollback=True):
        cur = conn.cursor()
        # A session time zone other than UTC, so the bounds must convert to UTC.
        cur.execute("SET LOCAL TimeZone = 'Asia/Tokyo'")

        create_dashboard_schema(cur, conn.info.user)
        create_collection_summaries_functions(cur)
        create_collection_extents_functions(cur)

        cur.execute("SELECT pgstac.create_collection(%s)", [Jsonb(collection)])
        cur.execute("SELECT pgstac.create_item(%s)", [Jsonb(item)])
        cur.execute(
            "SELECT dashboard.update_collection_extents_max(%s)", [collection["id"]]
        )
        cur.execute(
            "SELECT content->'extent'->'temporal'"
            "  FROM pgstac.collections"
            " WHERE id = %s",
            [collection["id"]],
        )

        assert cur.fetchone() == (
            {"interval": [["2023-01-15T00:00:00Z", "2024-08-08T23:59:59Z"]]},
        )


@pytest.fixture
def drop_rerun_db():
    """Drop the database and user that the handler creates."""
    yield

    name = sql.Identifier(RERUN_NAME)

    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(name))
        # Revokes the default privileges create_permissions sets in postgis.
        conn.execute(sql.SQL("DROP OWNED BY {}").format(name))
        conn.execute(sql.SQL("DROP ROLE {}").format(name))


@pytest.mark.usefixtures("drop_rerun_db")
def test_bootstrap_reruns():
    """Every change to handler.py reruns it on deploy, so a rerun must succeed.

    A step that cannot repeat raises on the second call.
    """
    bootstrap(ADMIN_SECRET, USER_SECRET, PGSTAC_VERSION)
    bootstrap(ADMIN_SECRET, USER_SECRET, PGSTAC_VERSION)
