# JsonDB-Py

A simple, lightweight, and file-based JSON database library for Python, now with proper error handling and a modular structure.

## Overview

`Json-Py` provides a simple interface for storing and retrieving data in a JSON file. It's perfect for small projects where a full-fledged database is overkill.

## Installation

```bash
pip install jsondb-py
```

## Quick Start

```python
from jsondb import JsonDB

# Initialize the database
db = JsonDB('my_database.json')

try:
    # Create a table
    db.create_table('users')

    # Insert data
    db.insert_data('users', {'id': 1, 'name': 'Alice', 'role': 'admin'})
    db.insert_data('users', {'id': 2, 'name': 'Bob', 'role': 'user'})

    # Update data where role is 'user'
    db.update_data(
        'users',
        condition=lambda user: user.get('role') == 'user',
        new_data={'id': 2, 'name': 'Bob', 'role': 'member'}
    )

    # Delete data where id is 1
    db.delete_data('users', condition=lambda user: user.get('id') == 1)

    # Show final data
    db.show_data('users')

except db.TableExistsError as e:
    print(f"Setup failed because a table already exists: {e}")
except db.Error as e: # Catch any library-specific error
    print(f"An error occurred with the database: {e}")
except Exception as e:
    print(f"A general error occurred: {e}")

```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
