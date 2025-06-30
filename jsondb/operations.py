from typing import List, Dict, Any, Callable, Union
import copy
from .exceptions import InvalidOperationError

def insert_into(table_data: Any, new_item: Any) -> Any:
    """Inserts an item into a table, returning a new copy."""
    if isinstance(table_data, list):
        # Buat copy baru untuk menghindari mutasi
        new_table = table_data.copy()
        new_table.append(new_item)
        return new_table
    elif isinstance(table_data, dict) and isinstance(new_item, dict):
        # Buat copy baru untuk menghindari mutasi
        new_table = table_data.copy()
        new_table.update(new_item)
        return new_table
    raise InvalidOperationError(
        f"Cannot insert into data of type '{type(table_data).__name__}'. "
        f"Only list appends and dict updates are supported."
    )

def update_in(table_data: Any, condition: Callable[[Any], bool], new_data: Any) -> Any:
    """Updates items in a list or dict based on a condition, returning a new copy."""
    if isinstance(table_data, list):
        return [new_data if condition(item) else item for item in table_data]
    elif isinstance(table_data, dict):
        # Buat copy baru dan update hanya yang match condition
        new_table = {}
        for key, value in table_data.items():
            if condition((key, value)):
                new_table[key] = new_data
            else:
                new_table[key] = value
        return new_table
    raise InvalidOperationError(
        f"Update operation not supported for type '{type(table_data).__name__}'."
    )

def delete_from(table_data: Any, condition: Callable[[Any], bool]) -> Any:
    """Deletes items from a list or dict based on a condition, returning a new copy."""
    if isinstance(table_data, list):
        return [item for item in table_data if not condition(item)]
    elif isinstance(table_data, dict):
        # Buat dict baru tanpa item yang match condition
        return {
            key: value 
            for key, value in table_data.items() 
            if not condition((key, value))
        }
    raise InvalidOperationError(
        f"Delete operation not supported for type '{type(table_data).__name__}'."
    )
