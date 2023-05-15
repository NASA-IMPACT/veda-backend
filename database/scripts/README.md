## PostgreSQLCommandRunner

`PostgreSQLCommandRunner` is a base class that provides functionality to execute SQL commands against a PostgreSQL database. It abstracts the database connection and execution logic.

### Constructor

```python
def __init__(self, host, port, database, user, password):
```

- `host`: The hostname or IP address of the PostgreSQL server.
- `port`: The port number on which the PostgreSQL server is listening.
- `database`: The name of the PostgreSQL database.
- `user`: The username to authenticate with the PostgreSQL server.
- `password`: The password to authenticate with the PostgreSQL server.

### Methods

#### `execute()`

```python
def execute(self):
```

This method establishes a connection to the PostgreSQL database, executes the SQL command defined in the child class, and commits the changes to the database. It also handles any exceptions that occur during the execution.

This method needs to be implemented in the child classes to provide the specific SQL command to execute.

#### `from_conn_string`

```python
@classmethod
def from_conn_string(cls) -> "PostgreSQLCommandRunner":
```

This class method of `PostgreSQLCommandRunner` allows creating an instance of the class by parsing a PostgreSQL connection string. It extracts the required connection parameters from the connection string and constructs a `PostgreSQLCommandRunner` object.

To create an instance of a `PostgreSQLCommandRunner` child using a PostgreSQL connection string, call the `from_conn_string` class method:

```python
runner = PostgreSQLCommandRunner.from_conn_string()
```

This will read the user-provided connection string provided with the `--connection_string` argument from the command line. The connection string is parsed and a `PostgreSQLCommandRunner` instance is created using the extracted connection parameters.


### Child Classes

`PostgreSQLCommandRunner` has the following child classes that inherit from it:


#### ProjExtensionFloatIntFix

`ProjExtensionFloatIntFix` is a subclass of `PostgreSQLCommandRunner` specifically designed to update floating point values for the projection extension of STAC (Spatio-Temporal Asset Catalog) to integers in a PostgreSQL database.
