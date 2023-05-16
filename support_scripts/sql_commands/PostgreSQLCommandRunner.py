"""
This module provides a base class for running PostgreSQL commands.
"""

import abc
import argparse
from typing import List

import psycopg2


class PostgreSQLCommandRunner(metaclass=abc.ABCMeta):
    """This class provides a base class for running PostgreSQL commands."""

    def __init__(self, host, port, database, user, password):
        """Initialize PostgreSQLCommandRunner."""
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def execute(self):
        """Execute SQL commands."""
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )
        cursor = conn.cursor()
        for command in self.sql_commands:
            print(f"Executing SQL command: {command}")
            try:
                cursor.execute(command)
                conn.commit()
                print("SQL command executed successfully.")
            except psycopg2.Error as e:
                print(f"Error executing SQL command: {e}")
        cursor.close()
        conn.close()

    @property
    @abc.abstractmethod
    def sql_commands(self) -> List[str]:
        """A list of SQL commands to execute."""
        raise NotImplementedError(
            "sql_command attribute must be implemented in the child class"
        )

    @classmethod
    def from_args(cls) -> "PostgreSQLCommandRunner":
        """Create a PostgreSQLCommandRunner from command line arguments."""
        parser = argparse.ArgumentParser(description="Run PostgreSQL command")
        parser.add_argument("--host", type=str, help="PostgreSQL host")
        parser.add_argument("--port", type=str, help="PostgreSQL port")
        parser.add_argument("--database", type=str, help="PostgreSQL database")
        parser.add_argument("--user", type=str, help="PostgreSQL username")
        parser.add_argument("--password", type=str, help="PostgreSQL password")
        args = parser.parse_args()

        return cls(
            host=args.host,
            port=args.port,
            database=args.database,
            user=args.user,
            password=args.password,
        )

    @classmethod
    def from_conn_string(cls) -> "PostgreSQLCommandRunner":
        """Create a PostgreSQLCommandRunner from a connection string."""
        parser = argparse.ArgumentParser(
            description="Parse PostgreSQL connection string"
        )
        parser.add_argument(
            "--connection_string", type=str, help="PostgreSQL connection string"
        )
        args = parser.parse_args()
        connection_string = args.connection_string
        parts = connection_string.split("://")

        # Extract username and password
        credentials, host_and_db = parts[1].split("@")
        username, password = credentials.split(":")

        # Extract host, port, and database
        host_parts = host_and_db.split("/")
        host, port = host_parts[0].split(":")
        database = host_parts[1]

        return cls(
            host=host, port=port, database=database, user=username, password=password
        )
