"""Start Pillway:  python Pillway.py   (add --help to see options like --check-config or --role).

This file only checks your Python setup, reads the command-line options and opens the window.
"""

import sys

MINIMUM_PYTHON = (3, 11)


def main():
    if sys.version_info < MINIMUM_PYTHON:
        print(f"Pillway needs Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer. You have "
              f"{sys.version.split()[0]}. Install the latest Python from https://www.python.org/downloads/")
        return 1
    from pillway.cli import run
    role = run()
    if role is None:
        return 0
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("Python's window toolkit (tkinter) is missing.\n"
              "  Windows/Mac: reinstall Python from python.org and keep 'tcl/tk' ticked.\n"
              "  Mac with Homebrew: brew install python-tk\n"
              "  Linux: sudo apt install python3-tk")
        return 1
    from pillway.app import PillwayApp
    app = PillwayApp(start_role=role)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
