"""Pillway desktop application package.

The window class is imported lazily, so the pure-logic parts (pillway.core,
pillway.ai, pillway.storage) work and can be tested even on a computer
without tkinter.
"""

__all__ = ["PillwayApp"]


def __getattr__(name):
    if name == "PillwayApp":
        from .app import PillwayApp
        return PillwayApp
    raise AttributeError(name)
