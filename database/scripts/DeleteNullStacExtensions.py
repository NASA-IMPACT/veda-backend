from PostgreSQLCommandRunner import PostgreSQLCommandRunner

class DeleteNullStacExtensions(PostgreSQLCommandRunner):
    """This class fixes the floating point values in proj:epsg and proj:shape properties (they should be int)."""
    @property
    def sql_commands(self):
        delete_null_field = """
            UPDATE collections
            SET content = content - 'stac_extensions'
            WHERE content->>'stac_extensions' IS NULL;
        """
        return [delete_null_field]

if __name__ == "__main__":
    DeleteNullStacExtensions.from_conn_string().execute()