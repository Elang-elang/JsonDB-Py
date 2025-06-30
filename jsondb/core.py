import copy
from typing import Any, Dict, List, Callable, Optional

from .storage import StorageHandler
from . import operations
from . import utils
from . import exceptions

class JsonDB:
    """
    A simple, file-based JSON database that uses a dictionary-like interface.
    """
    # Expose exceptions as attributes of the class
    Error = exceptions.JsonDBError
    TableNotFoundError = exceptions.TableNotFoundError
    TableExistsError = exceptions.TableExistsError
    InvalidOperationError = exceptions.InvalidOperationError
    StorageError = exceptions.StorageError
    
    def __init__(self, file_path: str):
        """Initializes the database, loading data from the given file path."""
        self._storage = StorageHandler(file_path)
        self._data = self._storage.read_data()

    def _save(self) -> None:
        """Saves the current state of the database to the file."""
        self._storage.write_data(self._data)

    def create_table(self, table_name: str, initial_data: Any = None) -> None:
        """Creates a new table. Raises TableExistsError if it already exists."""
        if table_name in self._data:
            raise TableExistsError(table_name)
        self._data[table_name] = initial_data if initial_data is not None else []
        self._save()

    def insert_data(self, table_name: str, data: Any) -> None:
        """Adds data to a table. Raises TableNotFoundError or InvalidOperationError."""
        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)
        table = self.get_data(table_name)
        self._data[table_name] = operations.insert_into(table, data)
        self._save()

    def update_data(self, table_name: str, condition: Callable, new_data: Any) -> None:
        """Updates data in a table based on a condition."""
        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)
        table = self.get_data(table_name)
        self._data[table_name] = operations.update_in(table, condition, new_data)
        self._save()

    def delete_data(self, table_name: str, condition: Callable) -> None:
        """Deletes data from a table based on a condition."""
        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)
        table = self.get_data(table_name)
        self._data[table_name] = operations.delete_from(table, condition)
        self._save()

    def clear_table(self, table_name: str) -> None:
        """Removes all data from a table, making it an empty list."""
        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)
        self._data[table_name] = []
        self._save()

    def drop_table(self, table_name: str) -> None:
        """Deletes an entire table. Raises TableNotFoundError."""
        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)
        del self._data[table_name]
        self._save()

    def get_data(self, table_name: str = None) -> Any:
        """Retrieves a copy of table or the entire database to prevent external mutation."""
        if table_name is None:
            # Return deep copy untuk mencegah mutasi eksternal
            return copy.deepcopy(self._data)
        
        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)
        
        # Return deep copy untuk mencegah mutasi eksternal
        return copy.deepcopy(self._data[table_name])
    
    def get_data_reference(self, table_name: str = None) -> Any:
        """
        Retrieves direct reference to data (for internal use or advanced users).
        WARNING: Modifying returned data will affect the database directly.
        """
        if table_name is None:
            return self._data
        
        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)
        
        return self._data[table_name]

    def table_exists(self, table_name: str) -> bool:
        """Checks if a table exists."""
        return table_name in self._data

    def list_tables(self) -> List[str]:
        """Returns a list of all table names."""
        return list(self._data.keys())

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Gets detailed information about a specific table."""
        if not self.table_exists(table_name):
            raise TableNotFoundError(table_name)
        return utils.get_table_info(table_name, self._data[table_name])

    def show_data(self, table_name: str = None) -> None:
        """Prints formatted data for a table or the entire database."""
        data_to_show = self.get_data(table_name)
        if table_name:
            info = self.get_table_info(table_name)
            print(utils.format_for_display(info))
        else:
            print(utils.format_for_display(data_to_show))