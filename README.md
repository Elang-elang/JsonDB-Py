<p align="center">
  <a href="https://pypi.org/project/jsondb-python">
    <img src="https://raw.githubusercontent.com/Elang-elang/JsonDB/refs/heads/main/icons/icon2.png?token=GHSAT0AAAAAADGRQCSXNYSVVQWA6VZJUYB42DMFE2A" alt="JsonDB Logo">
  </a>
</p>

<h1 align="center">JsonDB-Python</h1>

<p align="center">
  <a href="https://pypi.org/project/jsondb-python">
    <img src="https://img.shields.io/pypi/v/jsondb-python.svg?label=PyPI" alt="PyPI Version">
  </a>
  <a href="https://github.com/Elang-elang/JsonDB-Python/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-purple.svg" alt="License">
  </a>
  <a href="https://jsondb-docs.netlify.app">
    <img src="https://img.shields.io/badge/Documentation-passing-brightgreen" alt="Documentation">
  </a>
</p>

A simple, lightweight, and file-based JSON database library for Python, now with proper error handling, a modular structure, and a powerful interactive REPL.

## Overview

`jsondb-python` provides two ways to manage your data:

1.  **As a Python Library:** A simple interface for storing and retrieving data in a JSON file. It's perfect for small projects where a full-fledged database is overkill.
2.  **As an Interactive REPL:** A feature-rich command-line interface (CLI) to manage your databases directly from the terminal, no scripting required.

## Installation

```bash
pip install jsondb-python
```
For the best REPL experience with auto-completion and history, it is recommended to install `prompt_toolkit`:
```bash
pip install prompt-toolkit
```

## Usage

### As a Python Library (Quick Start)

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

### Interactive REPL (CLI)

The library includes a powerful interactive REPL (Read-Eval-Print Loop) to manage your databases from the command line.

**Launching the REPL:**

```bash
# Start the REPL in the main menu
jsondb

# Or open a database file directly
jsondb ./path/to/your/database.json
```

**Key Features:**

*   **Interactive Management:** Create, edit, and manage your JSON databases without writing Python code.
*   **Smart Auto-Completion:** Press `Tab` to get suggestions for commands, file paths, and table names.
*   **Command History:** Use the Up/Down arrow keys to navigate your command history.
*   **User-Friendly Interface:** A colorized and structured interface makes database management easy.
*   **Built-in Help:** Type `.help` in any mode to see a list of available commands.
*   **Safe Operations:** Features auto-saving on exit and automatic backup creation to prevent data loss.

**Example Session:**

```bash
$ jsondb
🌟 JsonDB >>> .build
📁 Enter database path (example: data/mydb.json): users.json
✅ Database 'users.json' created/opened successfully!
💡 Use '.create <table_name>' to create a new table
📦 [users.json] >>> .create people
✅ Table 'people' created successfully!
📦 [users.json] >>> .use people
✅ Successfully selected table 'people'!
💡 Use '.insert' to add data
📋 [people] >>> .insert
# ... interactive prompt to add data ...
✅ Data added successfully!
📋 [people] >>> .show
# ... displays table data ...
📋 [people] >>> .exit
💾 Performing auto-save before exiting...
👋 Thank you for using JsonDB REPL!
💾 Your data has been safely saved
```

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/Elang-elang/JsonDB-Python/blob/main/LICENSE) file for details.
