"""Custom exceptions for py-jsondb."""

class JsonDBError(Exception):
    """Base exception for all library-specific errors."""
    pass

class TableNotFoundError(JsonDBError, KeyError):
    """Raised when a table is not found in the database."""
    def __init__(self, table_name):
        super().__init__(f"Table '{table_name}' does not exist.")

class TableExistsError(JsonDBError, ValueError):
    """Raised when trying to create a table that already exists."""
    def __init__(self, table_name):
        super().__init__(f"Table '{table_name}' already exists.")

class InvalidOperationError(JsonDBError, TypeError):
    """Raised when an operation is not valid for the table's data type."""
    pass

class StorageError(JsonDBError, IOError):
    """Raised for errors related to file I/O."""
    pass
