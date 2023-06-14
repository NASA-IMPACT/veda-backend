"""
This script deletes the stac_extensions field from collections that have a null value for it.
"""

from postgres_runner import PostgreSQLCommandRunner


class DeleteNullStacExtensions(PostgreSQLCommandRunner):
    """This class deletes the stac_extensions field from collections that have a null value for it."""

    @property
    def sql_commands(self):
        """A list of SQL commands to execute."""
        delete_null_field = """
            UPDATE collections
            SET content = content - 'stac_extensions'
            WHERE content->>'stac_extensions' IS NULL;
        """
        return [delete_null_field]


if __name__ == "__main__":
    DeleteNullStacExtensions.from_conn_string().execute()
