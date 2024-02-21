"""Database connection handling."""

from typing import Optional

from fastapi import FastAPI
from psycopg_pool import ConnectionPool

from titiler.pgstac.settings import PostgresSettings


class RDSProxyConnectionPool(ConnectionPool):
    """Subclassing connectionpool to ensure search path is set when connection is acquired"""
    def getconn(self, key=None):
        conn = super().getconn(key)
        with conn.cursor() as cur:
            cur.execute("SET search_path TO pgstac, public")
        return conn

async def connect_to_rds_proxy(
    app: FastAPI, settings: Optional[PostgresSettings] = None
) -> None:
    """Connect to Database. Customized for RDS Proxy, so avoiding -c args"""
    if not settings:
        settings = PostgresSettings()

    # Application can be provided by query parameters rather than -c
    app.state.dbpool = RDSProxyConnectionPool(
        conninfo=str(settings.database_url)+"?application_name=pgstac",
        min_size=settings.db_min_conn_size,
        max_size=settings.db_max_conn_size,
        max_waiting=settings.db_max_queries,
        max_idle=settings.db_max_idle,
        num_workers=settings.db_num_workers
    )

    # Make sure the pool is ready
    # ref: https://www.psycopg.org/psycopg3/docs/advanced/pool.html#pool-startup-check
    app.state.dbpool.wait()


async def close_db_connection(app: FastAPI) -> None:
    """Close Pool."""
    app.state.dbpool.close()