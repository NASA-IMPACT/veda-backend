"""Tests for the dashboard SQL functions that handler.py installs.

These run against the database service in docker-compose.yml, inside a
transaction that is always rolled back.
"""

import psycopg
import pytest
from handler import create_collection_summaries_functions, create_dashboard_schema
from psycopg.types.json import Jsonb

DSN = "postgresql://username:password@localhost:5439/postgis"

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
