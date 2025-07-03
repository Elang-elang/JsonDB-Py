#!/usr/bin/env python3
"""
Command line interface for jsondb-py
"""

import sys
from . import repl

def main():
    """Main entry point for command line interface"""
    try:
        # Pass command line arguments to the repl module
        sys.argv[0] = 'jsondb'  # Set the program name
        repl.main()  # Assuming your Repl.py has a main() function
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()