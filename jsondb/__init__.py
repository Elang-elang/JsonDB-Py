"""
py-jsondb: A simple, file-based JSON database library.
"""

__version__ = "1.0.5" # Version bump for API improvement

# Expose only the main class. Exceptions are accessed via the class.
from .core import JsonDB

__all__ = ['JsonDB']

# CLI is available but not exposed in __all__ since it's for internal use
from . import cli