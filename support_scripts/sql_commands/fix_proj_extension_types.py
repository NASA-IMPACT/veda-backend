"""
This script fixes the projection extension properties proj:epsg and proj:shape.
"""

from postgres_runner import PostgreSQLCommandRunner


class ProjExtensionFloatIntFix(PostgreSQLCommandRunner):
    """This class fixes the floating point values in proj:epsg and proj:shape properties (they should be int)."""

    @property
    def sql_commands(self):
        """A list of SQL commands to execute."""
        epsg_update = """
            UPDATE items
            SET content = jsonb_set(content, '{properties, proj:epsg}', to_jsonb(CAST((content->'properties'->>'proj:epsg') AS INTEGER)), true)
            WHERE content->'properties'->>'proj:epsg' IS NOT NULL;
        """
        proj_shape_update0 = """
            UPDATE items
            SET content = jsonb_set(content, '{properties, proj:shape, 0}', to_jsonb(CAST((content->'properties'->'proj:shape'->0) AS INTEGER)), true)
            WHERE content->'properties'->'proj:shape'->0 IS NOT NULL;
        """
        proj_shape_update1 = """
            UPDATE items
            SET content = jsonb_set(content, '{properties, proj:shape, 1}', to_jsonb(CAST((content->'properties'->'proj:shape'->1) AS INTEGER)), true)
            WHERE content->'properties'->'proj:shape'->1 IS NOT NULL;
        """
        return [epsg_update, proj_shape_update0, proj_shape_update1]


if __name__ == "__main__":
    ProjExtensionFloatIntFix.from_conn_string().execute()
